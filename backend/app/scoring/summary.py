"""AI-written weekly summary in French, grounded only in computed scores."""

from __future__ import annotations

from datetime import date

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
    lines = [
        f"Semaine du {week.isoformat()}", "",
        "Scores (dimension | attribut | mentions pondérées | momentum du volume | statut | part des avis « en recul » sur 4 sem.):",
    ]
    for s in sorted(snaps, key=lambda s: -s.momentum):
        if s.mentions == 0 and not s.search:
            continue
        fading = f"{s.decline_share:.0%}" if s.decline_share is not None else "n/d"
        lines.append(
            f"{tax.dimension_labels[s.dimension]} | {tax.label(s.dimension, s.code)} | {s.mentions:.1f} | {s.momentum:+.0%} | {s.status} | {fading}"
        )
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
