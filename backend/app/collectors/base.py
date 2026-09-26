from __future__ import annotations

import logging
from datetime import datetime
from functools import lru_cache
from urllib import robotparser
from urllib.parse import urlsplit

import httpx
import trafilatura
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, Source

log = logging.getLogger(__name__)


def http_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": settings.user_agent},
        timeout=settings.request_timeout,
        follow_redirects=True,
    )


@lru_cache(maxsize=512)
def _robots_for(origin: str) -> robotparser.RobotFileParser | None:
    rp = robotparser.RobotFileParser()
    try:
        with http_client() as c:
            r = c.get(f"{origin}/robots.txt")
        if r.status_code >= 400:
            return None  # no robots.txt: allowed
        rp.parse(r.text.splitlines())
        return rp
    except httpx.HTTPError:
        return None


def allowed_by_robots(url: str) -> bool:
    parts = urlsplit(url)
    rp = _robots_for(f"{parts.scheme}://{parts.netloc}")
    return rp is None or rp.can_fetch(settings.user_agent, url)


def fetch_article_text(client: httpx.Client, url: str) -> str | None:
    """Download a page and extract the main article text. Returns None if blocked or empty."""
    if not allowed_by_robots(url):
        log.info("robots.txt disallows %s", url)
        return None
    try:
        r = client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as e:
        log.info("Fetch failed %s: %s", url, e)
        return None
    return trafilatura.extract(r.text, url=url, include_comments=False, favor_precision=True)


def get_or_create_source(session: Session, *, name: str, kind: str, url: str, lang: str, country: str | None = None) -> Source:
    src = session.scalar(select(Source).where(Source.url == url))
    if src is None:
        src = Source(name=name, kind=kind, url=url, lang=lang, country=country)
        session.add(src)
        session.flush()
    return src


def document_exists(session: Session, url: str) -> bool:
    return session.scalar(select(Document.id).where(Document.url == url)) is not None


def add_document(
    session: Session, *, source: Source, url: str, title: str, text: str, lang: str, published_at: datetime | None
) -> Document:
    doc = Document(source=source, url=url, title=title[:500], text=text, lang=lang, published_at=published_at)
    session.add(doc)
    return doc
