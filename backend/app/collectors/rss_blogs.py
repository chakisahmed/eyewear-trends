"""Press and blog RSS feeds (FR + EN)."""

from __future__ import annotations

import logging
from calendar import timegm
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx
import yaml
from sqlalchemy.orm import Session

from app.collectors.base import (
    add_document,
    document_exists,
    fetch_article_text,
    get_or_create_source,
    http_client,
)
from app.config import settings
from app.extraction.service import EYEWEAR_RE

log = logging.getLogger(__name__)
FEEDS_PATH = Path(__file__).with_name("feeds.yaml")


def load_feeds() -> list[dict]:
    return yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8"))["feeds"]


def _published(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc) if parsed else None


def collect_rss(session: Session, limit: int | None = None) -> int:
    limit = limit or settings.max_articles_per_run
    added = 0
    with http_client() as client:
        for feed in load_feeds():
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
    log.info("RSS: %d new documents", added)
    return added
