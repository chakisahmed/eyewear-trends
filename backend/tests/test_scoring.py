from datetime import date

import pytest

from app.scoring.trends import classify, growth, pooled_tone, score_series, week_start


def test_week_start_is_monday():
    assert week_start(date(2026, 9, 26)) == date(2026, 9, 21)  # Saturday -> Monday


def test_growth_vs_previous_four_weeks():
    assert growth([4, 4, 4, 4, 8]) == pytest.approx(1.0)
    assert growth([10, 10, 10, 10, 5]) == pytest.approx(-0.5)
    assert growth([5]) == 0.0


def test_growth_small_base_is_floored():
    # from 0 to 3 mentions: base floored at 1 so growth is 300%, not infinite
    assert growth([0, 0, 3]) == pytest.approx(3.0)


def status_of(values):
    return score_series(values)[-1][1]


def test_classify_thresholds():
    assert classify([2, 2, 2, 5], 1.5) == "en_hausse"
    assert classify([8, 8, 8, 3], -0.6) == "en_baisse"
    assert classify([5, 8, 6, 6], 0.0) == "stable"


def test_steady_climb_stays_rising_even_below_25_percent():
    # +1 mention/week: only ~+12 % vs the 4-week base at the end, but still climbing at the same pace
    series = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
    assert growth(series) < 0.25
    assert status_of(series) == "en_hausse"


def test_plateau_after_rise_is_peak():
    assert status_of([4, 6, 9, 13, 16, 17, 17, 16]) == "au_pic"


def test_decelerating_climb_near_top_is_peak():
    # still inching up, but far slower than the +2/week of a month ago
    assert status_of([1, 2, 3, 5, 7, 9, 11, 13, 14, 14.5, 14.8, 15]) == "au_pic"


def test_noisy_flat_series_with_one_low_week_is_stable():
    # one low week (4) must not count as "a real rise" to the current level
    assert status_of([4, 4, 3, 6, 4, 6, 6, 6, 5, 6, 6, 6]) == "stable"


def test_flat_series_is_stable_not_peak():
    # current value equals the 8-week high, but there was never a real rise
    assert status_of([12, 13, 11, 12, 12, 11, 12, 13]) == "stable"


def test_off_the_top_is_stable():
    # fell back well below its high without dropping 25 % vs the recent base
    assert status_of([4, 8, 12, 15, 14, 12, 11, 11]) == "stable"


def test_noise_does_not_break_a_steady_climb():
    assert status_of([3, 5, 4, 6, 6, 8, 7, 9, 9, 11, 10, 12]) == "en_hausse"


def test_score_series_blends_search():
    mentions = [4, 4, 4, 4, 4]
    flat = score_series(mentions)
    boosted = score_series(mentions, [20, 20, 20, 20, 60])
    assert flat[-1][0] == 0
    assert boosted[-1][0] > 0.5


def test_score_series_uses_only_past_data():
    series = score_series([1, 1, 1, 1, 10, 1])
    assert series[4][1] == "en_hausse"
    assert series[5][1] == "en_baisse"


# --- tone: volume and "fading" coverage are separate signals ---



def weeks_of(rising=0.0, neutral=0.0, declining=0.0, n=8):
    return [{"rising": rising, "neutral": neutral, "declining": declining} for _ in range(n)]


def test_fading_coverage_is_decline_even_with_steady_volume():
    # 5 mentions a week, all saying "adieu les rectangulaires": volume is flat, tone says it's over
    stances = weeks_of(declining=5)
    volume = [sum(w.values()) for w in stances]
    assert volume == [5] * 8  # declining mentions still count as attention
    assert score_series(volume, stances=stances)[-1][1] == "en_baisse"


def test_fading_coverage_beats_rising_volume():
    # more and more articles, but mostly calling the trend dead: a decline, not a rise
    stances = [{"rising": 1, "declining": d} for d in (1, 2, 3, 5, 7, 9, 11, 13)]
    volume = [sum(w.values()) for w in stances]
    momentum, status = score_series(volume, stances=stances)[-1]
    assert momentum > 0.25 and status == "en_baisse"


def test_mixed_coverage_keeps_volume_status():
    stances = [{"rising": r, "declining": 1} for r in (2, 3, 4, 5, 6, 8, 10, 12)]
    volume = [sum(w.values()) for w in stances]
    assert score_series(volume, stances=stances)[-1][1] == "en_hausse"


def test_one_negative_article_cannot_flip_status():
    # a single "fading" mention in 4 weeks is below the minimum sample for tone
    stances = weeks_of(n=7) + [{"declining": 1.0}]
    assert pooled_tone(stances[-4:]) == (None, None)
    assert score_series([sum(w.values()) for w in stances], stances=stances)[-1][1] != "en_baisse"


def test_tone_values():
    tone, share = pooled_tone([{"rising": 3, "neutral": 1, "declining": 0}, {"rising": 1, "neutral": 1, "declining": 2}])
    assert tone == pytest.approx((4 - 2) / 8) and share == pytest.approx(2 / 8)
