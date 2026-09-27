"""Daily sitemap collection (sources without RSS, e.g. Acuité) against a fake site: no real network."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

import app.collectors.base as base
import app.collectors.sitemap_news as sitemap_news
from app.collectors.rss_blogs import load_feeds, sync_feed_sources
from app.db import SessionLocal, init_db
from app.models import Document, Source

NOW = datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc)
SITE = "https://news.test"


def page(title: str, published: datetime, body: str) -> str:
    return (f'<html><head><title>{title}</title><meta property="article:published_time" content="{published.isoformat()}">'
            f'</head><body><article><h1>{title}</h1><p>{body}</p><p>{body}</p><p>{body}</p></article></body></html>')


def urlset(entries: list[tuple[str, datetime | None]]) -> str:
    return "<urlset>" + "".join(
        f"<url><loc>{u}</loc>" + (f"<lastmod>{d.isoformat()}</lastmod>" if d else "") + "</url>" for u, d in entries) + "</urlset>"


CFG = {"name": "News Test", "url": f"{SITE}/", "sitemap": f"{SITE}/sitemap.xml", "include": ["/actualites/lunettes/"],
       "lang": "fr", "country": "FR", "lookback_days": 7, "max_checked": 10, "max_new": 10}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    init_db()
    monkeypatch.setattr(sitemap_news, "DELAY_S", 0)
    monkeypatch.setattr(base, "allowed_by_robots", lambda url: "/blocked" not in url)


def fake_site(requested: list[str]):
    day = timedelta(days=1)
    art = lambda slug: f"{SITE}/actualites/lunettes/{slug}"
    routes = {
        f"{SITE}/sitemap.xml": (f"<sitemapindex><sitemap><loc>{SITE}/sitemap.xml?page=1</loc></sitemap>"
                                f"<sitemap><loc>{SITE}/sitemap.xml?page=2</loc></sitemap></sitemapindex>"),
        f"{SITE}/sitemap.xml?page=1": urlset([
            (art("new-frames"), NOW - day),                                   # kept
            (art("old-but-edited"), NOW - day),                               # lastmod recent, published long ago
            (f"{SITE}/actualites/profession/legislation-x", NOW - day),       # outside include: never fetched
            (art("ancient"), NOW - 60 * day),                                 # lastmod too old: never fetched
        ]),
        f"{SITE}/sitemap.xml?page=2": urlset([
            (art("lens-business"), NOW - 2 * day),                            # no eyewear words: skipped
            (art("newest-frames"), NOW - timedelta(hours=3)),                 # kept, checked first
            (art("blocked"), NOW - day),                                      # robots.txt: never fetched
            (art("no-lastmod"), None),                                        # no lastmod: not a daily candidate
        ]),
        art("new-frames"): page("Lunettes papillon au Silmo", NOW - day, "Les montures papillon en acétate reviennent."),
        art("old-but-edited"): page("Lunettes rondes 2019", NOW - 900 * day, "Les lunettes rondes en 2019."),
        art("lens-business"): page("Résultats financiers", NOW - 2 * day, "Le chiffre d'affaires progresse au trimestre."),
        art("newest-frames"): page("Tendance lunettes œil de chat", NOW - timedelta(hours=3), "Les lunettes œil de chat dominent."),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        return httpx.Response(200, text=routes[url]) if url in routes else httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def docs() -> dict[str, Document]:
    with SessionLocal() as s:
        return {d.url.rsplit("/", 1)[-1]: d for d in s.scalars(select(Document).where(Document.url.like(f"{SITE}/%")))}


def test_collects_recent_eyewear_articles_by_page_date():
    requested: list[str] = []
    with SessionLocal() as s, fake_site(requested) as client:
        added = sitemap_news.collect_sitemap_source(s, client, CFG, now=NOW)
        source = s.scalar(select(Source).where(Source.url == f"{SITE}/"))
    got = docs()
    assert added == 2 and set(got) == {"new-frames", "newest-frames"}
    assert got["newest-frames"].published_at.replace(tzinfo=timezone.utc).date() == NOW.date()  # page date kept
    assert (source.kind, source.country, source.lang) == ("press", "FR", "fr")
    assert not any(slug in u for u in requested for slug in ("legislation-x", "ancient", "blocked", "no-lastmod"))
    checked = [u.rsplit("/", 1)[-1] for u in requested if "/actualites/" in u]
    assert checked[0] == "newest-frames"                                   # newest lastmod first

    requested.clear()
    with SessionLocal() as s, fake_site(requested) as client:              # next day: nothing new, no refetch
        assert sitemap_news.collect_sitemap_source(s, client, CFG, now=NOW) == 0
    assert not any(u.endswith(("new-frames", "newest-frames")) for u in requested)


def test_caps_bound_pages_checked_and_articles_kept():
    requested: list[str] = []
    cfg = {**CFG, "url": f"{SITE}/capped/", "max_new": 1, "max_checked": 2}
    with SessionLocal() as s, fake_site(requested) as client:
        s.execute(Document.__table__.delete().where(Document.url.like(f"{SITE}/%")))
        s.commit()
        assert sitemap_news.collect_sitemap_source(s, client, cfg, now=NOW) == 1
    assert set(docs()) == {"newest-frames"}
    assert len([u for u in requested if "/actualites/" in u]) == 1         # stopped once max_new was reached


def test_acuite_is_configured_and_kept_active():
    (acuite,) = [c for c in sitemap_news.load_sitemap_sources() if c["name"] == "Acuité"]
    assert acuite["sitemap"] == "https://www.acuite.fr/sitemap.xml" and acuite["include"] == ["/actualites/lunettes/"]
    assert acuite["max_new"] <= 15  # Claude cost guard: ~$0.01 per analysed article
    with SessionLocal() as s:
        s.add(Source(name="Acuité", kind="press", url=acuite["url"], lang="fr", country="FR", active=False))
        s.commit()
        sync_feed_sources(s, load_feeds() + sitemap_news.load_sitemap_sources())
        assert s.scalar(select(Source.active).where(Source.url == acuite["url"])) is True
