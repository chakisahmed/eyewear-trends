"""Backfill against a fake site (httpx MockTransport): no real network."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

import app.collectors.backfill as backfill
import app.collectors.base as base
from app.db import SessionLocal, init_db
from app.models import Document

NOW = datetime.now(timezone.utc)


def rfc822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def page(title, published, body):
    return (f'<html><head><title>{title}</title><meta property="article:published_time" content="{published.isoformat()}">'
            f'</head><body><article><h1>{title}</h1><p>{body}</p><p>{body}</p></article></body></html>')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    init_db()
    monkeypatch.setattr(backfill, "DELAY_S", 0)
    monkeypatch.setattr(base, "allowed_by_robots", lambda url: True)


def client_for(routes: dict[str, str]):
    seen = []
    def handler(request: httpx.Request):
        seen.append(str(request.url))
        body = routes.get(str(request.url))
        return httpx.Response(200, text=body) if body is not None else httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_paged_feed_stops_at_the_cutoff_and_keeps_real_dates():
    def rss(items):
        return "<rss><channel>" + "".join(
            f"<item><title>{t}</title><link>{l}</link><description>{d}</description><pubDate>{rfc822(p)}</pubDate></item>"
            for t, l, d, p in items) + "</channel></rss>"
    feed = "https://trade.test/feed/"
    recent, older, too_old = NOW - timedelta(days=3), NOW - timedelta(days=40), NOW - timedelta(days=200)
    client, seen = client_for({
        f"{feed}?paged=1": rss([("New cat-eye frames", "https://trade.test/a1", "cat-eye glasses launch", recent),
                                ("Earnings call", "https://trade.test/a2", "quarterly revenue", recent)]),
        f"{feed}?paged=2": rss([("Titanium sunglasses", "https://trade.test/a3", "sunglasses in titanium", older),
                                ("Archive piece", "https://trade.test/a4", "glasses from long ago", too_old)]),
        "https://trade.test/a1": page("New cat-eye frames", recent, "Cat-eye glasses in acetate."),
        "https://trade.test/a3": page("Titanium sunglasses", older, "Sunglasses in titanium."),
    })
    cfg = {"name": "Trade Test", "feed": feed, "method": "paged_feed", "lang": "en", "max_pages": 10}
    with SessionLocal() as s:
        added = backfill.backfill_paged_feed(s, client, cfg, since=NOW - timedelta(weeks=12), limit=100)
        docs = {d.url: d for d in s.scalars(select(Document).where(Document.url.like("https://trade.test/%")))}
    assert added == 2 and set(docs) == {"https://trade.test/a1", "https://trade.test/a3"}  # no earnings call, nothing too old
    assert docs["https://trade.test/a3"].published_at.date() == older.date()               # real publication date kept
    assert f"{feed}?paged=3" not in seen                                                    # stopped at the cutoff


def test_sitemap_walks_newest_first_with_section_filter():
    urls = [("https://vm.test/launchpad/frame-collection/old", NOW - timedelta(days=400)),
            ("https://vm.test/business/article/not-a-launch", NOW - timedelta(days=5)),
            ("https://vm.test/launchpad/frame-collection/new1", NOW - timedelta(days=20)),
            ("https://vm.test/launchpad/sunwear-collection/new2", NOW - timedelta(days=2))]
    routes = {"https://vm.test/sitemap.xml": "<urlset>" + "".join(f"<url><loc>{u}</loc></url>" for u, _ in urls) + "</urlset>"}
    for u, d in urls:
        routes[u] = page(u.rsplit("/", 1)[-1], d, "A new collection of optical frames and sunglasses in acetate.")
    client, seen = client_for(routes)
    cfg = {"name": "VM Test", "feed": "https://vm.test/rss", "method": "sitemap", "sitemap": "https://vm.test/sitemap.xml",
           "order": "oldest_first", "include": ["/launchpad/frame-collection", "/launchpad/sunwear-collection"], "lang": "en"}
    with SessionLocal() as s:
        added = backfill.backfill_sitemap(s, client, cfg, since=NOW - timedelta(weeks=12), limit=100)
        got = set(s.scalars(select(Document.url).where(Document.url.like("https://vm.test/%"))))
    assert added == 2 and got == {"https://vm.test/launchpad/frame-collection/new1", "https://vm.test/launchpad/sunwear-collection/new2"}
    assert "https://vm.test/business/article/not-a-launch" not in seen  # filtered out before downloading
    assert seen.index("https://vm.test/launchpad/sunwear-collection/new2") < seen.index("https://vm.test/launchpad/frame-collection/new1")


def test_sitemap_lastmod_skips_old_pages_without_downloading():
    old, new = NOW - timedelta(days=300), NOW - timedelta(days=10)
    routes = {
        "https://om.test/sitemap.xml": (f"<urlset><url><loc>https://om.test/old</loc><lastmod>{old.isoformat()}</lastmod></url>"
                                        f"<url><loc>https://om.test/new</loc><lastmod>{new.isoformat()}</lastmod></url></urlset>"),
        "https://om.test/new": page("Lunettes papillon", new, "Les lunettes papillon et les montures en acétate reviennent."),
    }
    client, seen = client_for(routes)
    cfg = {"name": "OM Test", "feed": "https://om.test/feed", "method": "sitemap", "sitemap": "https://om.test/sitemap.xml", "lang": "fr"}
    with SessionLocal() as s:
        assert backfill.backfill_sitemap(s, client, cfg, since=NOW - timedelta(weeks=12), limit=100) == 1
    assert "https://om.test/old" not in seen
