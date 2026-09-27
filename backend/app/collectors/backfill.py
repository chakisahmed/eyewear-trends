"""One-off backfill of the optical trade press archives (last N weeks), beyond what RSS shows.

RSS feeds only carry the latest 10–20 items, so a new installation starts with almost no history
and every trend reads "Peu de données". This collects the archive once, keeping each article's real
publication date so trends spread over the weeks. It only collects: Claude analysis is a separate
step (pipeline "extract"), so the cost can be checked first.

Two archive methods, configured per site in feeds.yaml (`backfill:`):
  paged_feed  WordPress feeds that accept ?paged=N (newest first): read pages until the cutoff
  sitemap     XML sitemap; optional URL filters; dates from <lastmod> or from the page itself
"""

from __future__ import annotations

import logging
import re
import time
from calendar import timegm
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import feedparser
import httpx
import trafilatura
import yaml
from sqlalchemy.orm import Session

from app.collectors.base import add_document, document_exists, fetch_article_text, fetch_html, get_or_create_source, http_client
from app.extraction.service import EYEWEAR_RE
from app.progress import Progress, report

log = logging.getLogger(__name__)
FEEDS_PATH = Path(__file__).with_name("feeds.yaml")
DELAY_S = 1.5  # pause between page downloads: be polite to small trade sites
LOC_RE = re.compile(r"<url>(.*?)</url>", re.S)


def load_backfill_config() -> list[dict]:
    return yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8")).get("backfill", [])


def _as_utc(d: date | datetime | None) -> datetime | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.strip().replace("Z", "+00:00")))
    except ValueError:
        try:
            return _as_utc(date.fromisoformat(value.strip()[:10]))
        except ValueError:
            return None


def _is_eyewear(*texts: str | None) -> bool:
    return bool(EYEWEAR_RE.search(" ".join(t for t in texts if t)))


def backfill_paged_feed(session: Session, client: httpx.Client, cfg: dict, since: datetime, limit: int) -> int:
    source = get_or_create_source(session, name=cfg["name"], kind="press", url=cfg["feed"], lang=cfg["lang"], country=cfg.get("country"))
    added = 0
    for page in range(1, cfg.get("max_pages", 30) + 1):
        sep = "&" if "?" in cfg["feed"] else "?"
        try:
            resp = client.get(f"{cfg['feed']}{sep}paged={page}")
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.info("%s page %d: %s (end of archive)", cfg["name"], page, e)
            break
        entries = feedparser.parse(resp.content).entries
        if not entries:
            break
        reached_cutoff = False
        for entry in entries:
            parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            published = datetime.fromtimestamp(timegm(parsed), tz=timezone.utc) if parsed else None
            if published and published < since:
                reached_cutoff = True
                continue
            url, title, teaser = entry.get("link"), entry.get("title", ""), entry.get("summary", "")
            if not url or not _is_eyewear(title, teaser) or document_exists(session, url):
                continue
            time.sleep(DELAY_S)
            text = fetch_article_text(client, url) or teaser
            add_document(session, source=source, url=url, title=title, text=text, lang=cfg["lang"], published_at=published)
            added += 1
            if added >= limit:
                session.commit()
                return added
        session.commit()
        log.info("%s: page %d done, %d new so far", cfg["name"], page, added)
        if reached_cutoff:
            break
    return added


def backfill_sitemap(session: Session, client: httpx.Client, cfg: dict, since: datetime, limit: int) -> int:
    source = get_or_create_source(session, name=cfg["name"], kind="press", url=cfg["feed"], lang=cfg["lang"], country=cfg.get("country"))
    try:
        xml = client.get(cfg["sitemap"]).text
    except httpx.HTTPError as e:
        log.warning("%s sitemap unreachable: %s", cfg["name"], e)
        return 0
    items = []  # (url, lastmod or None), in sitemap order
    for block in LOC_RE.findall(xml):
        loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", block)
        lastmod = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", block)
        if loc:
            items.append((loc.group(1), _parse_date(lastmod.group(1)) if lastmod else None))
    include = cfg.get("include") or []
    if include:
        items = [(u, d) for u, d in items if any(p in u for p in include)]
    if cfg.get("order") == "oldest_first":
        items.reverse()  # walk newest first, so we can stop at the cutoff

    added, checked, old_in_a_row = 0, 0, 0
    for url, lastmod in items:
        if lastmod and lastmod < since:
            continue
        if document_exists(session, url):
            continue
        time.sleep(DELAY_S)
        html = fetch_html(client, url)
        checked += 1
        if not html:
            continue
        meta = trafilatura.extract_metadata(html)
        published = lastmod or _parse_date(meta.date if meta else None)
        if published and published < since:
            old_in_a_row += 1
            # Ordered sitemap: a run of old articles means we are past the window.
            if cfg.get("order") and old_in_a_row >= 5:
                break
            continue
        old_in_a_row = 0
        title = (meta.title if meta else None) or url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
        text = trafilatura.extract(html, url=url, include_comments=False, favor_precision=True) or ""
        if not _is_eyewear(title, text):
            continue
        add_document(session, source=source, url=url, title=title, text=text, lang=cfg["lang"], published_at=published)
        added += 1
        if added % 10 == 0:
            session.commit()
            log.info("%s: %d new so far (%d pages checked)", cfg["name"], added, checked)
        if added >= limit:
            break
    session.commit()
    return added


def run_backfill(session: Session, weeks: int = 12, limit_per_source: int = 300, progress: Progress = None) -> dict[str, int]:
    """Collect the trade press archive of the last `weeks` weeks. Returns new documents per source."""
    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    config = load_backfill_config()
    result: dict[str, int] = {}
    with http_client() as client:
        for i, cfg in enumerate(config):
            report(progress, i, len(config))
            method = backfill_paged_feed if cfg["method"] == "paged_feed" else backfill_sitemap
            log.info("Backfill %s (%s) since %s", cfg["name"], cfg["method"], since.date())
            result[cfg["name"]] = method(session, client, cfg, since, limit_per_source)
    report(progress, len(config), len(config))
    return result
