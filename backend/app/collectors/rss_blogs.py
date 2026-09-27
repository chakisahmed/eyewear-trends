"""Press and blog RSS feeds (FR + EN)."""

from __future__ import annotations

import logging
from calendar import timegm
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import (
    add_document,
    document_exists,
    fetch_article_text,
    get_or_create_source,
    http_client,
)
from app.config import settings
from app.models import Source
from app.extraction.service import EYEWEAR_RE
from app.progress import Progress, report

log = logging.getLogger(__name__)
FEEDS_PATH = Path(__file__).with_name("feeds.yaml")


def load_feeds() -> list[dict]:
    return yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8"))["feeds"]


def _published(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc) if parsed else None


def sync_feed_sources(session: Session, feeds: list[dict]) -> int:
    """Press sources follow feeds.yaml: listed ones are active, removed ones are marked inactive (their
    articles and mentions are kept as history). Only kind "press": stores and news are not feeds."""
    listed = {f["url"] for f in feeds}
    changed = 0
    for source in session.scalars(select(Source).where(Source.kind == "press")):
        active = source.url in listed
        if source.active != active:
            source.active, changed = active, changed + 1
    session.commit()
    return changed


def collect_rss(session: Session, limit: int | None = None, progress: Progress = None) -> int:
    limit = limit or settings.max_articles_per_run
    added = 0
    with http_client() as client:
        feeds = load_feeds()
        sync_feed_sources(session, feeds)
        for i, feed in enumerate(feeds):
            report(progress, i, len(feeds))  # feeds done so far (session is committed here)
            source = get_or_create_source(
                session, name=feed["name"], kind="press", url=feed["url"], lang=feed["lang"], country=feed.get("country")
            )
            try:
                resp = client.get(feed["url"])
                resp.raise_for_status()
            except httpx.HTTPError as e:
                log.warning("Feed %s failed: %s", feed["name"], e)
                continue
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries:
                if added >= limit:
                    session.commit()
                    return added
                url = entry.get("link")
                title = entry.get("title", "")
                teaser = entry.get("summary", "")
                # Cheap filter first: most fashion articles are not about eyewear.
                if not url or not EYEWEAR_RE.search(f"{title} {teaser}") or document_exists(session, url):
                    continue
                text = fetch_article_text(client, url) or teaser
                add_document(
                    session, source=source, url=url, title=title, text=text, lang=feed["lang"], published_at=_published(entry)
                )
                added += 1
            session.commit()
    report(progress, len(feeds), len(feeds))
    log.info("RSS: %d new documents", added)
    return added
