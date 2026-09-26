"""AI-written weekly summary in French, grounded only in computed scores."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.extraction.llm import LLMProvider
from app.extraction.service import load_prompt
from app.models import Document, Mention, TrendSnapshot, WeeklySummary
from app.taxonomy import load_taxonomy


def latest_week(session: Session) -> date | None:
    return session.scalar(select(func.max(TrendSnapshot.week)))


def build_brief(session: Session, week: date) -> str:
    tax = load_taxonomy()
    snaps = session.scalars(select(TrendSnapshot).where(TrendSnapshot.week == week)).all()
    # Sample size behind each score: weighted mentions over the last 4 weeks.
    volume_4w: dict[tuple[str, str], float] = {}
    for s in session.scalars(select(TrendSnapshot).where(TrendSnapshot.week > week - timedelta(weeks=4), TrendSnapshot.week <= week)):
        volume_4w[(s.dimension, s.code)] = volume_4w.get((s.dimension, s.code), 0.0) + s.mentions

    def line(s: TrendSnapshot) -> str:
        fading = f"{s.decline_share:.0%}" if s.decline_share is not None else "n/d"
        return (f"{tax.dimension_labels[s.dimension]} | {tax.label(s.dimension, s.code)} | {s.mentions:.1f} | "
                f"{volume_4w.get((s.dimension, s.code), 0.0):.0f} | {s.momentum:+.0%} | {s.status} | {fading}")

    ranked = sorted((s for s in snaps if s.mentions > 0 or s.search), key=lambda s: -s.momentum)
    lines = [
        f"Semaine du {week.isoformat()}", "",
        "Scores (dimension | attribut | mentions pondérées cette semaine | mentions sur 4 sem. | momentum du volume | statut | part des avis « en recul » sur 4 sem.):",
        *[line(s) for s in ranked if s.status != "faible"],
    ]
    weak = [line(s) for s in ranked if s.status == "faible"]
    if weak:
        lines += ["", "Signaux faibles (trop peu de mentions pour conclure, à citer seulement comme « à surveiller ») :", *weak]
    extracts = session.scalars(
        select(Document.summary_fr)
        .join(Mention)
        .where(Mention.occurred_on >= week, Document.summary_fr.is_not(None))
        .distinct()
        .limit(12)
    ).all()
    if extracts:
        lines += ["", "Extraits de sources:"] + [f"- {e}" for e in extracts]
    return "\n".join(lines)


def generate_weekly_summary(session: Session, provider: LLMProvider, week: date | None = None) -> WeeklySummary | None:
    week = week or latest_week(session)
    if week is None:
        return None
    text = provider.write(load_prompt("summary_fr"), build_brief(session, week))
    row = session.scalar(select(WeeklySummary).where(WeeklySummary.week == week))
    if row is None:
        row = WeeklySummary(week=week, text_fr=text, model=settings.summary_model)
        session.add(row)
    else:
        row.text_fr, row.model = text, settings.summary_model
    session.commit()
    return row
