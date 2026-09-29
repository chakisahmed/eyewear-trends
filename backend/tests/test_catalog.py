"""Catalog history, read side: baselines, new and retired frames, the creator-brand breakdown, store status and the brief.
Pure database reads on an in-memory SQLite; `now` is always explicit."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors.stores.config import parse_store_configs
from app.db import Base
from app.models import Product, ProductTag, Source, StoreCrawl
from app.scoring import catalog

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
DAY = timedelta(days=1)
HOUR = timedelta(hours=1)
BASELINE = NOW - 20 * DAY  # a creator store's first complete crawl


@pytest.fixture
def s():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def add_store(s, name: str, country: str, first_ok: datetime | None = BASELINE) -> Source:
    src = Source(name=name, kind="store", url=f"https://{name.lower().replace(' ', '')}.test/", lang="en", country=country)
    s.add(src)
    s.flush()
    if first_ok:
        add_crawl(s, src, "ok", first_ok)
    return src


def add_crawl(s, src, status: str, finished: datetime, **kw) -> None:
    s.add(StoreCrawl(source_id=src.id, status=status, trigger="batch", started_at=finished - HOUR, finished_at=finished, **kw))


def add_product(s, src, slug: str, *, first_seen: datetime, active: bool = True, dropped: datetime | None = None,
                tags=(("shape", "round"),)) -> Product:
    p = Product(source_id=src.id, url=f"{src.url}{slug}", name=slug.upper(), seen_at=NOW, first_seen_at=first_seen,
                is_active=active, dropped_at=dropped)
    p.tags = [ProductTag(dimension=d, code=c, field="spec", term=c, rules_version=10, supplier_code=code)
              for d, c, *rest in tags for code in [rest[0] if rest else None]]
    s.add(p)
    return p


# --- baselines, new and retired --------------------------------------------------------------------

def test_a_stores_history_starts_at_its_first_complete_crawl_only(s):
    a, b, c = (add_store(s, n, "ES", first_ok=None) for n in ("A", "B", "C"))
    add_crawl(s, a, "incomplete", NOW - 30 * DAY)
    add_crawl(s, a, "failed", NOW - 29 * DAY)
    add_crawl(s, a, "ok", NOW - 10 * DAY)
    add_crawl(s, a, "ok", NOW - 3 * DAY)                     # a later complete crawl does not move the baseline
    add_crawl(s, b, "failed", NOW - DAY)                     # never a complete one
    s.add(StoreCrawl(source_id=c.id, status="running", trigger="batch", started_at=NOW - HOUR))
    s.commit()
    assert catalog.baselines(s) == {a.id: NOW - 10 * DAY}


def test_without_a_baseline_nothing_is_new_or_retired(s):
    src = add_store(s, "Etnia", "ES", first_ok=None)
    p = add_product(s, src, "a", first_seen=NOW - DAY)
    q = add_product(s, src, "b", first_seen=NOW - 5 * DAY, active=False, dropped=NOW - DAY)
    s.commit()
    base = catalog.baselines(s)
    assert not catalog.is_new(p, base, NOW) and not catalog.is_retired(q, base, NOW)
    assert catalog.new_by_attribute(s, NOW)["stores"] == [] and catalog.catalog_brief(s, NOW) == []


def test_new_means_after_the_baseline_and_within_30_days(s):
    src = add_store(s, "Etnia", "ES")                                          # baseline: 20 days ago
    before = add_product(s, src, "old", first_seen=BASELINE - 5 * DAY)         # known before the log: baseline
    at = add_product(s, src, "at", first_seen=BASELINE)                        # first seen in the baseline crawl itself
    fresh = add_product(s, src, "fresh", first_seen=BASELINE + DAY)
    s.commit()
    base = catalog.baselines(s)
    assert [catalog.is_new(p, base, NOW) for p in (before, at, fresh)] == [False, False, True]
    assert catalog.is_new(fresh, base, BASELINE + DAY + 31 * DAY) is False    # a month later it is no longer news


def test_retired_needs_a_drop_inside_the_window_and_not_to_have_come_back(s):
    src = add_store(s, "Etnia", "ES")
    dropped = add_product(s, src, "gone", first_seen=BASELINE - DAY, active=False, dropped=NOW - 3 * DAY)
    long_ago = add_product(s, src, "older", first_seen=BASELINE - DAY, active=False, dropped=NOW - 40 * DAY)
    back = add_product(s, src, "back", first_seen=BASELINE - DAY, active=True, dropped=None)   # returned: dropped_at cleared
    backfilled = add_product(s, src, "legacy", first_seen=BASELINE - DAY, active=False, dropped=None)  # inactive before the history
    s.commit()
    base = catalog.baselines(s)
    assert [catalog.is_retired(p, base, NOW) for p in (dropped, long_ago, back, backfilled)] == [True, False, False, False]
    assert [p.name for p, _ in catalog.retired_products(s, NOW)] == ["GONE"]


# --- what creator brands added ----------------------------------------------------------------------

def seed_creator(s, n_new: int, n_old: int = 10):
    """A creator store: n_old old frames (round), n_new new ones (round and square, colours with two variant codes)."""
    etnia = add_store(s, "Etnia", "ES")
    for i in range(n_old):
        add_product(s, etnia, f"old{i}", first_seen=BASELINE - DAY, tags=(("shape", "square"),))
    for i in range(n_new):
        shape = "round" if i % 5 else "square"
        add_product(s, etnia, f"new{i}", first_seen=BASELINE + DAY, tags=(
            ("shape", shape), ("color", "blue", "BL"), ("color", "blue", "BL/HV")))    # one frame, two blue codes
    add_product(s, etnia, "cut", first_seen=BASELINE - DAY, active=False, dropped=NOW - DAY)
    s.commit()
    return etnia


def test_the_breakdown_gives_shares_only_from_ten_new_frames_and_counts_a_frame_once(s):
    seed_creator(s, n_new=10)
    data = catalog.new_by_attribute(s, NOW)
    assert (data["new"], data["catalog"], data["retired"]) == (10, 20, 1)
    assert data["stores"] == [{"name": "Etnia", "new": 10, "retired": 1}]
    got = {(i["dimension"], i["code"]): i for i in data["items"]}
    blue = got["color", "blue"]
    assert (blue["new"], blue["share_new"], blue["share_catalog"]) == (10, 1.0, 0.5)   # 10 frames, not 20 tags; 10 of 20 in the catalog
    assert (got["shape", "round"]["new"], got["shape", "square"]["new"]) == (8, 2)
    assert got["shape", "round"]["share_new"] == 0.8 and got["shape", "round"]["share_catalog"] == 0.4
    assert [i["new"] for i in data["items"]] == sorted((i["new"] for i in data["items"]), reverse=True)


def test_below_ten_new_frames_only_counts_are_given(s):
    seed_creator(s, n_new=9)
    data = catalog.new_by_attribute(s, NOW)
    assert data["new"] == 9 and all(i["share_new"] is None and i["share_catalog"] is None for i in data["items"])


def test_tunisian_retailers_are_not_a_design_signal_and_stores_without_history_are_left_out(s):
    seed_creator(s, n_new=10)
    tn = add_store(s, "Outika", "TN")
    for i in range(15):
        add_product(s, tn, f"t{i}", first_seen=BASELINE + DAY, tags=(("shape", "aviator"),))
    add_store(s, "Morel", "FR", first_ok=None)                                   # creator brand, no complete crawl yet
    s.commit()
    data = catalog.new_by_attribute(s, NOW)
    assert data["new"] == 10 and [st["name"] for st in data["stores"]] == ["Etnia"]
    assert ("shape", "aviator") not in {(i["dimension"], i["code"]) for i in data["items"]}


# --- store status ------------------------------------------------------------------------------------

def cfgs(*every: int) -> dict:
    yaml = "stores:\n" + "".join(
        f"  st{i}.test:\n    name: St{i}\n    base_url: https://st{i}.test\n    lang: fr\n    country: ES\n"
        f"    listing: {{urls: ['/x'], product: 'li', link: 'a'}}\n    crawl_every_days: {n}\n" for i, n in enumerate(every))
    return parse_store_configs(yaml)


@pytest.mark.parametrize("crawls, has_products, status", [
    ([], False, "never"),
    ([], True, "manual"),
    ([("ok", 3 * DAY)], True, "ok"),
    ([("ok", 13 * DAY)], True, "ok"),                                            # within 2 x 7 days
    ([("ok", 15 * DAY)], True, "late"),
    ([("ok", 10 * DAY), ("incomplete", DAY)], True, "incomplete"),
    ([("ok", 10 * DAY), ("failed", DAY)], True, "failed"),
    ([("ok", DAY), ("failed", 5 * DAY)], True, "ok"),                            # an older failure does not matter
    ([("ok", 20 * DAY), ("failed", DAY)], True, "failed"),                       # late AND failing: the newest news first
    ([("failed", DAY)], False, "failed"),
])
def test_store_status(s, crawls, has_products, status):
    (cfg,) = cfgs(7).values()
    src = Source(name=cfg.name, kind="store", url=str(cfg.base_url), lang="fr", country="ES")
    s.add(src)
    s.flush()
    for st, ago in crawls:
        add_crawl(s, src, st, NOW - ago, **({"problems": ["/x page 2: not fetched"]} if st == "incomplete" else
                                              {"error": "ConnectionError: blocked"} if st == "failed" else {}))
    if has_products:
        add_product(s, src, "a", first_seen=NOW - 60 * DAY)
    s.commit()
    (row,) = catalog.store_status(s, {cfg.domain: cfg}, NOW)
    assert row["status"] == status and row["status_label"] == catalog.STATUS_LABELS_FR[status]
    assert row["detail"] == {"incomplete": "/x page 2: not fetched", "failed": "ConnectionError: blocked"}.get(status)


def test_store_status_uses_each_stores_cadence_and_reports_its_counts(s):
    daily, weekly = cfgs(1, 7).values()
    for cfg in (daily, weekly):
        src = Source(name=cfg.name, kind="store", url=str(cfg.base_url), lang="fr", country="ES")
        s.add(src)
        s.flush()
        add_crawl(s, src, "ok", NOW - 3 * DAY)
        add_product(s, src, "old", first_seen=NOW - 30 * DAY)
        add_product(s, src, "new", first_seen=NOW - DAY)                         # after its baseline (3 days ago)
        add_product(s, src, "gone", first_seen=NOW - 30 * DAY, active=False, dropped=NOW - DAY)
    s.commit()
    rows = {r["name"]: r for r in catalog.store_status(s, {c.domain: c for c in (daily, weekly)}, NOW)}
    assert (rows["St0"]["status"], rows["St1"]["status"]) == ("late", "ok")       # 3 days is past 2 x 1 day
    assert (rows["St1"]["products"], rows["St1"]["new"], rows["St1"]["retired"], rows["St1"]["has_history"]) == (2, 1, 1, True)
    assert rows["St1"]["last_ok_at"] == (NOW - 3 * DAY).isoformat() and rows["St1"]["creator"] is True


def test_a_shrink_guard_note_is_carried_on_an_ok_store(s):
    (cfg,) = cfgs(7).values()
    src = Source(name=cfg.name, kind="store", url=str(cfg.base_url), lang="fr", country="ES")
    s.add(src)
    s.flush()
    add_crawl(s, src, "ok", NOW - DAY, drop_skipped="listing shrank 684 -> 120")
    s.commit()
    (row,) = catalog.store_status(s, {cfg.domain: cfg}, NOW)
    assert row["status"] == "ok" and row["note"] == "listing shrank 684 -> 120"


# --- the brief --------------------------------------------------------------------------------------

def test_the_brief_section_lists_counts_and_attribute_shares_for_creator_brands(s):
    seed_creator(s, n_new=10)
    lines = catalog.catalog_brief(s, NOW)
    text = "\n".join(lines)
    assert "Etnia : 10 nouveauté(s), 1 retirée(s)" in text and "indicateur avancé" in text
    assert "Couleur | Bleu | 10 | 100 % | 50 %" in text
    assert "Forme de monture | Ronde / Panto | 8 | 80 % | 40 %" in text and "Forme de monture | Carrée | 2 | 20 % | 60 %" in text


def test_the_brief_says_not_to_conclude_below_the_volume_floor(s):
    seed_creator(s, n_new=4)
    text = "\n".join(catalog.catalog_brief(s, NOW))
    assert "Trop peu de nouveautés (4)" in text and "|" not in text.split("Trop peu")[1]
