"""News discovery through the GDELT DOC 2.0 API (FR + EN queries)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml
from sqlalchemy.orm import Session

from app.collectors.base import add_document, document_exists, fetch_article_text, get_or_create_source, http_client
from app.config import settings
from app.progress import Progress, report

log = logging.getLogger(__name__)
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
FEEDS_PATH = Path(__file__).with_name("feeds.yaml")
MIN_INTERVAL_S = 6  # GDELT asks for at most one request every 5 seconds


def _seendate(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _query(client: httpx.Client, params: dict, attempts: int = 4) -> list[dict] | None:
    """GDELT rate-limits with 429 or a plain-text notice; back off and retry."""
    for attempt in range(attempts):
        try:
            resp = client.get(GDELT_URL, params=params)
            if resp.status_code != 429:
                resp.raise_for_status()
                return resp.json().get("articles", [])
        except (httpx.HTTPError, ValueError) as e:
            log.info("GDELT attempt %d failed: %s", attempt + 1, e)
        time.sleep(MIN_INTERVAL_S * 2 ** (attempt + 1))
    return None


def collect_news(session: Session, timespan: str = "1w", per_query: int = 30, progress: Progress = None) -> int:
    queries = yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8"))["news_queries"]
    added = 0
    with http_client() as client:
        for i, q in enumerate(queries):
            report(progress, i, len(queries))
            if i:
                time.sleep(MIN_INTERVAL_S)
            source = get_or_create_source(
                session, name=f"Actualités ({q['lang'].upper()})", kind="news",
                url=f"gdelt:{q['query']}", lang=q["lang"],
            )
            params = {"query": q["query"], "mode": "artlist", "format": "json", "maxrecords": per_query, "timespan": timespan, "sort": "datedesc"}
            articles = _query(client, params)
            if articles is None:
                log.warning("GDELT query failed (%s), skipping", q["lang"])
                continue
            for art in articles:
                url = art.get("url")
                if not url or document_exists(session, url) or added >= settings.max_articles_per_run:
                    continue
                text = fetch_article_text(client, url)
                if not text:
                    continue
                add_document(
                    session, source=source, url=url, title=art.get("title", ""), text=text,
                    lang=q["lang"], published_at=_seendate(art.get("seendate")),
                )
                added += 1
            session.commit()
    report(progress, len(queries), len(queries))
    log.info("News: %d new documents", added)
    return added
