"""Weekly trend scoring.

For each taxonomy attribute and week, two separate signals:
  mentions       VOLUME = Σ source_weight over that week's mentions. Every mention is attention,
                 whatever it says ("l'œil de chat revient" and "adieu l'œil de chat" both count).
  tone           TONE over the last 4 weeks, pooled: (rising − declining) / all mentions, in −1..+1
  decline_share  share of those pooled mentions that describe the attribute as fading (0..1)
  momentum       volume growth vs the previous 4 weeks, blended with Google Trends growth
  status         en_hausse | au_pic | stable | en_baisse | faible

Status rules (see classify):
  en_hausse  momentum ≥ +25 %, OR near its 8-week high and still climbing at an
             unchanged pace (steady growers stay "en hausse" even when the
             percentage growth shrinks as the base grows)
  au_pic     near its 8-week high after a real rise, but growth has slowed or stopped
  en_baisse  momentum ≤ −25 %, OR at least half of the last 4 weeks' mentions call it fading
             (tone overrides volume: lots of "it's over" articles are a decline, not a rise)
  stable     everything else
  faible     fewer than MIN_SAMPLE weighted mentions over the last 4 weeks: too little data for any
             trend claim (3 mentions going to 9 is not "+200 %" news). Overrides the rules above.
Pace is a least-squares slope over 4 weeks (vs the 4 before), which smooths weekly noise.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Document, Mention, SearchInterest, Source, TrendSnapshot

SOURCE_WEIGHTS = {"store": 1.5, "press": 1.0, "news": 1.0, "social": 0.6}
STANCES = ("rising", "neutral", "declining")
BASELINE_WEEKS = 4
PEAK_WINDOW = 8
RISING, FALLING = 0.25, -0.25
SEARCH_BLEND = 0.3  # share of momentum coming from Google Trends when present
NEAR_HIGH = 0.9  # "near the top" = at least 90 % of the 8-week high
MIN_RISE = 0.25  # real climb: the fitted 8-week rise must be ≥ 25 % of the high (and ≥ 1 mention)
SUSTAINED = 0.5  # still climbing at ≥ half the previous pace = sustained rise, not a peak
PACE_WEEKS = 4  # pace = least-squares slope over the last 4 weeks, compared with the 4 before
TONE_WEEKS = 4  # tone is pooled over the last 4 weeks so one article cannot flip it
FADING_SHARE = 0.5  # ≥ 50 % of pooled mentions calling it fading => en_baisse
MIN_TONE_MENTIONS = 3.0  # weighted mentions needed over TONE_WEEKS before tone may decide the status
MIN_SAMPLE = 5.0  # weighted mentions over the last 4 weeks needed before any status other than "faible"
SAMPLE_WEEKS = 4


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def growth(values: list[float], min_base: float = 1.0) -> float:
    """Growth of the last value versus the mean of up to BASELINE_WEEKS previous values."""
    if len(values) < 2:
        return 0.0
    base = mean(values[-1 - BASELINE_WEEKS : -1])
    return (values[-1] - base) / max(base, min_base)


def slope(values: list[float]) -> float:
    """Least-squares change per week — robust to one noisy week, unlike first-vs-last."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean, y_mean = (n - 1) / 2, mean(values)
    return sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values)) / sum((i - x_mean) ** 2 for i in range(n))


def pace(values: list[float]) -> tuple[float, float]:
    """(recent, prior) weekly slope: last PACE_WEEKS weeks vs the PACE_WEEKS before (prior = recent if too short)."""
    recent = slope(values[-PACE_WEEKS:])
    before = values[-2 * PACE_WEEKS : -PACE_WEEKS]
    return recent, (slope(before) if len(before) >= 3 else recent)


def classify(values: list[float], momentum: float) -> str:
    current = values[-1] if values else 0.0
    if momentum >= RISING:
        return "en_hausse"
    if momentum <= FALLING:
        return "en_baisse"
    window = values[-PEAK_WINDOW:]
    if current <= 0 or len(window) < 4:
        return "stable"
    high = max(window)
    fitted_rise = slope(window) * (len(window) - 1)  # uses every week, so one noisy week can't fake a climb
    if current < NEAR_HIGH * high or fitted_rise < max(1.0, MIN_RISE * high):
        return "stable"
    recent, prior = pace(values)
    if momentum > 0 and recent > 0 and recent >= SUSTAINED * max(prior, 0.0):
        return "en_hausse"  # steady climb near the top: not a peak yet
    return "au_pic"


def pooled_tone(stances: list[dict[str, float]]) -> tuple[float | None, float | None]:
    """(tone, decline_share) over the given weeks' weighted stance counts; (None, None) if too few mentions."""
    totals = {k: sum(w.get(k, 0.0) for w in stances) for k in STANCES}
    total = sum(totals.values())
    if total < MIN_TONE_MENTIONS:
        return None, None
    return (totals["rising"] - totals["declining"]) / total, totals["declining"] / total


def score_series(
    mentions: list[float],
    search: list[float | None] | None = None,
    stances: list[dict[str, float]] | None = None,
) -> list[tuple[float, str]]:
    """Momentum and status for every week of a series, using only data up to that week.

    `stances` (optional) holds each week's weighted {rising, neutral, declining} counts; when most
    recent mentions call the attribute fading, the status is en_baisse whatever the volume does.
    """
    out = []
    for i in range(len(mentions)):
        hist = mentions[: i + 1]
        m = growth(hist)
        if search:
            s_hist = [v for v in search[: i + 1] if v is not None]
            if len(s_hist) >= 2 and search[i] is not None:
                m = (1 - SEARCH_BLEND) * m + SEARCH_BLEND * growth(s_hist, min_base=5.0)
        status = classify(hist, m)
        if stances:
            _, decline_share = pooled_tone(stances[max(0, i - TONE_WEEKS + 1) : i + 1])
            if decline_share is not None and decline_share >= FADING_SHARE:
                status = "en_baisse"
        if sum(hist[-SAMPLE_WEEKS:]) < MIN_SAMPLE:
            status = "faible"  # not enough evidence, whatever the percentages say
        out.append((round(m, 4), status))
    return out


def compute_snapshots(session: Session, weeks: int = 12, today: date | None = None) -> int:
    today = today or date.today()
    last = week_start(today)
    week_list = [last - timedelta(weeks=n) for n in range(weeks - 1, -1, -1)]
    start = week_list[0]

    # weighted stance counts per attribute and week: counts[key][week] = {"rising": x, "neutral": y, "declining": z}
    counts: dict[tuple[str, str], dict[date, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    rows = session.execute(
        select(Mention.dimension, Mention.code, Mention.stance, Mention.occurred_on, Source.kind)
        .join(Document, Mention.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
        .where(Mention.occurred_on >= start)
    ).all()
    for dim, code, stance, day, kind in rows:
        counts[(dim, code)][week_start(day)][stance] += SOURCE_WEIGHTS.get(kind, 1.0)

    search: dict[tuple[str, str], dict[date, list[float]]] = defaultdict(lambda: defaultdict(list))
    for si in session.scalars(select(SearchInterest).where(SearchInterest.week >= start)):
        search[(si.dimension, si.code)][week_start(si.week)].append(si.value)

    session.execute(delete(TrendSnapshot).where(TrendSnapshot.week >= start))
    written = 0
    for key in set(counts) | set(search):
        dim, code = key
        st_series = [dict(counts[key].get(w, {})) for w in week_list]
        m_series = [sum(st.values()) for st in st_series]
        s_series = [mean(search[key][w]) if search[key].get(w) else None for w in week_list]
        has_search = any(v is not None for v in s_series)
        scored = score_series(m_series, s_series if has_search else None, st_series)
        for i, (w, m, s, (mom, status)) in enumerate(zip(week_list, m_series, s_series, scored)):
            tone, decline_share = pooled_tone(st_series[max(0, i - TONE_WEEKS + 1) : i + 1])
            session.add(TrendSnapshot(
                dimension=dim, code=code, week=w, mentions=m, search=s, momentum=mom, status=status,
                tone=None if tone is None else round(tone, 4),
                decline_share=None if decline_share is None else round(decline_share, 4),
            ))
            written += 1
    session.commit()
    return written
