"""feeds.yaml rebalancing: the feed list, backfill compatibility, and inactive removed feeds."""

from sqlalchemy import select

from app.collectors.backfill import load_backfill_config
from app.collectors.rss_blogs import load_feeds, sync_feed_sources
from app.db import SessionLocal, init_db
from app.models import Source

REMOVED_US_LIFESTYLE = {"Vogue", "GQ", "Harper's Bazaar", "Esquire", "Who What Wear", "Fashionista"}


def test_feed_list_is_rebalanced_towards_french_trade_press():
    feeds = {f["name"]: f for f in load_feeds()}
    assert not REMOVED_US_LIFESTYLE & set(feeds)
    assert feeds["La Revue des Opticiens"] == {"name": "La Revue des Opticiens", "url": "https://larevuedesopticiens.com/rss-fr.xml",
                                              "lang": "fr", "country": "FR"}
    assert {"Optique Mag", "Vision Monday", "Invision", "WWD", "Hypebeast", "Vogue France"} <= set(feeds)
    assert sum(f["country"] == "FR" for f in feeds.values()) > sum(f["country"] == "US" for f in feeds.values())


def test_backfill_sources_are_still_listed_feeds():
    """Backfill reuses each feed's source row (same url): a backfill feed missing from the list would be
    marked inactive by the next RSS collection."""
    feed_urls = {f["url"] for f in load_feeds()}
    assert {b["feed"] for b in load_backfill_config()} <= feed_urls


def test_removed_feeds_become_inactive_and_other_kinds_are_untouched():
    init_db()
    with SessionLocal() as s:
        rows = {
            "kept": Source(name="Kept", kind="press", url="https://feeds.test/kept", lang="fr"),
            "dropped": Source(name="Dropped", kind="press", url="https://feeds.test/dropped", lang="en"),
            "store": Source(name="Shop", kind="store", url="https://feeds.test/shop", lang="fr"),
            "news": Source(name="News", kind="news", url="https://feeds.test/news", lang="fr"),
        }
        s.add_all(rows.values())
        s.commit()
        feeds = [{"name": "Kept", "url": "https://feeds.test/kept", "lang": "fr"}]
        sync_feed_sources(s, feeds)
        state = {k: s.scalar(select(Source.active).where(Source.url == r.url)) for k, r in rows.items()}
        assert state == {"kept": True, "dropped": False, "store": True, "news": True}

        feeds.append({"name": "Dropped", "url": "https://feeds.test/dropped", "lang": "en"})  # listed again
        sync_feed_sources(s, feeds)
        assert s.scalar(select(Source.active).where(Source.url == "https://feeds.test/dropped")) is True
