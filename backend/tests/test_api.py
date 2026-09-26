from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.main import app
from app.db import SessionLocal, init_db
from app.demo import seed_demo
from app.models import JobRun
from app.scoring.trends import compute_snapshots, week_start


@pytest.fixture(scope="module")
def client():
    init_db()
    with SessionLocal() as s:
        seed_demo(s)
        compute_snapshots(s)
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_jobs():
    with SessionLocal() as s:
        s.execute(delete(JobRun))
        s.commit()
    yield


def test_overview_rows_have_8_week_sparklines(client):
    body = client.get("/api/overview").json()
    assert body["week"] == week_start(date.today()).isoformat()
    assert body["has_demo"] is True
    shapes = body["rising"]["shape"]
    assert shapes and all(len(r["spark"]) == 8 for r in shapes)
    assert shapes[0]["spark"][-1] == shapes[0]["mentions"]
    assert all(len(r["spark"]) == 8 for r in body["declining"])


def test_fading_trends_are_listed_as_declining_not_rising(client):
    body = client.get("/api/overview").json()
    declining = {r["code"]: r for r in body["declining"]}
    # demo: rectangle / pastel / y2k are written about as "on the way out"
    assert {"rectangle", "pastel", "y2k"} <= set(declining)
    assert all(r["decline_reason"] in ("volume", "tonalite") for r in declining.values())
    assert declining["rectangle"]["decline_share"] >= 0.5 and declining["rectangle"]["mentions"] > 0
    rising_codes = {r["code"] for rows in body["rising"].values() for r in rows}
    assert rising_codes.isdisjoint(declining)
    detail = client.get("/api/trends/shape/rectangle").json()
    assert detail["status"] == "en_baisse" and detail["stance"]["declining"] > 0


def test_week_param_and_week_list(client):
    weeks = client.get("/api/weeks").json()
    assert len(weeks) == 12 and weeks == sorted(weeks, reverse=True)
    older = weeks[3]
    assert client.get("/api/overview", params={"week": older}).json()["week"] == older
    # any day of the week resolves to its Monday
    mid_week = (date.fromisoformat(older) + timedelta(days=3)).isoformat()
    assert client.get("/api/trends/shape", params={"week": mid_week}).json()["week"] == older
    assert client.get("/api/overview", params={"week": "2001-01-01"}).status_code == 404


def test_trend_detail(client):
    body = client.get("/api/trends/shape/cat_eye").json()
    assert body["label"] == "Œil de chat" and body["dimension_label"] == "Forme de monture"
    assert len(body["weeks"]) == len(body["mentions"]) == 12
    # steady demo growth (3 -> 14/week) scores as rising or peaking depending on the growth vs the 4-week base
    assert body["status"] in ("en_hausse", "au_pic")
    assert (body["rising_streak"] >= 1) == (body["status"] == "en_hausse")
    assert body["stats"]["this_week"] == body["mentions"][-1]
    assert 0 < body["stats"]["share"] <= 1
    assert len(body["search"]["fr"]) == len(body["search"]["world"]) == 12
    assert body["stance"]["rising"] > 0
    assert 0 < len(body["evidence"]) <= 10
    assert client.get("/api/trends/shape/triangle").status_code == 404
    assert client.get("/api/trends/nope/cat_eye").status_code == 404


def test_mentions_pagination_and_filters(client):
    page1 = client.get("/api/mentions", params={"dimension": "color", "limit": 5}).json()
    page2 = client.get("/api/mentions", params={"dimension": "color", "limit": 5, "offset": 5}).json()
    assert page1["total"] == page2["total"] > 10
    assert {i["url"] + i["code"] for i in page1["items"]}.isdisjoint({i["url"] + i["code"] for i in page2["items"]})
    assert all(i["dimension"] == "color" for i in page1["items"])
    recent = client.get("/api/mentions", params={"days": 7}).json()
    assert recent["total"] < client.get("/api/mentions").json()["total"]


def test_csv_export_is_excel_friendly(client):
    r = client.get("/api/export/color.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="tendances-couleurs-' in r.headers["content-disposition"]
    text = r.content.decode("utf-8")
    assert text.startswith("﻿")
    header, first = text.lstrip("﻿").splitlines()[:2]
    assert header.split(";")[0] == "Attribut" and len(header.split(";")) == 9
    assert "," in first.split(";")[3]  # decimal comma


def test_job_run_records_status(client):
    idle = client.get("/api/jobs/status").json()
    assert idle["running"] is False and idle["last"] is None

    started = client.post("/api/jobs/run", json={"steps": ["score"]})
    assert started.status_code == 202 and started.json()["status"] == "running"

    # TestClient runs background tasks before returning, so the run has finished here.
    after = client.get("/api/jobs/status").json()
    assert after["running"] is False
    assert after["last_success"]["id"] == started.json()["id"]
    assert after["last_success"]["report"]["score"] > 0


def test_job_run_rejects_concurrent_and_unknown_steps(client):
    with SessionLocal() as s:
        s.add(JobRun(steps=["score"], status="running"))
        s.commit()
    assert client.post("/api/jobs/run", json={"steps": ["score"]}).status_code == 409
    assert client.get("/api/jobs/status").json()["running"] is True
    assert client.post("/api/jobs/run", json={"steps": ["hack"]}).status_code == 400


def test_stale_running_job_is_released(client):
    with SessionLocal() as s:
        s.add(JobRun(steps=["score"], status="running", started_at=datetime.now(timezone.utc) - timedelta(hours=5)))
        s.commit()
    status = client.get("/api/jobs/status").json()
    assert status["running"] is False
    assert status["last"]["status"] == "failed"
    assert client.post("/api/jobs/run", json={"steps": ["score"]}).status_code == 202


def test_failed_run_is_recorded(client, monkeypatch):
    import app.jobs.pipeline as pipeline

    def boom(session):
        raise RuntimeError("collecteur en panne")

    monkeypatch.setattr(pipeline, "compute_snapshots", boom)
    run_id = client.post("/api/jobs/run", json={"steps": ["score"]}).json()["id"]
    last = client.get("/api/jobs/status").json()["last"]
    assert last["id"] == run_id and last["status"] == "failed"
    assert "collecteur en panne" in last["error"]
