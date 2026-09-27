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

    def __init__(self, *a, **kw):
        pass

    def build_payload(self, kw_list, **kw):
        FakeTrendReq.payloads.append(list(kw_list))
        self.kw = kw_list

    def interest_over_time(self):
        (k,) = self.kw
        values = [0] * len(DAYS) if k in FakeTrendReq.silent else [50 + i for i in range(len(DAYS))]
        return pd.DataFrame({k: values, "isPartial": False}, index=DAYS)


@pytest.fixture(autouse=True)
def fake_pytrends(monkeypatch):
    init_db()
    FakeTrendReq.payloads, FakeTrendReq.silent = [], set()
    module = types.ModuleType("pytrends.request")
    module.TrendReq = FakeTrendReq
    monkeypatch.setitem(sys.modules, "pytrends.request", module)
    monkeypatch.setattr(gt, "PAUSE_S", 0)
    monkeypatch.setattr(gt, "BACKOFF_S", 0)
    with SessionLocal() as s:
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
