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
PAUSE_S = 4  # between requests: Google rate-limits aggressively (HTTP 429 after a few dozen quick requests)
BACKOFF_S = (30, 90)  # waits before the 2nd and 3rd attempt of a failed keyword
STOP_AFTER_FAILURES = 3  # consecutive keywords failing all attempts: Google is blocking us, stop the run
# An empty answer is ambiguous: too little volume for the period, or a soft rate limit. A keyword that always
# has volume in the same geo tells them apart: control empty too -> throttled; control fine -> no volume.
CONTROL_KEYWORDS = {"fr": "lunettes", "en": "glasses"}
NO_VOLUME = object()  # _fetch result for a keyword Google has no data for


def reset_search_interest(session: Session) -> int:
    """Delete collected (non-demo) search interest, e.g. before re-collecting on a new scale."""
    n = session.execute(delete(SearchInterest).where(SearchInterest.is_demo.is_(False))).rowcount
    session.commit()
    return n


def _answers(pytrends, keyword: str, geo: str) -> bool:
    """Does Google return data for this (high-volume) keyword right now?"""
    try:
        pytrends.build_payload([keyword], timeframe="today 3-m", geo=geo)
        df = pytrends.interest_over_time()
        return not df.empty and keyword in df and bool((df[keyword] > 0).any())
    except Exception:
        return False


def _fetch(pytrends, keyword: str, geo: str, control: str | None = None):
    """DataFrame with data, NO_VOLUME, or None (still failing after all attempts: rate-limited)."""
    attempts = len(BACKOFF_S) + 1
    for attempt in range(1, attempts + 1):
        try:
            pytrends.build_payload([keyword], timeframe="today 3-m", geo=geo)
            df = pytrends.interest_over_time()
            if df.empty:
                if control and _answers(pytrends, control, geo):
                    return NO_VOLUME  # Google is answering: this keyword simply has too little volume
                raise RuntimeError("empty answer and the control keyword is empty too (soft rate limit)")
            return df
        except Exception as e:  # pytrends raises bare exceptions on 429 / format changes
            log.warning("Google Trends failed for %r (attempt %d/%d): %s", keyword, attempt, attempts, e)
            if attempt < attempts:
                time.sleep(BACKOFF_S[attempt - 1])
    return None


def collect_google_trends(
    session: Session, dimensions: tuple[str, ...] = ("shape", "color", "material"), progress: Progress = None,
    only_missing: bool = False,
) -> int:
    """Store weekly interest per keyword. only_missing: request just the (attribute, language, geo) pairs
    with no data yet, e.g. to fill the gaps left by a rate-limited run without re-downloading the rest."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        log.warning("pytrends not installed (pip install -e '.[trends]'); skipping Google Trends")
        return 0

    tax = load_taxonomy()
    pytrends = TrendReq(hl="fr-FR", tz=60, timeout=(10, 25))
    items = [it for d in dimensions for it in tax.items[d].values()]
    jobs = [(it, lang, geo) for lang, geo in (("fr", settings.market_geo), ("en", "")) for it in items]
    if only_missing:
        have = set(session.execute(select(SearchInterest.code, SearchInterest.lang, SearchInterest.geo)
                                   .where(SearchInterest.is_demo.is_(False)).distinct()).all())
        jobs = [(it, lang, geo) for it, lang, geo in jobs if (it.code, lang, geo) not in have]
        log.info("Google Trends: %d keyword/geo pairs without data", len(jobs))
    stored = 0
    ok = silent = failed = in_a_row = 0
    for n, (it, lang, geo) in enumerate(jobs):
        report(progress, n, len(jobs))
        kw = it.query_fr if lang == "fr" else it.query_en
        df = _fetch(pytrends, kw, geo, CONTROL_KEYWORDS.get(lang))
        time.sleep(PAUSE_S)
        if df is NO_VOLUME:
            silent, in_a_row = silent + 1, 0
            continue
        if df is None:
            failed, in_a_row = failed + 1, in_a_row + 1
            if in_a_row >= STOP_AFTER_FAILURES:
                log.warning("Google Trends: %d keywords in a row rate-limited; stopping (%d not attempted). "
                            "Rerun later: python -m app.cli refresh-search --missing", in_a_row, len(jobs) - n - 1)
                break
            continue
        in_a_row = 0
        if df.empty or kw not in df or not (df[kw] > 0).any():
            silent += 1  # below Google's threshold: no data, not zeros
            continue
        ok += 1
        weekly = df[kw].resample("W-MON", label="left", closed="left").mean()
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
    log.info("Google Trends: %d keywords stored (%d weekly values), %d without Google volume, %d rate-limited%s",
             ok, stored, silent, failed, " -> rerun with --missing" if failed else "")
    return stored
