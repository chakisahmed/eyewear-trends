"""Daily collection for press sites without an RSS feed, read from their XML sitemap (e.g. Acuité).

Configured in feeds.yaml (`sitemap_sources:`). Runs in the pipeline's "rss" step, after the feeds.
A sitemap's <lastmod> is only a hint: sites re-save old articles (Acuité touched 858 "profession"
pages in a month), so candidates are picked by lastmod but kept only if the page's own publication
date is recent. Caps per run bound the downloads (`max_checked`) and the Claude analysis cost
(`max_new`, ~$0.01 per article): the extract step analyses whatever is collected.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import trafilatura
import yaml
from sqlalchemy.orm import Session

from app.collectors.backfill import _is_eyewear, _parse_date
from app.collectors.base import add_document, document_exists, fetch_html, get_or_create_source, http_client
from app.progress import Progress, report

log = logging.getLogger(__name__)
FEEDS_PATH = Path(__file__).with_name("feeds.yaml")
DELAY_S = 1.5  # pause between downloads: be polite to small trade sites
MAX_CHILD_SITEMAPS = 60
URL_RE = re.compile(r"<url>(.*?)</url>", re.S)
CHILD_RE = re.compile(r"<sitemap>\s*<loc>\s*([^<\s]+)\s*</loc>", re.S)
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
LASTMOD_RE = re.compile(r"<lastmod>\s*([^<\s]+)\s*</lastmod>")


def load_sitemap_sources() -> list[dict]:
    return yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8")).get("sitemap_sources", [])


def _get(client: httpx.Client, url: str) -> str | None:
    try:
        r = client.get(url)
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        log.info("Sitemap fetch failed %s: %s", url, e)
        return None


def read_sitemap(client: httpx.Client, url: str) -> list[tuple[str, datetime | None]]:
    """(loc, lastmod) of every <url>, following one level of <sitemapindex> children."""
    xml = _get(client, url) or ""
    children = [c.replace("&amp;", "&") for c in CHILD_RE.findall(xml)][:MAX_CHILD_SITEMAPS]
    docs = [xml] if not children else []
    for child in children:
        time.sleep(DELAY_S)
        docs.append(_get(client, child) or "")
    out = []
    for doc in docs:
        for block in URL_RE.findall(doc):
            loc, lastmod = LOC_RE.search(block), LASTMOD_RE.search(block)
            if loc:
                out.append((loc.group(1).replace("&amp;", "&"), _parse_date(lastmod.group(1)) if lastmod else None))
    return out


def collect_sitemap_source(session: Session, client: httpx.Client, cfg: dict, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=cfg.get("lookback_days", 7))
    include = cfg.get("include") or []
    source = get_or_create_source(session, name=cfg["name"], kind="press", url=cfg["url"], lang=cfg["lang"], country=cfg.get("country"))
    candidates = sorted(
        ((loc, lastmod) for loc, lastmod in read_sitemap(client, cfg["sitemap"])
         if lastmod and lastmod >= since and (not include or any(p in loc for p in include))),
        key=lambda c: c[1], reverse=True,  # newest first, so the caps keep the most recent articles
    )
    added = checked = 0
    for url, lastmod in candidates:
        if added >= cfg.get("max_new", 15) or checked >= cfg.get("max_checked", 40):
            break
        if document_exists(session, url):
            continue
        time.sleep(DELAY_S)
        checked += 1
        html = fetch_html(client, url)  # robots.txt checked here
        if not html:
            continue
        meta = trafilatura.extract_metadata(html)
        published = _parse_date(meta.date if meta else None) or lastmod
        if published < since:
            continue  # an old article re-saved recently
        title = (meta.title if meta else None) or url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
        text = trafilatura.extract(html, url=url, include_comments=False, favor_precision=True) or ""
        if not _is_eyewear(title, text):
            continue
        add_document(session, source=source, url=url, title=title, text=text, lang=cfg["lang"], published_at=published)
        added += 1
    session.commit()
    log.info("%s (sitemap): %d candidates, %d pages checked, %d new", cfg["name"], len(candidates), checked, added)
    return added


def collect_sitemap_sources(session: Session, progress: Progress = None) -> int:
    configs = load_sitemap_sources()
    added = 0
    with http_client() as client:
        for i, cfg in enumerate(configs):
            report(progress, i, len(configs))
            added += collect_sitemap_source(session, client, cfg)
    report(progress, len(configs), len(configs))
    return added
