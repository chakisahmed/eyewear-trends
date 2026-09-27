"""Command line: python -m app.cli <command>

  run [steps...]    full pipeline, or chosen steps (rss news google_trends extract score summary)
  backfill [weeks]  one-off: collect the trade press archive of the last N weeks (default 12).
                    Collection only (free); prints how many articles await Claude analysis and
                    the estimated cost. Then run: python -m app.cli run extract score summary
  refresh-search    replace collected Google Trends data (one keyword per request) and re-score; free
  seed-demo         load synthetic demo data and score it
  clear-demo        remove demo data
"""

import json
import logging
import sys

from sqlalchemy import func, select

from app.collectors.backfill import run_backfill
from app.collectors.google_trends import collect_google_trends, reset_search_interest
from app.db import SessionLocal, init_db
from app.demo import clear_demo, seed_demo
from app.jobs.pipeline import ALL_STEPS, run_pipeline
from app.models import Document
from app.scoring.trends import compute_snapshots

# Rough Claude cost per article on the default extraction model (Sonnet 5, $2 / $10 per M tokens):
# ~4 chars per token of article text + ~500 output tokens; the shared taxonomy prompt is cached.
INPUT_PRICE, OUTPUT_PRICE, OUTPUT_TOKENS = 2 / 1e6, 10 / 1e6, 500


def pending_cost_estimate() -> tuple[int, float]:
    with SessionLocal() as s:
        n, chars = s.execute(
            select(func.count(), func.coalesce(func.sum(func.length(Document.text)), 0)).where(Document.status == "pending")
        ).one()
    return n, (chars / 4) * INPUT_PRICE + n * OUTPUT_TOKENS * OUTPUT_PRICE


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    cmd, args = (argv[0], argv[1:]) if argv else ("help", [])
    init_db()
    if cmd == "run":
        print(json.dumps(run_pipeline(tuple(args) or ALL_STEPS), indent=2, default=str))
    elif cmd == "backfill":
        weeks = int(args[0]) if args else 12
        with SessionLocal() as s:
            added = run_backfill(s, weeks=weeks)
        n, cost = pending_cost_estimate()
        print(json.dumps({"new_documents": added, "weeks": weeks}, indent=2))
        print(f"{n} articles await Claude analysis, estimated cost ~${cost:.2f}. "
              "Run: python -m app.cli run extract score summary")
    elif cmd == "refresh-search":
        with SessionLocal() as s:
            removed = reset_search_interest(s)
            stored = collect_google_trends(s)
            print(f"removed {removed} old values, stored {stored} new ones, {compute_snapshots(s)} snapshots")
    elif cmd == "seed-demo":
        with SessionLocal() as s:
            n = seed_demo(s)
            print(f"{n} demo documents, {compute_snapshots(s)} snapshots")
    elif cmd == "clear-demo":
        with SessionLocal() as s:
            clear_demo(s)
            compute_snapshots(s)
            print("demo data removed")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
