"""Google Trends search interest for bilingual taxonomy keywords.

Uses pytrends (unofficial). Google normalizes every request to its own 0-100 scale,
so each batch includes an anchor keyword and values are rescaled against it to stay
comparable across batches. Swap for SerpAPI in production for reliability.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.progress import Progress, report
from app.models import SearchInterest
from app.taxonomy import load_taxonomy

log = logging.getLogger(__name__)
ANCHORS = {"fr": "lunettes", "en": "glasses"}
BATCH = 4  # pytrends allows 5 keywords per request: 4 + anchor


def collect_google_trends(
    session: Session, dimensions: tuple[str, ...] = ("shape", "color", "material"), progress: Progress = None
) -> int:
    try:
        from pytrends.request import TrendReq
    except ImportError:
        log.warning("pytrends not installed (pip install -e '.[trends]'); skipping Google Trends")
        return 0

    tax = load_taxonomy()
    pytrends = TrendReq(hl="fr-FR", tz=60)
    stored = 0
    langs = (("fr", settings.market_geo), ("en", ""))
    n_items = sum(len(tax.items[d]) for d in dimensions)
    total_batches, batch_no = len(langs) * -(-n_items // BATCH), 0
    for lang, geo in langs:
        items = [it for d in dimensions for it in tax.items[d].values()]
        for i in range(0, len(items), BATCH):
            report(progress, batch_no, total_batches)
            batch_no += 1
            chunk = items[i : i + BATCH]
            keywords = [it.query_fr if lang == "fr" else it.query_en for it in chunk]
            anchor = ANCHORS[lang]
            try:
                pytrends.build_payload(keywords + [anchor], timeframe="today 3-m", geo=geo)
                df = pytrends.interest_over_time()
            except Exception as e:  # pytrends raises bare exceptions on 429 / format changes
                log.warning("Google Trends batch failed (%s): %s", keywords, e)
                time.sleep(10)
                continue
            if df.empty:
                continue
            weekly = df.drop(columns=["isPartial"], errors="ignore").resample("W-MON", label="left", closed="left").mean()
            anchor_mean = weekly[anchor].mean() or 1.0
            for it, kw in zip(chunk, keywords):
                for ts, value in weekly[kw].items():
                    week = ts.date()
                    scaled = float(value) / anchor_mean * 50  # anchor ≈ 50 on every batch
                    row = session.scalar(
                        select(SearchInterest).where(
                            SearchInterest.code == it.code, SearchInterest.lang == lang,
                            SearchInterest.geo == geo, SearchInterest.week == week,
                        )
                    )
                    if row is None:
                        row = SearchInterest(dimension=it.dimension, code=it.code, keyword=kw, lang=lang, geo=geo, week=week, value=scaled)
                        session.add(row)
                    else:
                        row.value = scaled
                    stored += 1
            session.commit()
            time.sleep(2)  # be gentle: Google rate-limits aggressively
    report(progress, total_batches, total_batches)
    log.info("Google Trends: %d weekly values stored", stored)
    return stored
