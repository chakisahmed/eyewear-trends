"""Command line: python -m app.cli <command>

  run [steps...]   full pipeline, or chosen steps (rss news google_trends extract score summary)
  seed-demo        load synthetic demo data and score it
  clear-demo       remove demo data
"""

import json
import logging
import sys

from app.db import SessionLocal, init_db
from app.demo import clear_demo, seed_demo
from app.jobs.pipeline import ALL_STEPS, run_pipeline
from app.scoring.trends import compute_snapshots


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cmd, args = (argv[0], argv[1:]) if argv else ("help", [])
    init_db()
    if cmd == "run":
        print(json.dumps(run_pipeline(tuple(args) or ALL_STEPS), indent=2, default=str))
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
