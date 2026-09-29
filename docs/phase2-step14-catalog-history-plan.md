# Step 14 plan: catalog history and automated store crawls

Status: **plan only, nothing implemented.** Follows Step 13 (frequent pairings, commit `1d5595d`).

## Why

Every store crawl today overwrites its products in place (`StoreSyncService.sync`, upsert by url). We cannot say
what is new, what was retired, or when. For creator brands this is the leading signal: a new model appears in a
brand's catalog months before the press writes about it. Crawls are also manual (`crawl-store DOMAIN`).

## 1. Schema (one Alembic migration, on `products`)

| column | type | meaning |
|---|---|---|
| `first_seen_at` | DateTime(tz), NOT NULL | set once, on insert, never rewritten |
| `is_active` | Boolean, NOT NULL, default true | in the store's latest complete crawl |
| `dropped_at` | DateTime(tz), NULL | when a crawl noticed the product gone; cleared on return |

`seen_at` stays as is and is read as `last_seen_at` (no rename: a rename would touch every reader for no gain).
`dropped_at` goes beyond the two columns asked for. It is optional, but without it "disappeared" can only be
dated as "somewhere between `seen_at` and today". Index `ix_products_source_active (source_id, is_active)`.

No history table and no per-crawl product rows: a product is one row for its whole life.

**Backfill (in the migration, so nothing on screen moves):**
- `first_seen_at = seen_at`.
- `is_active` = the rule `retail.active_products` applies today: seen within `ACTIVE_DAYS` (14) of the store's latest
  `seen_at`. Computed in Python inside the migration (SQLite date arithmetic on stored strings is fragile).
- `dropped_at = NULL` (unknown for old drops).

**Honest limit:** for products that existed before the migration, `first_seen_at` is "no later than", not a real
arrival date. So "new arrival" is never `first_seen_at > some date`. It is defined against each store's baseline:
`baseline(source) = MIN(first_seen_at)`; a product is new if `first_seen_at > baseline + 3 days`. That also makes the
first crawl of any future store (Woodys, a Safilo brand) a baseline, not a wave of "new" frames.

Migration gets the usual treatment: plan shown, live DB backed up, your approval before `alembic upgrade head`,
plus a test in `tests/test_migrations.py` (old rows in, backfill checked, downgrade round-trip).

## 2. Sync logic: how a dropped product is detected

Yes: a product active in the DB for a store, absent from that store's latest crawl, is set `is_active = False`
and `dropped_at = now`. But "absent from the batch" is not safe on its own. Three ways it lies, each closed:

1. **The crawl was partial.** `fetch()` returns `None` on any failure, and `listing_pages` follows `link[rel=next]`:
   one failed page silently truncates the listing (a 429, a bot challenge, a timeout). Fix: the crawler records a
   `CrawlReport` (`crawler.report`, `crawl()` keeps returning the product list, so existing tests do not change):
   `listed` = every product URL the listing returned, `complete` = false if any main-listing page failed or was blocked,
   or pagination stopped at `max_pages` with more to come. Facet-pass failures do not count: they only enrich, they
   never decide presence.
2. **Validation drops a product that is still listed.** `crawl()` drops a `ScrapedProduct` that fails validation, so
   it is missing from the batch yet still on the shelf. Presence is therefore decided on `report.listed`, not on the
   validated batch.
3. **The store changed and the crawl "succeeded" with almost nothing.** Guard: if `len(listed)` is under 70 % of the
   store's currently active products, nothing is dropped. The run is reported as `drop_skipped: "listing shrank
   684 → 120"`. `crawl-store --accept-drops` overrides it, for a genuine catalog cull.

Rules in `StoreSyncService.sync(source_id, products, listed=None, complete=False)`:
- inserted: `first_seen_at = seen_at`, `is_active = True`;
- seen again: `seen_at` updated, `is_active = True`; if it was inactive, `reactivated += 1`, `dropped_at = None`;
- dropped: only when `complete` and the guard passes, only this source's active rows, never a product that belongs to
  another source (the existing conflict rule is unchanged);
- `SyncResult` gains `reactivated`, `dropped`, `drop_skipped` (reason or `None`);
- sold out is not dropped: Etnia keeps sold-out frames listed, `flags.out_of_stock` stays a separate signal.

`retail.active_products` becomes `Product.is_active` (its single definition, so every reader follows). `ACTIVE_DAYS`
is retired. That also fixes a quiet weakness: the 14-day window only works with regular crawls.

Known limit: a store that renames a product URL looks like one drop plus one new arrival. Mitigation later, if it
shows up: match on a stable id when the store exposes one (Shopify's product id is in `var meta`).

## 3. Automation

**A `stores` pipeline step**, not part of the default steps:
- `ALL_STEPS` stays the daily press set, so "Actualiser les données" does not start a 60-minute crawl. The API accepts
  `KNOWN_STEPS = ALL_STEPS + ("stores",)`, with the label "Boutiques" in `STEP_LABELS`.
- The crawl logic moves out of `cli.py` into `collectors/stores/runner.py`:
  `crawl_stores(session, only=None, force=False, progress=None) -> dict`. The CLI (`crawl-store DOMAIN`, new
  `crawl-stores`) and the pipeline both call it: one code path, one sync rule.
- Per store: crawl (network only, no DB transaction open for the ~15-30 min), then `sync` in one short transaction.
  Stores run one after another, never in parallel, each on its own `delay_s`, same user agent, same robots.txt rules.
- **One store failing does not stop the others.** Each store is wrapped in its own try/except. The run report is
  `report["stores"] = {"Etnia Barcelona": {"status": "ok", "listed": 684, "inserted": 3, "reactivated": 0,
  "dropped": 2}, "Morel": {"status": "failed", "error": "..."}}`. The run is `failed` only if every store failed.
- **Cadence by data, not by cron alone:** each store has `crawl_every_days` (config, default 7). A store is due when
  `max(Product.seen_at)` for its source is older than that (it is only written by a successful sync, so it is the
  last good crawl: no new column). The cron then only says "check", a re-run after a failure retries just the failed
  stores, and `--force` ignores it.
- **Schedule (`jobs/scheduler.py`):** add `weekly_stores`, `cron` Monday 03:00 Europe/Paris, `steps=("stores",)`,
  `max_instances=1`, `coalesce=True`, `misfire_grace_time=6h`, so a laptop that was asleep at 03:00 still runs it on
  wake. It ends well before the 06:00 daily press run. The scheduler must be running (`python -m app.jobs.scheduler`);
  a Windows Task Scheduler entry calling `python -m app.cli crawl-stores` is an equivalent option for a machine that
  sleeps, and both use the same function.
- **Stale-run window:** `STALE_AFTER` is 3 h for every run today. A stores run gets 12 h. Fifteen brands at ~20 min each
  is five hours, and a live crawl must not be declared dead and overlapped. Overlap stays impossible: `active_run`
  still allows one run at a time. A manual "Actualiser" during a crawl gets the existing "en cours" message, with
  "Boutiques 3/5" progress (`progress(done_stores, total_stores)`).
- **Stale store warning:** the Sources page flags a store whose last good crawl is older than 2 × its cadence, so a
  silently broken crawler (layout change, bot challenge) shows up instead of freezing its shelf forever.

## 4. Files

- `migrations/versions/…_catalog_history.py`; `models.py` (three columns, index).
- `collectors/stores/base.py` (`CrawlReport`), `service.py` (sync rules, `SyncResult`), `config.py` (`crawl_every_days`),
  new `runner.py`.
- `jobs/pipeline.py` (`stores` step, `KNOWN_STEPS`, per-step stale window), `jobs/scheduler.py`, `cli.py`
  (`crawl-stores`, `--accept-drops`), `api/main.py` (accept the step, label).
- `scoring/retail.py` (`active_products` on `is_active`; drop `ACTIVE_DAYS`); their tests updated.

## 5. Offline tests

- **Sync:** `first_seen_at` set on insert and never changed by a later update; return of a dropped product clears
  `dropped_at`; drop only with `complete`; no drop on an incomplete crawl; no drop under the 70 % guard; `--accept-drops`
  overrides it; another source's products untouched; a URL owned by another source stays a conflict.
- **Crawler report (MockTransport):** a failing listing page 2 gives `complete = False`; a validation-dropped card
  stays in `listed`; reaching `max_pages` with a next link gives `complete = False`; facet failure does not.
- **Runner and pipeline:** store B raising does not stop A or C; run status `success` with per-store statuses; `failed`
  only if all fail; a store crawled 2 days ago is skipped, `force` runs it; progress is (done, total) in stores.
- **Scheduler:** the weekly job is registered with the Monday 03:00 trigger, `coalesce` and the grace window (inspect
  the job, do not start the scheduler).
- **Migration:** old rows backfilled as above; downgrade round-trip; `test_migrations_match_models` still green.
- `retail` tests: the shelf is unchanged after switching to `is_active` on the same data.

## 6. What it does not do (yet)

- No screen. This step is the data layer. The next small step reads it: a "Nouveauté" pill on frames whose
  `first_seen_at` is past the store baseline, "N nouveautés / N retirés (30 j)" per attribute for creator brands,
  and a line in the weekly brief.
- No price history and no daily snapshots.
- No change to the press pipeline or its schedule.

## Decisions (settled 2026-09-29: defaults taken)

1. `dropped_at` is added as a third column.
2. The shrink guard is 70 %; the default cadence is weekly, Monday 03:00 Europe/Paris.
3. The schedule lives in the existing scheduler process (`python -m app.jobs.scheduler`), next to the daily press job.
   `python -m app.cli crawl-stores` calls the same function, so a Windows Task Scheduler entry stays a drop-in option.

Changes to the decisions above, made on approval: the weekly crawl is triggered by **Windows Task Scheduler**, not by
`jobs/scheduler.py`; `crawl-stores` must therefore be self-contained and idempotent, and the scheduler and `stores`
pipeline step are not built.

## Status
- Part 1, schema: done and live (`ab4dbe5`).
- Part 2, sync rules and completeness report: done (see `docs/build-plan.md`, Step 14). `param` pagination cannot tell a
  natural end from a cut-off, so a `?page=` listing that fills `max_pages`, or whose page past the end returns 404,
  reports incomplete and never drops (no shipped store uses `?page=`; all follow `next` links).
- Part 3, `crawl-stores` runner, `store_crawls` log, Task Scheduler wrapper and docs: done (see `docs/build-plan.md`, Step 14, and `docs/crawl-stores-task-scheduler.md`).
- Part 4, the read side (new / retired counts, "Nouveauté" pill, Sources panel, brief section, prompt v4): done (see
  `docs/build-plan.md`, Step 14). It differs from the sketch above in one place: "new" is measured against the first complete
  crawl in `store_crawls`, not `MIN(first_seen_at) + 3 days`, so genuinely new frames found by a first `crawl-stores` run are
  not swallowed by a grace window.
