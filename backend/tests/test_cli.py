"""CLI (click): crawl-store end to end with the crawl mocked, so nothing reaches the internet."""

from datetime import datetime, timezone

import anthropic
import pytest
from click.testing import CliRunner
from sqlalchemy import select

import app.extraction.llm as llm
from app.cli import cli
from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.schemas import CrawlReport, ScrapedProduct
from app.db import SessionLocal
from app.models import Product, Source

DOMAIN = "outika-eyewear.tn"
SHOP = "https://www.outika-eyewear.tn/shop/cli-test"


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """Zero-LLM rule: any Claude call during these commands fails the test."""
    def forbidden(*a, **kw):
        raise AssertionError("LLM called from the CLI store path")
    monkeypatch.setattr(llm, "get_provider", forbidden)
    monkeypatch.setattr(anthropic.Anthropic, "__init__", forbidden)


def fake_crawl(prices: dict[str, float], problems: list[str] | None = None):
    """A crawl that lists exactly `prices`; `problems` makes its listing incomplete."""
    async def crawl(self):
        assert self.config.domain == DOMAIN  # the CLI built the crawler from the YAML entry
        products = [ScrapedProduct(url=f"{SHOP}-{slug}/", name=slug.upper(), brand="Outika", price=price, currency="TND",
                                   rank=i, flags={"raw_specs": {"Materials": "Acetate"}}, seen_at=datetime.now(timezone.utc))
                    for i, (slug, price) in enumerate(prices.items(), start=1)]
        self.report = CrawlReport(listed={p.db_url() for p in products}, problems=problems or [])
        return products
    return crawl


def rows() -> dict[str, Product]:
    with SessionLocal() as s:
        return {p.url: p for p in s.scalars(select(Product).where(Product.url.like(f"{SHOP}-%")))}


def test_crawl_store_inserts_then_updates(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(BaseStoreCrawler, "crawl", fake_crawl({"adonia": 45.0, "evan": 49.0}))
    result = runner.invoke(cli, ["crawl-store", DOMAIN])
    assert result.exit_code == 0, result.output
    assert "Outika: 2 products crawled — inserted 2, updated 0, conflicts 0" in result.stdout

    stored = rows()
    assert {u: (p.name, p.price, p.currency, p.rank) for u, p in stored.items()} == {
        f"{SHOP}-adonia/": ("ADONIA", 45.0, "TND", 1), f"{SHOP}-evan/": ("EVAN", 49.0, "TND", 2)}
    with SessionLocal() as s:
        source = s.get(Source, next(iter(stored.values())).source_id)
        assert (source.kind, source.country, source.url) == ("store", "TN", "https://www.outika-eyewear.tn/")

    monkeypatch.setattr(BaseStoreCrawler, "crawl", fake_crawl({"adonia": 39.0, "evan": 49.0}))
    result = runner.invoke(cli, ["crawl-store", "www.outika-eyewear.tn"])  # "www." is ignored
    assert result.exit_code == 0, result.output
    assert "inserted 0, updated 2, conflicts 0" in result.stdout
    assert rows()[f"{SHOP}-adonia/"].price == 39.0


def test_crawl_store_drops_what_the_listing_no_longer_returns_and_says_so(monkeypatch):
    runner = CliRunner()
    names = {f"c{i}": 10.0 + i for i in range(10)}
    monkeypatch.setattr(BaseStoreCrawler, "crawl", fake_crawl(names))
    assert runner.invoke(cli, ["crawl-store", DOMAIN]).exit_code == 0

    def active() -> dict[str, bool]:
        with SessionLocal() as s:
            return {p.name: p.is_active for p in s.scalars(select(Product).where(Product.url.like(f"{SHOP}-c%")))}

    monkeypatch.setattr(BaseStoreCrawler, "crawl", fake_crawl({k: v for k, v in names.items() if k != "c9"}))
    out = runner.invoke(cli, ["crawl-store", DOMAIN]).stdout
    assert "reactivated 0, dropped 1" in out and active()["C9"] is False and active()["C0"] is True
    assert runner.invoke(cli, ["crawl-store", DOMAIN]).stdout.count("dropped 0") == 1  # a re-run changes nothing

    monkeypatch.setattr(BaseStoreCrawler, "crawl", fake_crawl(names))                   # c9 is back
    assert "reactivated 1, dropped 0" in runner.invoke(cli, ["crawl-store", DOMAIN]).stdout and active()["C9"] is True

    monkeypatch.setattr(BaseStoreCrawler, "crawl", fake_crawl({"c0": 1.0}, problems=["/shop page 2: not fetched"]))
    out = runner.invoke(cli, ["crawl-store", DOMAIN, "--accept-drops"]).stdout          # never overrides an incomplete crawl
    assert "dropped 0" in out and "drops skipped: incomplete crawl: /shop page 2: not fetched" in out
    assert all(active().values())

    monkeypatch.setattr(BaseStoreCrawler, "crawl", fake_crawl({"c0": 1.0}))             # complete, but 1 of 10 listed
    out = runner.invoke(cli, ["crawl-store", DOMAIN]).stdout
    assert "dropped 0" in out and "listing shrank" in out and "--accept-drops" in out and all(active().values())
    out = runner.invoke(cli, ["crawl-store", DOMAIN, "--accept-drops"]).stdout
    assert "dropped 9" in out and [n for n, on in active().items() if on] == ["C0"]


def test_crawl_store_unknown_domain_exits_1_without_db_writes(monkeypatch):
    async def must_not_crawl(self):
        raise AssertionError("crawl started for an unknown domain")
    monkeypatch.setattr(BaseStoreCrawler, "crawl", must_not_crawl)
    with SessionLocal() as s:
        before = s.query(Product).count(), s.query(Source).count()
    result = CliRunner().invoke(cli, ["crawl-store", "unknown.tn"])
    assert result.exit_code == 1
    assert "no store config for 'unknown.tn'" in result.stderr and DOMAIN in result.stderr
    with SessionLocal() as s:
        assert (s.query(Product).count(), s.query(Source).count()) == before


def test_existing_commands_still_work_under_click():
    runner = CliRunner()
    result = runner.invoke(cli, ["seed-demo"])
    assert result.exit_code == 0 and "demo documents" in result.stdout
    result = runner.invoke(cli, ["clear-demo"])
    assert result.exit_code == 0 and "demo data removed" in result.stdout
    result = runner.invoke(cli, [])
    assert result.exit_code in (0, 2) and "crawl-store" in result.output  # bare invocation shows help


def test_retag_products(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(BaseStoreCrawler, "crawl", fake_crawl({"retag": 45.0}))
    assert runner.invoke(cli, ["crawl-store", DOMAIN]).exit_code == 0  # fake products carry Materials: Acetate
    result = runner.invoke(cli, ["retag-products", DOMAIN])
    assert result.exit_code == 0, result.output
    assert "products re-tagged" in result.stdout and "material" in result.stdout
    result = runner.invoke(cli, ["retag-products"])                    # all stores
    assert result.exit_code == 0 and "products re-tagged" in result.stdout
    result = runner.invoke(cli, ["retag-products", "unknown.tn"])
    assert result.exit_code == 1 and "no store config" in result.stderr
