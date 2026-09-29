"""Run store crawls unattended: which stores are due, one crawl at a time, and a row in store_crawls for each.

Shared by `crawl-store` (one store, by hand) and `crawl-stores` (every due store, from Windows Task Scheduler). The
crawler never touches the database and the sync is one transaction per store (service.py), so a process killed mid-crawl
leaves products exactly as they were; its store_crawls row stays "running" and the next run marks it interrupted.

Due-ness is judged from the log, not from the clock alone: a store is due when its last complete (`ok`) crawl is older
than its cadence, so running the command daily costs nothing and a missed day is harmless; an `incomplete` or `failed`
crawl is retried after RETRY_AFTER rather than waiting a whole cadence, without hammering a broken store.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import or_, select, update

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import ScraperConfig, config_for
from app.collectors.stores.schemas import CrawlReport, ScrapedProduct
from app.collectors.stores.service import StoreSyncService, SyncResult
from app.config import BACKEND_DIR, settings
from app.db import SessionLocal
from app.models import Source, StoreCrawl

log = logging.getLogger(__name__)

LOCK_PATH = BACKEND_DIR / "data" / "crawl-stores.lock"
CADENCE_SLACK = timedelta(hours=12)  # a crawl that ended at 03:40 must not make next week's 03:00 run "not yet due"
RETRY_AFTER = timedelta(hours=20)  # an incomplete or failed crawl is retried the next day
STORE_TIMEOUT = 3 * 60 * 60  # seconds: a hung store must not block the others


INTERRUPTED = "interrupted"  # error prefix of a crawl whose process ended before it finished


class CrawlBusy(RuntimeError):
    """Another crawl process holds the lock."""


# --- one crawl process at a time --------------------------------------------------------------------

if os.name == "nt":
    import msvcrt

    def _try_lock(fh) -> None:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)  # OSError when another handle holds it

    def _unlock(fh) -> None:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _try_lock(fh) -> None:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)  # BlockingIOError (an OSError) when held

    def _unlock(fh) -> None:
        fcntl.flock(fh, fcntl.LOCK_UN)


@contextmanager
def crawl_lock(path: Path | None = None) -> Iterator[None]:
    """An OS file lock: released by the OS if the process dies, so there is no stale lock to clear (and no PID probing:
    on Windows os.kill(pid, 0) would terminate the process)."""
    path = path or LOCK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+b")
    try:
        try:
            _try_lock(fh)
        except OSError:
            raise CrawlBusy(f"another crawl is running (lock: {path})") from None
        try:
            yield
        finally:
            _unlock(fh)
    finally:
        fh.close()


# --- which stores are due ---------------------------------------------------------------------------

def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite returns naive UTC


def ago(delta: timedelta) -> str:
    hours = delta.total_seconds() / 3600
    return f"{hours:.0f} h ago" if hours < 48 else f"{hours / 24:.0f} d ago"


@dataclass
class Decision:
    cfg: ScraperConfig
    due: bool
    reason: str


def decide(session, cfg: ScraperConfig, now: datetime, force: bool = False) -> Decision:
    """Is this store due? Only finished crawls count; a "running" row is a crawl in progress or a dead one, cleaned up
    under the lock by interrupt_leftovers."""
    if force:
        return Decision(cfg, True, "forced")
    source = session.scalar(select(Source).where(Source.url == str(cfg.base_url)))
    if source is None:
        return Decision(cfg, True, "never crawled")

    def newest(*where) -> StoreCrawl | None:
        return session.scalar(select(StoreCrawl).where(StoreCrawl.source_id == source.id, StoreCrawl.finished_at.is_not(None), *where)
                              .order_by(StoreCrawl.finished_at.desc()).limit(1))

    # A crawl that was interrupted (process killed, reboot) says nothing about the store: it does not start a back-off.
    last_ok = newest(StoreCrawl.status == "ok")
    last_try = newest(or_(StoreCrawl.error.is_(None), StoreCrawl.error.not_like(f"{INTERRUPTED}%")))
    cadence = timedelta(days=cfg.crawl_every_days)
    if last_ok and now - aware(last_ok.finished_at) < cadence - CADENCE_SLACK:
        return Decision(cfg, False, f"complete crawl {ago(now - aware(last_ok.finished_at))}, every {cfg.crawl_every_days} d")
    if last_try and last_try.status != "ok" and now - aware(last_try.finished_at) < RETRY_AFTER:
        return Decision(cfg, False, f"{last_try.status} crawl {ago(now - aware(last_try.finished_at))}, retry after {RETRY_AFTER.total_seconds() / 3600:.0f} h")
    if last_ok is None:
        return Decision(cfg, True, "no complete crawl yet" if last_try else "never crawled")
    retry = f" (retrying a {last_try.status} crawl)" if last_try and last_try.status != "ok" else ""
    return Decision(cfg, True, f"last complete crawl {ago(now - aware(last_ok.finished_at))}{retry}")


def plan(configs: dict[str, ScraperConfig], only: tuple[str, ...] = (), force: bool = False,
         now: datetime | None = None) -> list[Decision]:
    """The stores to consider (all, or the named ones) with whether each is due. Raises KeyError for an unknown domain.
    Reads the database, writes nothing."""
    now = now or datetime.now(timezone.utc)
    chosen = [config_for(d, configs) for d in only] if only else list(configs.values())
    with SessionLocal() as s:
        return [decide(s, cfg, now, force) for cfg in chosen]


def interrupt_leftovers() -> int:
    """Rows still "running" belong to a crawl whose process ended: only call this while holding the lock."""
    with SessionLocal() as s:
        n = s.execute(update(StoreCrawl).where(StoreCrawl.status == "running").values(
            status="failed", finished_at=datetime.now(timezone.utc),
            error=f"{INTERRUPTED}: the process ended before this crawl finished")).rowcount
        s.commit()
    if n:
        log.warning("%d crawl(s) left running by a process that ended were marked failed", n)
    return n


# --- crawling one store -----------------------------------------------------------------------------

@dataclass
class StoreOutcome:
    cfg: ScraperConfig
    status: str  # ok | incomplete | failed
    crawled: int = 0
    listed: int = 0
    result: SyncResult | None = None
    problems: list[str] | None = None
    error: str | None = None
    seconds: float = 0.0

    @property
    def needs_attention(self) -> bool:
        """Nothing broke, but the crawl could not be trusted to drop products (partial listing, shrunk listing)."""
        return self.status == "incomplete" or bool(self.result and self.result.drop_skipped)


async def _crawl(cfg: ScraperConfig) -> tuple[list[ScrapedProduct], CrawlReport]:
    async with httpx.AsyncClient(headers={"User-Agent": settings.user_agent},
                                 timeout=httpx.Timeout(settings.request_timeout), follow_redirects=True) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        products = await crawler.crawl()
        return products, crawler.report


async def _crawl_with_cap(cfg: ScraperConfig) -> tuple[list[ScrapedProduct], CrawlReport]:
    return await asyncio.wait_for(_crawl(cfg), timeout=STORE_TIMEOUT)


def run_store(cfg: ScraperConfig, trigger: str, accept_drops: bool = False) -> StoreOutcome:
    """Crawl one store, sync it, and record the crawl. A failure of the crawl or the sync does not raise: it is a
    "failed" row and outcome. Call it while holding crawl_lock. Nothing reaches `products` unless the sync itself runs."""
    started = time.monotonic()
    with SessionLocal() as s:
        service = StoreSyncService(s)
        source_id = service.source_for(cfg).id
        row = StoreCrawl(source_id=source_id, status="running", trigger=trigger)
        s.add(row)
        s.commit()
        row_id = row.id
        try:
            products, report = asyncio.run(_crawl_with_cap(cfg))
            result = service.sync(source_id, products, report, accept_drops=accept_drops)
        except Exception as e:  # any failure of this store, including a timeout: record it, let the others run
            s.rollback()
            error = f"{type(e).__name__}: {e}"[:2000]
            log.exception("%s: crawl failed", cfg.name)
            row = s.get(StoreCrawl, row_id)
            row.status, row.error, row.finished_at = "failed", error, datetime.now(timezone.utc)
            s.commit()
            return StoreOutcome(cfg, "failed", error=error, seconds=time.monotonic() - started)
        # a facet page that could not be fetched leaves the listing (and so the drops) sound but the data stale: the crawl is
        # incomplete, so it shows on the panel and is retried the next day
        status = "ok" if report.complete and not report.gaps else "incomplete"
        problems = [*report.problems, *(g.note for g in report.gaps)]
        row = s.get(StoreCrawl, row_id)
        row.status, row.finished_at = status, datetime.now(timezone.utc)
        row.listed, row.crawled = len(report.listed), len(products)
        row.inserted, row.updated, row.reactivated, row.dropped = result.inserted, result.updated, result.reactivated, result.dropped
        row.drop_skipped, row.problems = result.drop_skipped, problems or None
        s.commit()
    return StoreOutcome(cfg, status, crawled=len(products), listed=len(report.listed), result=result,
                        problems=problems, seconds=time.monotonic() - started)


def run_single(cfg: ScraperConfig, accept_drops: bool = False) -> StoreOutcome:
    """`crawl-store`: one store, now, whatever its cadence. Raises CrawlBusy if another crawl is running."""
    with crawl_lock():
        interrupt_leftovers()
        return run_store(cfg, "single", accept_drops)


def run_due(configs: dict[str, ScraperConfig], only: tuple[str, ...] = (), force: bool = False,
            now: datetime | None = None, on_start: Callable[[list[Decision]], None] | None = None,
            on_outcome: Callable[[StoreOutcome], None] | None = None) -> tuple[list[Decision], list[StoreOutcome]]:
    """`crawl-stores`: every due store, one after another. One store failing never stops the others. Raises CrawlBusy
    if another crawl is running, and KeyError for an unknown domain (before anything is crawled)."""
    with crawl_lock():
        interrupt_leftovers()
        decisions = plan(configs, only, force, now)
        if on_start:
            on_start(decisions)
        outcomes = []
        for d in decisions:
            if d.due:
                outcomes.append(run_store(d.cfg, "batch"))
                if on_outcome:
                    on_outcome(outcomes[-1])
    return decisions, outcomes
