"""Daily collection schedule. Run with: python -m app.jobs.scheduler"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.jobs.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Europe/Paris")
    # Collect + extract + score every morning; the summary is regenerated from the latest scores.
    scheduler.add_job(run_pipeline, "cron", hour=6, minute=0, id="daily_pipeline", max_instances=1, kwargs={"trigger": "schedule"})
    scheduler.start()
