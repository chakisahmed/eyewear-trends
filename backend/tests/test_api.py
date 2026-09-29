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
    assert body["week"] == (week_start(date.today()) - timedelta(weeks=1)).isoformat()  # last complete week
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


def test_run_progress_is_saved_during_each_step(client, monkeypatch):
    import app.jobs.pipeline as pipeline

    seen = {}

    def fake_rss(session, progress=None):
        progress(2, 5)  # e.g. 2 of 5 feeds done
        with SessionLocal() as other:  # what the status endpoint would read right now
            run = other.query(JobRun).order_by(JobRun.id.desc()).first()
            seen["mid"] = (run.current_step, run.step_done, run.step_total)
        return 0

    monkeypatch.setattr(pipeline, "collect_rss", fake_rss)
    client.post("/api/jobs/run", json={"steps": ["rss", "score"]})
    assert seen["mid"] == ("rss", 2, 5)
    progress = client.get("/api/jobs/status").json()["last"]["progress"]
    assert progress == {"step": "score", "label": "Calcul des tendances", "index": 2, "count": 2, "done": None, "total": None}


def test_extraction_reports_articles_done(client):
    from app.extraction.service import extract_pending
    from app.models import Document, Source

    with SessionLocal() as s:
        src = s.query(Source).filter_by(url="test:progress-source").first() or Source(name="Test", kind="press", url="test:progress-source", lang="fr")
        # no eyewear keyword: skipped by the free pre-filter, so no LLM call is made
        s.add_all([Document(source=src, url=f"test:progress:{i}", title="Météo", text="Soleil demain.", lang="fr") for i in range(3)])
        s.commit()
        calls = []
        stats = extract_pending(s, provider=None, progress=lambda d, t: calls.append((d, t)))
    assert stats["irrelevant"] == 3
    assert calls == [(0, 3), (1, 3), (2, 3), (3, 3)]


def test_collection_run_removes_demo_data_first(client, monkeypatch):
    import app.jobs.pipeline as pipeline
    from app.demo import seed_demo

    with SessionLocal() as s:
        seed_demo(s)
    assert client.get("/api/meta").json()["has_demo"] is True
    monkeypatch.setattr(pipeline, "collect_rss", lambda session, progress=None: 0)

    client.post("/api/jobs/run", json={"steps": ["score"]})  # scoring only: demo stays
    assert client.get("/api/meta").json()["has_demo"] is True

    client.post("/api/jobs/run", json={"steps": ["rss", "score"]})  # real collection: demo goes first
    last = client.get("/api/jobs/status").json()["last"]
    assert last["status"] == "success" and last["report"]["demo_removed"] is True
    assert client.get("/api/meta").json()["has_demo"] is False


def test_restart_interrupts_runs_left_running(client):
    with SessionLocal() as s:
        s.add(JobRun(steps=["rss"], status="running"))  # e.g. a run killed by a server restart
        s.commit()
    with TestClient(app) as restarted:  # startup marks it as interrupted
        status = restarted.get("/api/jobs/status").json()
    assert status["running"] is False
    assert status["last"]["status"] == "failed" and "redémarré" in status["last"]["error"]


def test_trend_detail_retail_presence(client):
    from app.models import Product, ProductTag, Source
    now = datetime.now(timezone.utc)
    with SessionLocal() as s:
        a = Source(name="Store A", kind="store", url="https://a.retail.test", lang="fr", country="TN")
        b = Source(name="Store B", kind="store", url="https://b.retail.test", lang="fr", country="FR")
        s.add_all([a, b])
        s.flush()

        def product(src, slug, *, price, currency, rank, seen=now, out=False, kind="optical", code="wood", list_price=None):
            p = Product(source_id=src.id, url=f"{src.url}/{slug}", name=slug.upper(), brand=src.name, price=price,
                        list_price=list_price,
                        currency=currency, rank=rank, image_url=f"{src.url}/{slug}.jpg", seen_at=seen,
                        flags={"out_of_stock": True} if out else None)
            p.tags = [ProductTag(dimension="material", code=code, field="spec:Materials", term=code, rules_version=1),
                      ProductTag(dimension="product_type", code=kind, field="categories", term=kind, rules_version=1)]
            s.add(p)

        product(a, "a1", price=40, currency="TND", rank=1)
        product(a, "a2", price=None, currency="TND", rank=2, out=True)                     # sold out: counted, not priced
        product(a, "a3", price=99, currency="TND", rank=0, seen=now - timedelta(days=30))  # stale: not counted
        product(a, "a4", price=50, currency="TND", rank=3, kind="sun")
        product(a, "a5", price=10, currency="TND", rank=4, code="metal")                  # other attribute
        product(b, "b1", price=100, currency="EUR", rank=2, kind="sun", list_price=200)  # -50 %
        product(b, "b2", price=120, currency="EUR", rank=1)
        s.commit()

    body = client.get("/api/trends/material/wood").json()
    assert body["retail_sku_count"] == 5 and body["retail_store_count"] == 2
    assert body["retail_avg_price"] == [
        {"currency": "TND", "avg": 45.0, "min": 40.0, "max": 50.0, "priced": 2},
        {"currency": "EUR", "avg": 110.0, "min": 100.0, "max": 120.0, "priced": 2}]
    assert body["retail_by_type"] == {"optical": 3, "sun": 2}
    # in stock first, then listing rank, alternating stores
    assert [p["name"] for p in body["retail_sample"]] == ["A1", "B2", "A4", "B1", "A2"]
    assert body["retail_sample"][-1]["out_of_stock"] is True and body["retail_sample"][0]["store"] == "Store A"
    assert body["retail_updated_at"].startswith(now.date().isoformat())
    # only Store B publishes list prices: b1 -50 %, b2 full price -> store baseline 25 %, relative 0 on average
    assert body["retail_markdown"] == {"compared": 2, "discounted": 1, "share_discounted": 0.5, "avg_depth": 0.5,
                                       "relative_depth": 0.0}

    empty = client.get("/api/trends/shape/browline").json()
    assert (empty["retail_sku_count"], empty["retail_avg_price"], empty["retail_sample"], empty["retail_by_type"]) == (0, [], [], {})
    assert empty["retail_updated_at"] is None
    assert empty["retail_markdown"] is None


def test_retail_overview_shape(client):
    body = client.get("/api/retail/overview").json()
    assert set(body) == {"week", "stores", "types", "opportunities", "risks", "skipped_dimensions", "thresholds"}
    assert set(body["skipped_dimensions"]) == {"optical", "sun"}
    assert body["thresholds"] == {"opportunity_share": 0.05, "risk_share": 0.15, "min_tagged": 20}
    for gap in body["opportunities"] + body["risks"]:
        assert {"dimension", "code", "label", "status", "momentum", "sku", "share", "avg_price", "product_type"} <= set(gap)
    assert all({"name", "products", "updated"} <= set(st) for st in body["stores"])
