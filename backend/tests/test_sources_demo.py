from fastapi.testclient import TestClient

import pytest

from app.api.main import app
from app.db import SessionLocal, init_db
from app.demo import seed_demo
from app.scoring.trends import compute_snapshots


@pytest.fixture(scope="module")
def client():
    init_db()
    with SessionLocal() as s:
        seed_demo(s)
        compute_snapshots(s)
    with TestClient(app) as c:
        yield c


def test_sources_are_one_item_per_document_with_all_attributes(client):
    body = client.get("/api/sources", params={"limit": 5}).json()
    assert body["total"] > 5 and len(body["items"]) == 5
    item = body["items"][0]
    assert {"url", "source", "kind", "lang", "date", "quote", "summary", "attributes"} <= set(item)
    assert item["attributes"] and all({"dimension", "code", "label"} <= set(a) for a in item["attributes"])
    dates = [i["date"] for i in body["items"]]
    assert dates == sorted(dates, reverse=True)  # newest first


def test_sources_filters_and_pagination(client):
    by_code = client.get("/api/sources", params={"dimension": "shape", "code": "cat_eye", "limit": 50}).json()
    assert by_code["total"] > 0
    assert all(any(a["code"] == "cat_eye" for a in i["attributes"]) for i in by_code["items"])
    en = client.get("/api/sources", params={"lang": "en", "limit": 50}).json()
    assert en["total"] > 0 and all(i["lang"] == "en" for i in en["items"])
    news = client.get("/api/sources", params={"kind": "news", "limit": 50}).json()
    assert all(i["kind"] == "news" for i in news["items"])
    p1 = client.get("/api/sources", params={"limit": 4}).json()["items"]
    p2 = client.get("/api/sources", params={"limit": 4, "offset": 4}).json()["items"]
    assert {i["id"] for i in p1}.isdisjoint(i["id"] for i in p2)
    recent = client.get("/api/sources", params={"days": 7}).json()["total"]
    assert 0 < recent < client.get("/api/sources").json()["total"]


def test_remove_and_reload_demo(client):
    assert client.get("/api/overview").json()["has_demo"] is True
    removed = client.delete("/api/demo")
    assert removed.status_code == 200
    after = client.get("/api/overview").json()
    assert after["has_demo"] is False
    assert client.get("/api/sources").json()["total"] == 0  # the test DB holds demo data only
    loaded = client.post("/api/demo")
    assert loaded.status_code == 201 and loaded.json()["documents"] > 0
    assert client.get("/api/overview").json()["has_demo"] is True


def test_meta_for_the_app_shell(client):
    body = client.get("/api/meta").json()
    assert set(body) == {"has_demo", "weeks", "running", "last_success", "market_geo"}
    assert body["has_demo"] is True and body["running"] is False
    assert body["weeks"] == sorted(body["weeks"], reverse=True) and len(body["weeks"]) == 12


def test_demo_data_is_never_dated_in_the_future(client):
    from datetime import date
    body = client.get("/api/sources", params={"limit": 50}).json()
    assert all(i["date"] <= date.today().isoformat() for i in body["items"])
