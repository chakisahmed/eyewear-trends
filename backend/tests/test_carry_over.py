"""A facet page that cannot be fetched must not erase what we already knew: carry_over on flags, the sync that uses it, and
how a crawl with such gaps is reported (incomplete, retried, drops unaffected). Offline, temp database."""

import copy
from datetime import datetime, timedelta, timezone

import pytest
from click.testing import CliRunner
from sqlalchemy import select

from app.cli import cli
from app.collectors.stores import runner
from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import config_for
from app.collectors.stores.schemas import CrawlReport, FacetGap, ScrapedProduct
from app.collectors.stores.service import carry_over
from app.db import SessionLocal, init_db
from app.models import Product, StoreCrawl
from tests.test_catalog_history import Shop
from tests.test_crawl_stores import make_configs, rows

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
WEEK = timedelta(days=7)
METAL = FacetGap("Materials", "Metal", url="https://s.test/collections/sun?filter=x")
BEST = FacetGap("Best-seller", "Yes", flag="is_bestseller", url="https://s.test/collections/sun?filter=y")
RED = FacetGap("Couleur", "Red", per_variant=True, url="https://s.test/collections/optical?filter=z")


# --- the pure function -----------------------------------------------------------------------------

@pytest.mark.parametrize("old, new, gaps, expected", [
    # a plain facet: the failed label comes back, next to the labels this crawl did read
    ({"raw_specs": {"Materials": "Acetate, Metal"}}, {"raw_specs": {"Materials": "Acetate"}}, [METAL],
     {"raw_specs": {"Materials": "Acetate, Metal"}}),
    ({"raw_specs": {"Materials": "Metal"}}, {"is_bestseller": True}, [METAL],
     {"is_bestseller": True, "raw_specs": {"Materials": "Metal"}}),
    # a label the product never had is not invented; unrelated old labels are not carried
    ({"raw_specs": {"Materials": "Acetate"}}, {"raw_specs": {"Materials": "Acetate"}}, [METAL],
     {"raw_specs": {"Materials": "Acetate"}}),
    ({"raw_specs": {"Materials": "Titanium"}}, {"raw_specs": {}}, [METAL], {"raw_specs": {}}),
    # this crawl did read it: nothing to carry
    ({"raw_specs": {"Materials": "Metal"}}, {"raw_specs": {"Materials": "Metal"}}, [METAL], {"raw_specs": {"Materials": "Metal"}}),
    # a flag facet: unset now, known before (True or False)
    ({"is_bestseller": True}, {"raw_specs": {"Forme": "Round"}}, [BEST], {"raw_specs": {"Forme": "Round"}, "is_bestseller": True}),
    ({"is_bestseller": False}, {}, [BEST], {"is_bestseller": False}),
    ({"is_bestseller": True}, {"is_bestseller": False}, [BEST], {"is_bestseller": False}),        # a fresh answer wins
    # a per-variant facet: the old colour of the same code, only when it was exactly the gap's label
    ({"raw_specs": {"Couleur": "Red"}, "variants": [{"code": "RP01", "color": "Red"}, {"code": "BM02", "color": "Blue"}]},
     {"raw_specs": {"Couleur": "Blue"}, "variants": [{"code": "RP01"}, {"code": "BM02", "color": "Blue"}]}, [RED],
     {"raw_specs": {"Couleur": "Blue, Red"}, "variants": [{"code": "RP01", "color": "Red"}, {"code": "BM02", "color": "Blue"}]}),
    ({"variants": [{"code": "BM02", "color": "Blue"}]}, {"variants": [{"code": "BM02"}]}, [RED], {"variants": [{"code": "BM02"}]}),
])
def test_carry_over_keeps_only_what_a_failed_facet_kept_us_from_reading(old, new, gaps, expected):
    before = copy.deepcopy((old, new))
    assert carry_over(old, new, gaps) == expected
    assert (old, new) == before                                                 # never mutates


def test_carry_over_is_a_no_op_without_gaps_or_history():
    new = {"raw_specs": {"Materials": "Acetate"}}
    assert carry_over({"raw_specs": {"Materials": "Metal"}}, new, []) is new    # the same object: nothing was kept
    assert carry_over(None, new, [METAL]) is new and carry_over({}, new, [METAL]) is new
    assert carry_over({"raw_specs": {"Materials": "Metal"}}, None, [METAL]) == {"raw_specs": {"Materials": "Metal"}}
    assert carry_over({"raw_specs": {"Materials": "Metal"}}, new, [METAL, BEST]) == {"raw_specs": {"Materials": "Acetate, Metal"}}


# --- in the sync -----------------------------------------------------------------------------------

@pytest.fixture
def shop():
    init_db()
    with SessionLocal() as s:
        yield Shop(s)


def frame(shop, slug: str, materials: str, at, **flags):
    return ScrapedProduct(url=f"{shop.host}/p/{slug}", name=slug.upper(), seen_at=at,
                          flags={"raw_specs": {"Materials": materials}, **flags})


def material_tags(shop, slug: str) -> set[str]:
    shop.session.expire_all()
    product = shop.session.scalar(select(Product).where(Product.url == f"{shop.host}/p/{slug}"))
    return {t.code for t in product.tags if t.dimension == "material"}


def test_a_failed_facet_page_keeps_the_material_tag_and_the_best_seller_flag(shop):
    listed = [f"{shop.host}/p/{s}" for s in ("sun1", "sun2")]
    shop.service.sync(shop.source.id, [frame(shop, "sun1", "Acetate, Metal", T0, is_bestseller=True),
                                       frame(shop, "sun2", "Metal", T0)], CrawlReport(listed=set(listed)))
    assert material_tags(shop, "sun1") == {"acetate", "metal"} and material_tags(shop, "sun2") == {"metal"}

    gaps = [FacetGap("Materials", "Metal", url=f"{shop.host}/collections/sun?m"), FacetGap("Best-seller", "Yes", flag="is_bestseller", url=f"{shop.host}/b")]
    report = CrawlReport(listed=set(listed), gaps=gaps)                         # the crawl could not read Metal or Best-seller
    result = shop.service.sync(shop.source.id, [frame(shop, "sun1", "Acetate", T0 + WEEK), frame(shop, "sun2", "", T0 + WEEK)], report)
    assert (result.updated, result.carried, result.dropped) == (2, 2, 0)
    assert material_tags(shop, "sun1") == {"acetate", "metal"} and material_tags(shop, "sun2") == {"metal"}
    sun1 = shop.session.scalar(select(Product).where(Product.url == listed[0]))
    assert sun1.flags["is_bestseller"] is True and sun1.flags["raw_specs"]["Materials"] == "Acetate, Metal"

    result = shop.service.sync(shop.source.id, [frame(shop, "sun1", "Acetate", T0 + 2 * WEEK), frame(shop, "sun2", "Acetate", T0 + 2 * WEEK)],
                               CrawlReport(listed=set(listed)))                 # a crawl with no gap tells the truth again
    assert result.carried == 0 and material_tags(shop, "sun1") == {"acetate"} and material_tags(shop, "sun2") == {"acetate"}


def test_new_products_have_nothing_to_carry_and_other_sources_are_never_touched(shop):
    other = Shop(shop.session)
    other.service.sync(other.source.id, [frame(other, "x", "Metal", T0)], CrawlReport(listed={f"{other.host}/p/x"}))
    gap = FacetGap("Materials", "Metal", url=f"{shop.host}/m")
    result = shop.service.sync(shop.source.id, [frame(shop, "fresh", "Acetate", T0)], CrawlReport(listed={f"{shop.host}/p/fresh"}, gaps=[gap]))
    assert (result.inserted, result.carried) == (1, 0) and material_tags(shop, "fresh") == {"acetate"}
    assert material_tags(other, "x") == {"metal"}


# --- how the crawl is reported ---------------------------------------------------------------------

def fake_crawl(monkeypatch, slugs, gaps=(), problems=()):
    async def crawl(self):
        products = [ScrapedProduct(url=f"https://{self.config.domain}/p/{s}", name=s.upper(), seen_at=datetime.now(timezone.utc),
                                   flags={"raw_specs": {"Materials": "Acetate"}}) for s in slugs]
        self.report = CrawlReport(listed={p.db_url() for p in products}, problems=list(problems), gaps=list(gaps))
        return products
    monkeypatch.setattr(BaseStoreCrawler, "crawl", crawl)


TEN = [f"s{i}" for i in range(10)]


def test_a_crawl_with_facet_gaps_is_incomplete_but_still_drops_what_left_the_listing(monkeypatch):
    (cfg,) = make_configs().values()
    fake_crawl(monkeypatch, TEN)
    assert runner.run_store(cfg, "batch").status == "ok"
    gap = FacetGap("Materials", "Metal", url=f"https://{cfg.domain}/collections/sun?m")
    fake_crawl(monkeypatch, TEN[:9], gaps=[gap])                                # s9 left; one facet page failed
    outcome = runner.run_store(cfg, "batch")
    assert outcome.status == "incomplete" and outcome.needs_attention and outcome.result.dropped == 1   # the listing was whole
    assert outcome.problems == [f"facet Materials = Metal (/collections/sun): not fetched"]
    row = rows(cfg)[1]
    assert (row.status, row.problems, row.drop_skipped, row.dropped) == ("incomplete", outcome.problems, None, 1)


def test_a_store_due_for_a_week_whose_crawl_had_gaps_is_retried_the_next_day(monkeypatch):
    from tests.test_crawl_stores import add_crawl
    (cfg,) = make_configs().values()
    now = datetime.now(timezone.utc)
    add_crawl(cfg, "ok", 8 * timedelta(days=1), now)                            # last complete crawl 8 days ago: due
    fake_crawl(monkeypatch, TEN, gaps=[FacetGap("Materials", "Metal", url=f"https://{cfg.domain}/m")])
    assert runner.run_store(cfg, "batch").status == "incomplete"
    with SessionLocal() as s:
        assert runner.decide(s, cfg, datetime.now(timezone.utc)).due is False   # not hammered straight away
        assert runner.decide(s, cfg, datetime.now(timezone.utc) + timedelta(hours=21)).due is True   # tomorrow, not next week


def test_a_gap_and_a_listing_problem_are_both_listed_and_the_listing_problem_still_blocks_drops(monkeypatch):
    (cfg,) = make_configs().values()
    fake_crawl(monkeypatch, TEN)
    runner.run_store(cfg, "batch")
    gap = FacetGap("Materials", "Metal", url=f"https://{cfg.domain}/m")
    fake_crawl(monkeypatch, TEN[:5], gaps=[gap], problems=["/x page 2: not fetched"])
    outcome = runner.run_store(cfg, "batch")
    assert outcome.problems == ["/x page 2: not fetched", "facet Materials = Metal (/m): not fetched"]
    assert outcome.result.dropped == 0 and outcome.result.drop_skipped.startswith("incomplete crawl: /x page 2")


def test_the_command_says_what_was_kept_and_why_the_crawl_is_incomplete(monkeypatch):
    configs = make_configs(1)
    (cfg,) = configs.values()
    monkeypatch.setattr("app.cli.load_store_configs", lambda: configs)
    monkeypatch.setattr("app.cli.config_for", lambda domain: config_for(domain, configs))
    fake_crawl(monkeypatch, TEN)
    assert CliRunner().invoke(cli, ["crawl-store", cfg.domain]).exit_code == 0
    gap = FacetGap("Materials", "Metal", url=f"https://{cfg.domain}/collections/sun?m")
    with SessionLocal() as s:                                                   # a previous value to keep: Metal on s0
        product = s.scalar(select(Product).where(Product.url == f"https://{cfg.domain}/p/s0"))
        product.flags = {"raw_specs": {"Materials": "Acetate, Metal"}}
        s.commit()
    fake_crawl(monkeypatch, TEN, gaps=[gap])
    result = CliRunner().invoke(cli, ["crawl-stores", "--force"])
    assert result.exit_code == 2, result.output                                 # nothing failed, but it needs a look
    assert "kept previous values for 1" in result.stdout and "some pages could not be fetched" in result.stdout
    assert "facet Materials = Metal (/collections/sun): not fetched" in result.stdout
    assert "1 need attention" in result.stdout
