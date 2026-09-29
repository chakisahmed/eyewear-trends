"""Catalog history: first_seen_at, is_active and dropped_at kept true by StoreSyncService.sync, and the guards that stop
a partial crawl from "dropping" products that are still on the shelf. Offline, temp database."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.collectors.stores.schemas import CrawlReport, ScrapedProduct
from app.collectors.stores.service import StoreSyncService
from app.db import SessionLocal, init_db
from app.models import Product, Source

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
WEEK = timedelta(days=7)
TEN = [f"s{i}" for i in range(10)]  # a catalog big enough that one product leaving is not a suspicious shrink


class Shop:
    """One fake store in the shared test database (unique host per test, so tests never see each other's rows)."""

    def __init__(self, session):
        self.session = session
        self.host = f"https://history-{uuid.uuid4().hex[:10]}.test"
        self.source = Source(name=self.host, kind="store", url=self.host, lang="fr")
        session.add(self.source)
        session.commit()
        self.service = StoreSyncService(session)

    def products(self, slugs, at) -> list[ScrapedProduct]:
        return [ScrapedProduct(url=f"{self.host}/p/{s}", name=s.upper(), seen_at=at) for s in slugs]

    def report(self, slugs, problems=()) -> CrawlReport:
        return CrawlReport(listed={f"{self.host}/p/{s}" for s in slugs}, problems=list(problems))

    def crawl(self, slugs, at, *, listed=None, problems=(), **kw):
        """One crawl: the listing returned `listed` (default: the same slugs), of which `slugs` became products."""
        return self.service.sync(self.source.id, self.products(slugs, at), self.report(listed if listed is not None else slugs, problems), **kw)

    def state(self) -> dict[str, tuple]:
        self.session.expire_all()
        aware = lambda d: d.replace(tzinfo=timezone.utc) if d else None
        return {p.url.rsplit("/", 1)[-1]: (p.is_active, aware(p.first_seen_at), aware(p.seen_at), aware(p.dropped_at))
                for p in self.session.scalars(select(Product).where(Product.source_id == self.source.id))}


@pytest.fixture
def shop():
    init_db()
    with SessionLocal() as s:
        yield Shop(s)


def test_a_new_product_is_first_seen_at_its_crawl_and_the_date_never_moves(shop):
    result = shop.crawl(["a", "b"], T0)
    assert (result.inserted, result.dropped, result.reactivated, result.drop_skipped) == (2, 0, 0, None)
    assert shop.state()["a"] == (True, T0, T0, None)
    shop.crawl(["a", "b"], T0 + WEEK)
    assert shop.state()["a"] == (True, T0, T0 + WEEK, None)                     # seen again: last seen moves, first seen stays


def test_a_product_the_listing_no_longer_returns_is_dropped_with_the_crawl_time(shop):
    shop.crawl(TEN, T0)
    result = shop.crawl(TEN[:9], T0 + WEEK)
    assert (result.updated, result.dropped, result.drop_skipped) == (9, 1, None)
    state = shop.state()
    assert state["s0"] == (True, T0, T0 + WEEK, None)
    assert state["s9"] == (False, T0, T0, T0 + WEEK)                            # seen_at of the dropped row is left alone


def test_a_dropped_product_that_comes_back_is_reactivated_and_keeps_its_first_seen_date(shop):
    shop.crawl(TEN, T0)
    shop.crawl(TEN[:9], T0 + WEEK)
    assert shop.state()["s9"][0] is False
    result = shop.crawl(TEN, T0 + 2 * WEEK)
    assert (result.reactivated, result.dropped, result.inserted, result.updated) == (1, 0, 0, 10)
    assert shop.state()["s9"] == (True, T0, T0 + 2 * WEEK, None)                # dropped_at cleared, first_seen_at intact


def test_running_the_same_crawl_twice_changes_nothing(shop):
    shop.crawl(TEN, T0)
    shop.crawl(TEN[:9], T0 + WEEK)
    before = shop.state()
    result = shop.crawl(TEN[:9], T0 + WEEK)
    assert (result.dropped, result.reactivated, result.inserted, result.drop_skipped) == (0, 0, 0, None)
    assert shop.state() == before                                               # not even dropped_at moves


def test_a_product_still_listed_but_missing_from_the_batch_is_not_dropped(shop):
    """Validation can drop a product that is still on the shelf: presence is decided on what the listing returned."""
    shop.crawl(TEN, T0)
    result = shop.crawl(TEN[:9], T0 + WEEK, listed=TEN)
    assert result.dropped == 0 and shop.state()["s9"] == (True, T0, T0, None)


def test_an_incomplete_crawl_drops_nothing_and_says_why(shop):
    shop.crawl(TEN, T0)
    result = shop.crawl(TEN[:3], T0 + WEEK, problems=["/lunettes page 2: not fetched", "/solaire page 3: not fetched"])
    assert result.dropped == 0
    assert result.drop_skipped == "incomplete crawl: /lunettes page 2: not fetched (+1 more)"
    assert all(active for active, *_ in shop.state().values())


def test_without_a_report_nothing_is_dropped(shop):
    shop.service.sync(shop.source.id, shop.products(TEN, T0))
    result = shop.service.sync(shop.source.id, shop.products(TEN[:9], T0 + WEEK))
    assert (result.dropped, result.drop_skipped) == (0, None) and shop.state()["s9"][0] is True


def test_a_listing_that_shrank_below_70_percent_drops_nothing_unless_accepted(shop):
    slugs = TEN
    shop.crawl(slugs, T0)
    result = shop.crawl(slugs[:6], T0 + WEEK)                                   # 6 of 10
    assert result.dropped == 0 and result.drop_skipped == "listing shrank 10 -> 6"
    assert all(active for active, *_ in shop.state().values())
    result = shop.crawl(slugs[:6], T0 + WEEK, accept_drops=True)                # a real cull, confirmed by the operator
    assert result.dropped == 4 and result.drop_skipped is None


def test_exactly_70_percent_is_enough_and_new_products_count_toward_the_listing(shop):
    slugs = TEN
    shop.crawl(slugs, T0)
    assert shop.crawl(slugs[:7], T0 + WEEK).dropped == 3                        # 7 of 10: not a shrink
    shop.crawl(slugs, T0 + 2 * WEEK)                                            # everything back
    assert shop.crawl(slugs[:5] + ["n1", "n2"], T0 + 3 * WEEK).dropped == 5     # 7 listed, two of them new


def test_accepting_drops_never_overrides_an_incomplete_crawl(shop):
    shop.crawl(TEN, T0)
    result = shop.crawl(TEN[:3], T0 + WEEK, problems=["/lunettes page 2: not fetched"], accept_drops=True)
    assert result.dropped == 0 and result.drop_skipped.startswith("incomplete crawl")


def test_the_first_crawl_of_a_store_has_nothing_to_drop_and_no_guard_to_trip(shop):
    result = shop.crawl(["a"], T0)
    assert (result.inserted, result.dropped, result.drop_skipped) == (1, 0, None)


def test_another_stores_products_are_never_touched(shop):
    other = Shop(shop.session)
    other.crawl(TEN, T0)
    shop.crawl(TEN, T0)
    shop.crawl(TEN[:9], T0 + WEEK)
    assert shop.state()["s9"][0] is False and all(active for active, *_ in other.state().values())
    # a url owned by another store stays a conflict, is not stolen, and is not dropped by either store
    stolen = [ScrapedProduct(url=f"{other.host}/p/s0", name="S0", seen_at=T0 + WEEK)]
    result = shop.service.sync(shop.source.id, stolen, CrawlReport(listed={f"{other.host}/p/s0"}), accept_drops=True)
    assert result.conflicts == 1 and other.state()["s0"] == (True, T0, T0, None)


def test_the_shelf_reads_is_active_not_the_age_of_seen_at(shop):
    from app.scoring import retail
    shop.crawl(TEN, datetime.now(timezone.utc) - 400 * timedelta(days=1))       # crawled long ago, never re-crawled
    shelf = lambda: {p.name for p, store in retail.active_products(shop.session) if store == shop.host}
    assert shelf() == {s.upper() for s in TEN}                                  # still on the shelf: nothing dropped them
    shop.crawl(TEN[:9], datetime.now(timezone.utc))
    assert shelf() == {s.upper() for s in TEN[:9]}                              # dropped by a crawl: off the shelf
