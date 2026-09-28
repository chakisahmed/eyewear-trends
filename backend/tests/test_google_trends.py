"""Google Trends collector against a fake pytrends: no real network."""

import sys
import types
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import delete, select

import app.collectors.google_trends as gt
from app.db import SessionLocal, init_db
from app.models import SearchInterest
from app.taxonomy import load_taxonomy

DAYS = pd.date_range("2026-07-06", periods=28, freq="D")


class FakeTrendReq:
    payloads: list[list[str]] = []
    silent: set[str] = set()  # keywords Google has no volume for
    failures: dict[str, int] = {}  # keyword -> how many more requests fail (HTTP 429)

    def __init__(self, *a, **kw):
        pass

    def build_payload(self, kw_list, **kw):
        FakeTrendReq.payloads.append(list(kw_list))
        self.kw = kw_list

    def interest_over_time(self):
        (k,) = self.kw
        if FakeTrendReq.failures.get(k, 0) > 0:
            FakeTrendReq.failures[k] -= 1
            raise Exception("The request failed: Google returned a response with code 429")
        values = [0] * len(DAYS) if k in FakeTrendReq.silent else [50 + i for i in range(len(DAYS))]
        return pd.DataFrame({k: values, "isPartial": False}, index=DAYS)


@pytest.fixture(autouse=True)
def fake_pytrends(monkeypatch):
    init_db()
    FakeTrendReq.payloads, FakeTrendReq.silent, FakeTrendReq.failures = [], set(), {}
    module = types.ModuleType("pytrends.request")
    module.TrendReq = FakeTrendReq
    monkeypatch.setitem(sys.modules, "pytrends.request", module)
    monkeypatch.setattr(gt, "PAUSE_S", 0)
    monkeypatch.setattr(gt, "BACKOFF_S", (0, 0))
    with SessionLocal() as s:
        s.execute(delete(SearchInterest))
        s.commit()
    yield
    with SessionLocal() as s:  # leave nothing behind: other tests seed demo search data on the same keys
        s.execute(delete(SearchInterest))
        s.commit()


def test_one_keyword_per_request_and_silent_keywords_store_nothing():
    shapes = list(load_taxonomy().items["shape"].values())
    FakeTrendReq.silent = {shapes[0].query_fr}
    with SessionLocal() as s:
        gt.collect_google_trends(s, dimensions=("shape",))
        rows = s.scalars(select(SearchInterest)).all()
    assert FakeTrendReq.payloads and all(len(p) == 1 for p in FakeTrendReq.payloads)  # no anchor term
    assert len(FakeTrendReq.payloads) == 2 * len(shapes)                                  # FR + EN per attribute
    fr_codes = {r.code for r in rows if r.lang == "fr"}
    assert shapes[0].code not in fr_codes and shapes[1].code in fr_codes                  # silent -> no rows, not zeros
    assert max(r.value for r in rows) > 50                                                 # own scale, not rescaled to ~0


def test_reset_keeps_demo_rows():
    with SessionLocal() as s:
        s.add_all([
            SearchInterest(dimension="shape", code="round", keyword="x", lang="fr", geo="FR", week=date(2026, 7, 6), value=1, is_demo=False),
            SearchInterest(dimension="shape", code="round", keyword="x", lang="fr", geo="FR", week=date(2026, 7, 13), value=1, is_demo=True),
        ])
        s.commit()
        assert gt.reset_search_interest(s) == 1
        assert [r.is_demo for r in s.scalars(select(SearchInterest))] == [True]


def test_rate_limited_keyword_is_retried_with_backoff():
    shapes = list(load_taxonomy().items["shape"].values())
    FakeTrendReq.failures = {shapes[0].query_en: 2, shapes[1].query_en: 5}  # recovers on the 3rd try / never
    with SessionLocal() as s:
        gt.collect_google_trends(s, dimensions=("shape",))
        world = {r.code for r in s.scalars(select(SearchInterest).where(SearchInterest.geo == ""))}
    assert shapes[0].code in world                    # 2 failures, then success: kept
    assert shapes[1].code not in world                # still failing after 3 attempts: skipped, not fatal
    assert sum(p == [shapes[0].query_en] for p in FakeTrendReq.payloads) == 3


def test_only_missing_requests_just_the_gaps():
    shapes = list(load_taxonomy().items["shape"].values())
    with SessionLocal() as s:
        gt.collect_google_trends(s, dimensions=("shape",))
        s.execute(delete(SearchInterest).where(SearchInterest.code == shapes[0].code, SearchInterest.geo == ""))
        s.commit()
        FakeTrendReq.payloads = []
        stored = gt.collect_google_trends(s, dimensions=("shape",), only_missing=True)
    assert FakeTrendReq.payloads == [[shapes[0].query_en]]  # only the worldwide gap, nothing else re-downloaded
    assert stored > 0


def test_run_stops_when_google_keeps_rate_limiting():
    shapes = list(load_taxonomy().items["shape"].values())
    FakeTrendReq.failures = {it.query_fr: 99 for it in shapes}  # every French request blocked
    with SessionLocal() as s:
        gt.collect_google_trends(s, dimensions=("shape",))
    attempted = {p[0] for p in FakeTrendReq.payloads}
    assert len(attempted) == gt.STOP_AFTER_FAILURES          # stopped after 3 keywords, didn't hammer on


def empty_for(monkeypatch, keywords: set[str]):
    """Google answers an empty frame for these keywords (low volume, or throttling if the control is in it)."""
    real = FakeTrendReq.interest_over_time

    def maybe_empty(self):
        (k,) = self.kw
        return pd.DataFrame() if k in keywords else real(self)

    monkeypatch.setattr(FakeTrendReq, "interest_over_time", maybe_empty)


def test_empty_keyword_with_a_healthy_control_is_no_volume_not_a_block(monkeypatch):
    """Low-volume keywords (e.g. 'lunettes œil de chat' in France over 3 months) come back empty too. If the
    control keyword ('lunettes') answers with data, Google is fine: no retries, no stop, the run goes on."""
    shapes = list(load_taxonomy().items["shape"].values())
    quiet = {it.query_fr for it in shapes[:4]}  # 4 in a row: would trip the stop rule if miscounted
    empty_for(monkeypatch, quiet)
    with SessionLocal() as s:
        gt.collect_google_trends(s, dimensions=("shape",))
        fr = {r.code for r in s.scalars(select(SearchInterest).where(SearchInterest.lang == "fr"))}
    assert not {it.code for it in shapes[:4]} & fr and shapes[4].code in fr  # the run continued past them
    assert all(sum(p == [kw] for p in FakeTrendReq.payloads) == 1 for kw in quiet)  # asked once each, no retries


def test_empty_keyword_and_empty_control_is_a_soft_block(monkeypatch):
    """Throttled, Google answers empty for everything, the control included: retry, then stop the run."""
    shapes = list(load_taxonomy().items["shape"].values())
    empty_for(monkeypatch, {it.query_fr for it in shapes} | {gt.CONTROL_KEYWORDS["fr"]})
    with SessionLocal() as s:
        gt.collect_google_trends(s, dimensions=("shape",))
    attempted = [p[0] for p in FakeTrendReq.payloads if p[0] != gt.CONTROL_KEYWORDS["fr"]]
    assert len(set(attempted)) == gt.STOP_AFTER_FAILURES                     # stopped after 3 blocked keywords
    assert attempted.count(shapes[0].query_fr) == len(gt.BACKOFF_S) + 1      # each one retried
