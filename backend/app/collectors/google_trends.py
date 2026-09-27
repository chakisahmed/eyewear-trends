"""Google Trends search interest for bilingual taxonomy keywords.

Uses pytrends (unofficial). Google scores every request 0-100 in whole numbers against the most
searched term IN THAT REQUEST, so each keyword is requested on its own: its series then runs 0-100
against its own peak over the period. Mixing it with a popular term (e.g. "lunettes") would round
specific terms like "lunettes masque" down to 0. Momentum only uses growth against the keyword's
own history, so the per-keyword scale does not matter there. A keyword that is 0 every week is below
Google's reporting threshold and is not stored at all (no data, rather than a fake flat 0).
Swap for SerpAPI in production for reliability.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.progress import Progress, report
from app.models import SearchInterest
from app.taxonomy import load_taxonomy

log = logging.getLogger(__name__)
PAUSE_S = 2  # between requests: Google rate-limits aggressively
BACKOFF_S = 30  # after a failed request, before retrying it once


def reset_search_interest(session: Session) -> int:
    """Delete collected (non-demo) search interest, e.g. before re-collecting on a new scale."""
    n = session.execute(delete(SearchInterest).where(SearchInterest.is_demo.is_(False))).rowcount
    session.commit()
    return n


def _fetch(pytrends, keyword: str, geo: str):
    for attempt in (1, 2):
        try:
            pytrends.build_payload([keyword], timeframe="today 3-m", geo=geo)
            return pytrends.interest_over_time()
        except Exception as e:  # pytrends raises bare exceptions on 429 / format changes
            log.warning("Google Trends failed for %r (attempt %d): %s", keyword, attempt, e)
            if attempt == 1:
                time.sleep(BACKOFF_S)
    return None


def collect_google_trends(
    session: Session, dimensions: tuple[str, ...] = ("shape", "color", "material"), progress: Progress = None
) -> int:
    try:
        from pytrends.request import TrendReq
    except ImportError:
        log.warning("pytrends not installed (pip install -e '.[trends]'); skipping Google Trends")
        return 0

    tax = load_taxonomy()
    pytrends = TrendReq(hl="fr-FR", tz=60, timeout=(10, 25))
    items = [it for d in dimensions for it in tax.items[d].values()]
    jobs = [(it, lang, geo) for lang, geo in (("fr", settings.market_geo), ("en", "")) for it in items]
    stored = 0
    for n, (it, lang, geo) in enumerate(jobs):
        report(progress, n, len(jobs))
        kw = it.query_fr if lang == "fr" else it.query_en
        df = _fetch(pytrends, kw, geo)
        time.sleep(PAUSE_S)
        if df is None or df.empty or kw not in df:
            continue
        weekly = df[kw].resample("W-MON", label="left", closed="left").mean()
        if not (weekly > 0).any():
            continue  # below Google's threshold: no data, not zeros
        for ts, value in weekly.items():
            week = ts.date()
            row = session.scalar(
                select(SearchInterest).where(
                    SearchInterest.code == it.code, SearchInterest.lang == lang,
                    SearchInterest.geo == geo, SearchInterest.week == week,
                )
            )
            if row is None:
                session.add(SearchInterest(dimension=it.dimension, code=it.code, keyword=kw, lang=lang, geo=geo,
                                           week=week, value=float(value)))
            else:
                row.value, row.keyword = float(value), kw
            stored += 1
        session.commit()
    report(progress, len(jobs), len(jobs))
    log.info("Google Trends: %d weekly values stored", stored)
    return stored
