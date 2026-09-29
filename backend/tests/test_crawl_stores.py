"""Unattended store crawls: which stores are due, one crawl at a time, the crawl log, and the two commands.

Offline: BaseStoreCrawler.crawl is replaced by a fake that lists whatever a test says, so nothing reaches the network.
Every store here has a unique domain in the shared test database, and the lock file lives in a temp folder."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from click.testing import CliRunner
from sqlalchemy import select

from app.cli import cli
from app.collectors.stores import runner
from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import config_for, parse_store_configs
from app.collectors.stores.schemas import CrawlReport, ScrapedProduct
from app.collectors.stores.service import StoreSyncService
from app.db import SessionLocal, init_db
from app.models import Product, Source, StoreCrawl

HOUR = timedelta(hours=1)
DAY = 24 * HOUR
TEN = [f"s{i}" for i in range(10)]


def make_configs(n: int = 1, every: list[int] | None = None) -> dict:
    """n stores with unique domains; `every`: crawl_every_days for each (default 7)."""
    domains = [f"crawl-{uuid.uuid4().hex[:8]}.test" for _ in range(n)]
    yaml = "stores:\n" + "".join(
        f"  {d}:\n    name: Store {d[6:10]}\n    base_url: https://{d}\n    lang: fr\n"
        f"    listing: {{urls: ['/x'], product: 'li.card', link: 'a'}}\n"
        + (f"    crawl_every_days: {every[i]}\n" if every else "")
        for i, d in enumerate(domains))
    return parse_store_configs(yaml)


class FakeShops:
    """Stand-in for the network. behaviour[domain] = ("ok", slugs) | ("incomplete", slugs, problems) | ("raise", exc) | ("hang",)."""

    def __init__(self, monkeypatch):
        self.behaviour: dict[str, tuple] = {}
        self.calls: list[str] = []
        fake = self

        async def crawl(crawler):
            domain = crawler.config.domain
            fake.calls.append(domain)
            kind, *rest = fake.behaviour[domain]
            if kind == "raise":
                raise rest[0]
            if kind == "hang":
                await asyncio.sleep(30)
            slugs, problems = rest[0], (rest[1] if kind == "incomplete" else [])
            products = [ScrapedProduct(url=f"https://{domain}/p/{s}", name=s.upper(), seen_at=datetime.now(timezone.utc)) for s in slugs]
            crawler.report = CrawlReport(listed={p.db_url() for p in products}, problems=list(problems))
            return products

        monkeypatch.setattr(BaseStoreCrawler, "crawl", crawl)

    def ok(self, cfg, slugs=TEN):
        self.behaviour[cfg.domain] = ("ok", slugs)


@pytest.fixture(autouse=True)
def isolated():
    init_db()  # the lock file is already in a temp folder (conftest)


@pytest.fixture
def shops(monkeypatch):
    return FakeShops(monkeypatch)


def rows(cfg) -> list[StoreCrawl]:
    with SessionLocal() as s:
        source = s.scalar(select(Source).where(Source.url == str(cfg.base_url)))
        return [] if source is None else list(s.scalars(select(StoreCrawl).where(StoreCrawl.source_id == source.id).order_by(StoreCrawl.id)))


def products_of(cfg) -> int:
    with SessionLocal() as s:
        source = s.scalar(select(Source).where(Source.url == str(cfg.base_url)))
        return 0 if source is None else s.query(Product).filter(Product.source_id == source.id).count()


def add_crawl(cfg, status: str, finished_ago: timedelta, now: datetime) -> None:
    """A finished crawl in the log, `finished_ago` before `now`."""
    with SessionLocal() as s:
        source_id = StoreSyncService(s).source_for(cfg).id
        s.add(StoreCrawl(source_id=source_id, status=status, trigger="batch", started_at=now - finished_ago - HOUR,
                         finished_at=now - finished_ago))
        s.commit()


# --- which stores are due ---------------------------------------------------------------------------

@pytest.mark.parametrize("history, due, reason", [
    ([], True, "never crawled"),
    ([("ok", 3 * DAY)], False, "complete crawl 3 d ago"),
    ([("ok", 6.4 * DAY)], False, "complete crawl"),
    ([("ok", 6.6 * DAY)], True, "last complete crawl"),        # 7 d minus 12 h slack: a Monday 03:40 finish is due next Monday
    ([("ok", 8 * DAY), ("incomplete", 5 * HOUR)], False, "incomplete crawl 5 h ago"),
    ([("ok", 8 * DAY), ("incomplete", 21 * HOUR)], True, "retrying a incomplete crawl"),
    ([("ok", 8 * DAY), ("failed", 5 * HOUR)], False, "failed crawl 5 h ago"),
    ([("ok", 8 * DAY), ("failed", 21 * HOUR)], True, "retrying a failed crawl"),
    ([("ok", 1 * DAY), ("failed", 5 * HOUR)], False, "complete crawl"),   # a recent complete crawl beats a later failure
    ([("failed", 21 * HOUR)], True, "no complete crawl yet"),
    ([("failed", 5 * HOUR)], False, "failed crawl 5 h ago"),
])
def test_due_follows_the_last_complete_crawl_and_retries_the_next_day(history, due, reason):
    now = datetime.now(timezone.utc)
    (cfg,) = make_configs().values()
    for status, ago in history:
        add_crawl(cfg, status, ago, now)
    with SessionLocal() as s:
        decision = runner.decide(s, cfg, now)
    assert (decision.due, reason in decision.reason) == (due, True), decision.reason


def test_cadence_is_per_store_and_force_ignores_it():
    now = datetime.now(timezone.utc)
    weekly, every_three = make_configs(2, every=[7, 3]).values()
    for cfg in (weekly, every_three):
        add_crawl(cfg, "ok", 4 * DAY, now)
    with SessionLocal() as s:
        assert [runner.decide(s, c, now).due for c in (weekly, every_three)] == [False, True]
        assert runner.decide(s, weekly, now, force=True) == runner.Decision(weekly, True, "forced")


def test_a_crawl_still_running_does_not_count_as_finished():
    now = datetime.now(timezone.utc)
    (cfg,) = make_configs().values()
    with SessionLocal() as s:
        s.add(StoreCrawl(source_id=StoreSyncService(s).source_for(cfg).id, status="running", trigger="batch", started_at=now - HOUR))
        s.commit()
        assert runner.decide(s, cfg, now).reason == "never crawled"


def test_plan_names_an_unknown_domain():
    configs = make_configs(2)
    with pytest.raises(KeyError):
        runner.plan(configs, ("nope.test",))
    assert [d.cfg.domain for d in runner.plan(configs, (next(iter(configs)),))] == [next(iter(configs))]


# --- crawling one store -----------------------------------------------------------------------------

def test_a_complete_crawl_is_logged_with_its_counts(shops):
    (cfg,) = make_configs().values()
    shops.ok(cfg)
    outcome = runner.run_store(cfg, "batch")
    assert (outcome.status, outcome.crawled, outcome.listed, outcome.result.inserted) == ("ok", 10, 10, 10)
    (row,) = rows(cfg)
    assert (row.status, row.trigger, row.listed, row.crawled, row.inserted, row.updated, row.reactivated, row.dropped) == (
        "ok", "batch", 10, 10, 10, 0, 0, 0)
    assert row.finished_at is not None and row.error is None and row.problems is None and row.drop_skipped is None

    shops.ok(cfg, TEN[:9])                                                     # s9 left the catalog
    runner.run_store(cfg, "single")
    assert (rows(cfg)[1].trigger, rows(cfg)[1].dropped, rows(cfg)[1].updated) == ("single", 1, 9)


def test_an_incomplete_crawl_is_synced_but_logged_with_its_problems_and_drops_nothing(shops):
    (cfg,) = make_configs().values()
    shops.ok(cfg)
    runner.run_store(cfg, "batch")
    shops.behaviour[cfg.domain] = ("incomplete", TEN[:3], ["/x page 2: not fetched"])
    outcome = runner.run_store(cfg, "batch")
    assert outcome.status == "incomplete" and outcome.needs_attention and outcome.problems == ["/x page 2: not fetched"]
    row = rows(cfg)[1]
    assert (row.status, row.problems, row.dropped, row.crawled) == ("incomplete", ["/x page 2: not fetched"], 0, 3)
    assert row.drop_skipped.startswith("incomplete crawl")


def test_a_listing_that_shrank_is_ok_but_needs_attention_and_is_not_retried(shops):
    (cfg,) = make_configs().values()
    shops.ok(cfg)
    runner.run_store(cfg, "batch")
    shops.ok(cfg, TEN[:5])
    outcome = runner.run_store(cfg, "batch")
    assert outcome.status == "ok" and outcome.needs_attention and outcome.result.drop_skipped == "listing shrank 10 -> 5"
    with SessionLocal() as s:
        assert runner.decide(s, cfg, datetime.now(timezone.utc)).due is False   # reading it again would say the same


def test_a_failing_crawl_is_logged_and_writes_no_product(shops):
    (cfg,) = make_configs().values()
    shops.behaviour[cfg.domain] = ("raise", RuntimeError("boom"))
    outcome = runner.run_store(cfg, "batch")                                   # does not raise
    assert (outcome.status, outcome.error) == ("failed", "RuntimeError: boom")
    (row,) = rows(cfg)
    assert (row.status, row.error, row.crawled) == ("failed", "RuntimeError: boom", None) and row.finished_at is not None
    assert products_of(cfg) == 0


def test_a_hung_crawl_times_out_as_a_failure(shops, monkeypatch):
    (cfg,) = make_configs().values()
    shops.behaviour[cfg.domain] = ("hang",)
    monkeypatch.setattr(runner, "STORE_TIMEOUT", 0.05)
    outcome = runner.run_store(cfg, "batch")
    assert outcome.status == "failed" and outcome.error.startswith("TimeoutError") and products_of(cfg) == 0


# --- crawling every due store -----------------------------------------------------------------------

def test_one_failing_store_never_stops_the_others(shops):
    a, b, c = make_configs(3).values()
    shops.ok(a)
    shops.behaviour[b.domain] = ("raise", ConnectionError("blocked"))
    shops.ok(c)
    decisions, outcomes = runner.run_due({x.domain: x for x in (a, b, c)})
    assert [o.status for o in outcomes] == ["ok", "failed", "ok"] and all(d.due for d in decisions)
    assert (products_of(a), products_of(b), products_of(c)) == (10, 0, 10)


def test_running_twice_in_a_row_crawls_nothing_the_second_time(shops):
    configs = make_configs(2)
    for cfg in configs.values():
        shops.ok(cfg)
    runner.run_due(configs)
    calls, logged = list(shops.calls), {c.domain: len(rows(c)) for c in configs.values()}
    decisions, outcomes = runner.run_due(configs)
    assert outcomes == [] and not any(d.due for d in decisions)
    assert shops.calls == calls and {c.domain: len(rows(c)) for c in configs.values()} == logged   # no request, no row


def test_a_failed_store_is_retried_after_20_hours_not_before(shops):
    (cfg,) = make_configs().values()
    shops.behaviour[cfg.domain] = ("raise", RuntimeError("boom"))
    runner.run_due({cfg.domain: cfg})
    assert runner.run_due({cfg.domain: cfg})[1] == []                          # too soon
    with SessionLocal() as s:                                                  # 21 h later
        s.get(StoreCrawl, rows(cfg)[0].id).finished_at = datetime.now(timezone.utc) - 21 * HOUR
        s.commit()
    shops.ok(cfg)
    (outcome,) = runner.run_due({cfg.domain: cfg})[1]
    assert outcome.status == "ok"


def test_a_crawl_left_running_by_a_dead_process_is_marked_interrupted(shops):
    (cfg,) = make_configs().values()
    shops.ok(cfg)
    with SessionLocal() as s:
        s.add(StoreCrawl(source_id=StoreSyncService(s).source_for(cfg).id, status="running", trigger="batch"))
        s.commit()
    runner.run_due({cfg.domain: cfg})
    old, new = rows(cfg)
    assert (old.status, old.error.split(":")[0], old.finished_at is not None) == ("failed", "interrupted", True)
    assert new.status == "ok"                      # and the interruption did not put the store into the 20 h back-off


def test_an_unknown_domain_is_refused_before_anything_is_crawled(shops):
    configs = make_configs()
    with pytest.raises(KeyError):
        runner.run_due(configs, only=("nope.test",))
    assert shops.calls == []


def test_named_stores_are_still_gated_by_their_cadence_unless_forced(shops):
    a, b = make_configs(2).values()
    configs = {a.domain: a, b.domain: b}
    shops.ok(a)
    shops.ok(b)
    add_crawl(a, "ok", 1 * DAY, datetime.now(timezone.utc))
    assert [o.cfg.domain for o in runner.run_due(configs, only=(a.domain, b.domain))[1]] == [b.domain]
    assert [o.cfg.domain for o in runner.run_due(configs, only=(a.domain,), force=True)[1]] == [a.domain]


# --- the lock ---------------------------------------------------------------------------------------

def test_the_lock_admits_one_holder_and_is_released_on_exit(tmp_path):
    path = tmp_path / "lock"
    with runner.crawl_lock(path):
        with pytest.raises(runner.CrawlBusy):
            with runner.crawl_lock(path):
                pass
    with runner.crawl_lock(path):                                              # free again
        pass


def test_the_lock_is_released_when_the_crawl_raises(tmp_path):
    path = tmp_path / "lock"
    with pytest.raises(ValueError):
        with runner.crawl_lock(path):
            raise ValueError("crash")
    with runner.crawl_lock(path):
        pass


# --- the commands -----------------------------------------------------------------------------------

@pytest.fixture
def cli_stores(monkeypatch, shops):
    """crawl-store(s) working on two fake stores."""
    configs = make_configs(2)
    monkeypatch.setattr("app.cli.load_store_configs", lambda: configs)
    monkeypatch.setattr("app.cli.config_for", lambda domain: config_for(domain, configs))
    for cfg in configs.values():
        shops.ok(cfg)
    return configs


def run_cli(*args):
    return CliRunner().invoke(cli, list(args))


def test_dry_run_lists_what_is_due_and_touches_nothing(cli_stores, shops):
    result = run_cli("crawl-stores", "--dry-run")
    assert result.exit_code == 0 and result.stdout.count("DUE") == 2 and "never crawled" in result.stdout
    assert "2 of 2 stores due (dry run: nothing crawled)" in result.stdout
    assert shops.calls == [] and all(rows(cfg) == [] for cfg in cli_stores.values())


def test_crawl_stores_crawls_what_is_due_then_reports_nothing_to_do(cli_stores, shops):
    result = run_cli("crawl-stores")
    assert result.exit_code == 0, result.output
    assert "2 of 2 stores due" in result.stdout and result.stdout.count("10 products crawled — inserted 10") == 2
    assert "done: 2 ok, 0 need attention, 0 failed" in result.stdout
    calls = list(shops.calls)
    again = run_cli("crawl-stores")
    assert again.exit_code == 0 and "0 of 2 stores due: nothing to do" in again.stdout and "skip" in again.stdout
    assert shops.calls == calls                                                # idempotent: no request the second time


def test_exit_code_1_when_a_store_failed_and_the_other_still_ran(cli_stores, shops):
    a, b = cli_stores.values()
    shops.behaviour[a.domain] = ("raise", RuntimeError("boom"))
    result = run_cli("crawl-stores")
    assert result.exit_code == 1 and "FAILED — RuntimeError: boom" in result.stdout
    assert "done: 1 ok, 0 need attention, 1 failed" in result.stdout and products_of(b) == 10


def test_exit_code_2_when_a_crawl_was_incomplete_but_nothing_failed(cli_stores, shops):
    a, _ = cli_stores.values()
    shops.behaviour[a.domain] = ("incomplete", TEN, ["/x page 2: not fetched"])
    result = run_cli("crawl-stores")
    assert result.exit_code == 2 and "1 need attention" in result.stdout
    assert "drops skipped" not in result.stdout or "/x page 2" in result.stdout


def test_crawl_stores_when_another_crawl_holds_the_lock_exits_quietly(cli_stores, shops):
    with runner.crawl_lock():
        result = run_cli("crawl-stores")
    assert result.exit_code == 0 and "another crawl is running" in result.stdout and shops.calls == []


def test_crawl_stores_rejects_an_unknown_domain_and_a_bad_config(cli_stores, shops, monkeypatch):
    result = run_cli("crawl-stores", "nope.test")
    assert result.exit_code == 1 and "no store config for" in result.stderr and shops.calls == []
    monkeypatch.setattr("app.cli.load_store_configs", lambda: (_ for _ in ()).throw(ValueError("store_configs.yaml: bad")))
    result = run_cli("crawl-stores")
    assert result.exit_code == 1 and "store_configs.yaml: bad" in result.stderr


def test_crawl_store_is_logged_as_single_and_counts_toward_the_cadence(cli_stores, shops):
    a, _ = cli_stores.values()
    result = run_cli("crawl-store", a.domain)
    assert result.exit_code == 0 and "10 products crawled — inserted 10" in result.stdout
    assert [r.trigger for r in rows(a)] == ["single"]
    assert "skip" in run_cli("crawl-stores", "--dry-run").stdout                # a manual crawl makes the store not due
    shops.behaviour[a.domain] = ("raise", RuntimeError("boom"))
    failed = run_cli("crawl-store", a.domain)
    assert failed.exit_code == 1 and "FAILED — RuntimeError: boom" in failed.stdout
    with runner.crawl_lock():
        busy = run_cli("crawl-store", a.domain)
    assert busy.exit_code == 1 and "another crawl is running" in busy.stderr
