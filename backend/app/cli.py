"""Command line: python -m app.cli <command>   (python -m app.cli --help lists them)

  run [STEPS...]         full pipeline, or chosen steps (rss news google_trends extract score summary)
  backfill [WEEKS]       one-off: collect the trade press archive of the last N weeks (default 12).
                         Collection only (free); prints how many articles await Claude analysis and
                         the estimated cost. Then run: python -m app.cli run extract score summary
  refresh-search         replace collected Google Trends data (one keyword per request) and re-score; free
                         --missing: only fetch keywords with no data yet (after a rate-limited run)
  crawl-store DOMAIN     crawl one store from store_configs.yaml into products; free (no LLM)
  retag-products [DOMAIN] re-run the rule-based tagger on stored products; free, no network
  reread-colors          re-read, with Claude, the colors of articles analysed with an older prompt (colors
                         only). Prints the count and estimated cost; --confirm spends, then re-scores
  seed-demo              load synthetic demo data and score it
  clear-demo             remove demo data
"""

import asyncio
import json
import logging

import click
import httpx
from sqlalchemy import func, select

from app.collectors.backfill import run_backfill
from app.collectors.google_trends import collect_google_trends, reset_search_interest
from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import ScraperConfig, config_for, load_store_configs
from app.collectors.stores.schemas import CrawlReport, ScrapedProduct
from app.collectors.stores.service import StoreSyncService
from app.config import settings
from app.db import SessionLocal, init_db
from app.extraction import llm
from app.extraction.service import reread_pending, reread_query
from app.demo import clear_demo, seed_demo
from app.jobs.pipeline import ALL_STEPS, run_pipeline
from app.models import Document, Source
from app.scoring.trends import compute_snapshots

# Rough Claude cost per article on the default extraction model (Sonnet 5, $2 / $10 per M tokens):
# ~4 chars per token of article text + ~500 output tokens; the shared taxonomy prompt is cached.
INPUT_PRICE, OUTPUT_PRICE, OUTPUT_TOKENS = 2 / 1e6, 10 / 1e6, 500
REREAD_OUTPUT_TOKENS = 150  # a one-dimension re-read answers with that dimension only


def cost_estimate(docs, output_tokens: int = OUTPUT_TOKENS) -> tuple[int, float]:
    """(articles, estimated $) for analysing the documents a select(Document) query returns."""
    sub = docs.subquery()
    with SessionLocal() as s:
        n, chars = s.execute(select(func.count(), func.coalesce(func.sum(func.length(sub.c.text)), 0))).one()
    return n, (chars / 4) * INPUT_PRICE + n * output_tokens * OUTPUT_PRICE


def pending_cost_estimate() -> tuple[int, float]:
    return cost_estimate(select(Document).where(Document.status == "pending"))


@click.group(invoke_without_command=True, help=__doc__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.WARNING)  # startup migration chatter
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return
    init_db()


@cli.command()
@click.argument("steps", nargs=-1)
def run(steps: tuple[str, ...]) -> None:
    """Full pipeline, or the chosen steps."""
    click.echo(json.dumps(run_pipeline(steps or ALL_STEPS), indent=2, default=str))


@cli.command()
@click.argument("weeks", type=int, default=12)
def backfill(weeks: int) -> None:
    """Collect the trade press archive of the last WEEKS weeks (free)."""
    with SessionLocal() as s:
        added = run_backfill(s, weeks=weeks)
    n, cost = pending_cost_estimate()
    click.echo(json.dumps({"new_documents": added, "weeks": weeks}, indent=2))
    click.echo(f"{n} articles await Claude analysis, estimated cost ~${cost:.2f}. "
               "Run: python -m app.cli run extract score summary")


@cli.command("refresh-search")
@click.option("--missing", is_flag=True, help="Only fetch keywords with no data yet (fills gaps left by rate limits).")
def refresh_search(missing: bool) -> None:
    """Replace collected Google Trends data and re-score (free). With --missing: keep the data, fill the gaps."""
    with SessionLocal() as s:
        removed = 0 if missing else reset_search_interest(s)
        stored = collect_google_trends(s, only_missing=missing)
        click.echo(f"removed {removed} old values, stored {stored} new ones, {compute_snapshots(s)} snapshots")


async def _crawl(cfg: ScraperConfig) -> tuple[list[ScrapedProduct], CrawlReport]:
    async with httpx.AsyncClient(headers={"User-Agent": settings.user_agent},
                                 timeout=httpx.Timeout(settings.request_timeout), follow_redirects=True) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        products = await crawler.crawl()
        return products, crawler.report


@cli.command("crawl-store")
@click.argument("domain")
@click.option("--accept-drops", is_flag=True,
              help="Drop products the listing no longer returns even if it shrank a lot (a real catalog cull). "
                   "Never overrides an incomplete crawl.")
def crawl_store(domain: str, accept_drops: bool) -> None:
    """Crawl one store from store_configs.yaml and upsert its products (free, no LLM).

    Products the store's listing no longer returns are marked inactive (dropped), only when the crawl read the whole
    listing and it did not shrink suspiciously; a returning product is reactivated. Safe to re-run."""
    cfg = _store_config_or_exit(domain)
    products, report = asyncio.run(_crawl(cfg))
    with SessionLocal() as s:
        service = StoreSyncService(s)
        result = service.sync(service.source_for(cfg).id, products, report, accept_drops=accept_drops)
    click.echo(f"{cfg.name}: {len(products)} products crawled — inserted {result.inserted}, "
               f"updated {result.updated}, conflicts {result.conflicts}, reactivated {result.reactivated}, "
               f"dropped {result.dropped}")
    if result.drop_skipped:
        click.echo(f"  drops skipped: {result.drop_skipped}")
        for problem in report.problems[:10]:
            click.echo(f"  - {problem}")
        if report.complete:
            click.echo("  (re-run with --accept-drops if the catalog really shrank)")


def _store_config_or_exit(domain: str) -> ScraperConfig:
    try:
        return config_for(domain)
    except KeyError:
        known = ", ".join(load_store_configs()) or "none"
        click.echo(f"Error: no store config for {domain!r}. Known: {known}", err=True)
        raise SystemExit(1)
    except ValueError as e:  # invalid store_configs.yaml
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command("retag-products")
@click.argument("domain", required=False)
def retag_products(domain: str | None) -> None:
    """Re-run the rule-based tagger on stored products (all stores, or DOMAIN). Free, no network."""
    source_id = None
    with SessionLocal() as s:
        if domain:
            cfg = _store_config_or_exit(domain)
            source = s.scalar(select(Source).where(Source.url == str(cfg.base_url)))
            if source is None:
                click.echo(f"Error: {cfg.name} has not been crawled yet. Run: python -m app.cli crawl-store {cfg.domain}", err=True)
                raise SystemExit(1)
            source_id = source.id
        service = StoreSyncService(s)
        n = service.retag_all(source_id)
        counts = ", ".join(f"{dim} {k}" for dim, k in service.tag_counts(source_id).items()) or "none"
        click.echo(f"{n} products re-tagged. Tagged products per dimension: {counts}")


@cli.command("reread-colors")
@click.option("--confirm", is_flag=True, help="Spend: re-read up to max_extract_per_run articles with Claude, then re-score.")
def reread_colors(confirm: bool) -> None:
    """Re-read the colors of articles analysed with an older prompt. Colors only: shapes, materials and styles
    keep their first analysis. Without --confirm, only prints how many articles and the estimated cost."""
    n, cost = cost_estimate(reread_query("color"), REREAD_OUTPUT_TOKENS)
    if not n:
        click.echo("Every article's colors are from the current prompt: nothing to re-read.")
        return
    click.echo(f"{n} articles have colors from an older prompt: ~${cost:.2f} to re-read them all, "
               f"at most {settings.max_extract_per_run} per run.")
    if not confirm:
        click.echo("Nothing spent. Run again with --confirm to re-read.")
        return
    with SessionLocal() as s:
        stats = reread_pending(s, llm.get_provider(), "color", limit=settings.max_extract_per_run)
        click.echo(f"re-read {stats['reread']}, kept {stats['kept']} (judged not relevant this time), "
                   f"failed {stats['failed']}; {stats['remaining']} left. {compute_snapshots(s)} snapshots")


@cli.command("seed-demo")
def seed_demo_cmd() -> None:
    """Load synthetic demo data and score it."""
    with SessionLocal() as s:
        n = seed_demo(s)
        click.echo(f"{n} demo documents, {compute_snapshots(s)} snapshots")


@cli.command("clear-demo")
def clear_demo_cmd() -> None:
    """Remove demo data."""
    with SessionLocal() as s:
        clear_demo(s)
        compute_snapshots(s)
        click.echo("demo data removed")


if __name__ == "__main__":
    cli()
