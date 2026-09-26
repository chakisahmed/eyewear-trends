"""Synthetic demo data so the dashboard can be reviewed before real collection runs.

Everything created here is flagged is_demo=True and removed by `clear_demo`.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Document, Mention, SearchInterest, Source, TrendSnapshot, WeeklySummary
from app.scoring.trends import week_start

# (dimension, code) -> weekly mention level over 12 weeks: (start, end) is a straight line;
# (start, end, "peak") climbs to `end` by ~week 7, then plateaus, so the dashboard shows "au pic" too.
PATTERNS = {
    ("shape", "cat_eye"): (3, 14),
    ("shape", "oversized"): (5, 11),
    ("shape", "rectangle"): (10, 4),
    ("shape", "round"): (6, 7),
    ("shape", "aviator"): (3, 9, "peak"),
    ("shape", "geometric"): (1, 5),
    ("color", "tortoiseshell"): (5, 13, "peak"),
    ("color", "clear"): (2, 9),
    ("color", "gold"): (4, 7),
    ("color", "black"): (9, 8),
    ("color", "pastel"): (6, 2),
    ("color", "brown"): (2, 6),
    ("material", "acetate"): (6, 11),
    ("material", "metal"): (7, 6),
    ("material", "titanium"): (1, 6, "peak"),
    ("material", "recycled"): (1, 5),
    ("style", "retro"): (5, 9),
    ("style", "minimalist"): (6, 5),
    ("style", "y2k"): (7, 3),
    ("style", "statement"): (2, 6),
    ("style", "luxury"): (2, 7, "peak"),
}


def clear_demo(session: Session) -> None:
    demo_docs = select(Document.id).where(Document.is_demo)
    session.execute(delete(Mention).where(Mention.document_id.in_(demo_docs)))
    session.execute(delete(Document).where(Document.is_demo))
    session.execute(delete(Source).where(Source.url.like("demo:%")))
    session.execute(delete(SearchInterest).where(SearchInterest.is_demo))
    session.execute(delete(TrendSnapshot))
    session.execute(delete(WeeklySummary))
    session.commit()


def seed_demo(session: Session, weeks: int = 12, seed: int = 7) -> int:
    rng = random.Random(seed)
    clear_demo(session)
    sources = [
        Source(name="Démo presse FR", kind="press", url="demo:press-fr", lang="fr", country="FR"),
        Source(name="Démo press EN", kind="press", url="demo:press-en", lang="en", country="US"),
        Source(name="Démo actualités", kind="news", url="demo:news", lang="fr", country="FR"),
    ]
    session.add_all(sources)
    this_week = week_start(date.today())
    n = 0
    for w in range(weeks):
        week = this_week - timedelta(weeks=weeks - 1 - w)
        for (dim, code), (a, b, *kind) in PATTERNS.items():
            progress = min(1.0, w / (weeks * 0.6)) if kind == ["peak"] else w / (weeks - 1)
            level = a + (b - a) * progress
            for _ in range(max(0, round(level + rng.uniform(-1.2, 1.2)))):
                src = rng.choice(sources)
                # never in the future: the current week is only partly over
                day = min(week + timedelta(days=rng.randint(0, 6)), date.today())
                stance = "rising" if b > a else ("declining" if b < a - 2 else "neutral")
                doc = Document(
                    source=src, url=f"demo:{dim}:{code}:{w}:{n}", title=f"[Démo] {dim} / {code}",
                    text="Donnée de démonstration.", lang=src.lang,
                    published_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
                    status="extracted", summary_fr=f"Donnée de démonstration ({dim} {code}).", is_demo=True,
                )
                doc.mentions.append(Mention(dimension=dim, code=code, stance=stance, evidence="[démo]", occurred_on=day))
                session.add(doc)
                n += 1
            for lang, geo in (("fr", "FR"), ("en", "")):
                session.add(SearchInterest(
                    dimension=dim, code=code, keyword=f"demo {code}", lang=lang, geo=geo, week=week,
                    value=max(1.0, level * 4 + rng.uniform(-4, 4)), is_demo=True,
                ))
    session.commit()
    return n
