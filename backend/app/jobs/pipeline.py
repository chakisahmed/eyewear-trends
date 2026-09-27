"""End-to-end run: collect -> extract -> score -> summary, recorded as a JobRun."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.google_trends import collect_google_trends
from app.collectors.news_gdelt import collect_news
from app.collectors.rss_blogs import collect_rss
from app.config import settings
from app.db import SessionLocal, init_db
from app.demo import clear_demo
from app.extraction.llm import get_provider
from app.extraction.service import extract_pending
from app.models import Document, JobRun
from app.scoring.summary import generate_weekly_summary
from app.scoring.trends import compute_snapshots

log = logging.getLogger(__name__)
ALL_STEPS = ("rss", "news", "google_trends", "extract", "score", "summary")
# Steps that bring in real data: a run with any of them first removes the demo data set,
# so demo and real mentions are never scored or summarized together.
COLLECTION_STEPS = ("rss", "news", "google_trends", "extract")
# A run still "running" after this long is assumed dead (process killed, server restarted).
STALE_AFTER = timedelta(hours=3)


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes even for timezone=True columns.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def active_run(session: Session) -> JobRun | None:
    run = session.scalar(select(JobRun).where(JobRun.status == "running").order_by(JobRun.started_at.desc()))
    if run and datetime.now(timezone.utc) - _aware(run.started_at) > STALE_AFTER:
        run.status, run.error, run.finished_at = "failed", "Interrompu (délai dépassé)", datetime.now(timezone.utc)
        session.commit()
        return None
    return run


def interrupt_orphaned_runs(session: Session) -> int:
    """Mark runs left "running" by a previous process as failed.

    Runs execute in the API process (background task), so none can survive a restart; without this, a
    killed run would block new ones until STALE_AFTER. Assumes a single API process, as deployed today.
    """
    orphans = session.scalars(select(JobRun).where(JobRun.status == "running")).all()
    for run in orphans:
        run.status = "failed"
        run.error = "Interrompu : le serveur a redémarré pendant la collecte. Relancez « Actualiser les données »."
        run.finished_at = datetime.now(timezone.utc)
    session.commit()
    return len(orphans)


def start_run(session: Session, steps: tuple[str, ...], trigger: str) -> JobRun:
    run = JobRun(steps=list(steps), trigger=trigger, status="running")
    session.add(run)
    session.commit()
    return run


def execute_run(run_id: int) -> dict:
    """Run the steps of an already-created JobRun and record the outcome.

    Progress (current step, items done / total) is saved on the run as it goes, using the pipeline's
    own session: steps call it right after their own commits, so it never commits half-built rows,
    and there is no second writer to contend with SQLite's single write lock.
    """
    report: dict = {}
    with SessionLocal() as session:
        run = session.get(JobRun, run_id)
        steps = tuple(run.steps)

        def begin(step: str):
            run.current_step, run.step_done, run.step_total = step, None, None
            session.commit()

            def progress(done: int, total: int) -> None:
                run.step_done, run.step_total = done, total
                session.commit()

            return progress

        try:
            if any(step in steps for step in COLLECTION_STEPS) and session.scalar(select(Document.id).where(Document.is_demo).limit(1)):
                clear_demo(session)
                report["demo_removed"] = True
            if "rss" in steps:
                report["rss"] = collect_rss(session, progress=begin("rss"))
            if "news" in steps:
                report["news"] = collect_news(session, progress=begin("news"))
            if "google_trends" in steps:
                report["google_trends"] = collect_google_trends(session, progress=begin("google_trends"))
            if "extract" in steps:
                report["extract"] = extract_pending(
                    session, get_provider(), limit=settings.max_extract_per_run, progress=begin("extract")
                )
            if "score" in steps:
                begin("score")
                report["score"] = compute_snapshots(session)
            if "summary" in steps:
                begin("summary")
                report["summary"] = bool(generate_weekly_summary(session, get_provider()))
            run.status = "success"
        except Exception as e:  # record any failure so the UI can show it, then re-raise for logs
            session.rollback()
            run = session.get(JobRun, run_id)
            run.status, run.error = "failed", f"{type(e).__name__}: {e}"[:2000]
            log.exception("Pipeline run %s failed", run_id)
        finally:
            run.report = report
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
    log.info("Pipeline run %s done: %s", run_id, report)
    return report


def run_pipeline(steps: tuple[str, ...] = ALL_STEPS, trigger: str = "cli") -> dict:
    init_db()
    with SessionLocal() as session:
        if active_run(session):
            raise RuntimeError("A collection run is already in progress")
        run_id = start_run(session, steps, trigger).id
    return execute_run(run_id)
