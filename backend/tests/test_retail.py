"""Tunisian shelf data per attribute and Shelf vs. Signal gaps (deterministic, no LLM).

Uses its own in-memory database: shelf shares depend on every product present, so the shared test
database (other tests add products) would make the numbers unstable.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductTag, Source, TrendSnapshot
from app.scoring import retail
from app.scoring.summary import build_brief

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
WEEK = date(2026, 9, 21)


@pytest.fixture
def s():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def type_tag(kind: str) -> ProductTag:
    return ProductTag(dimension="product_type", code=kind, field="categories", term=kind, rules_version=4)


def add_store(s, name: str, n_products: dict[str, int], *, seen=NOW, stale: dict[str, int] | None = None, price=100.0,
              kind: str = "sun"):
    """n_products: shape code -> number of active products; stale: shape code -> products seen long ago."""
    src = Source(name=name, kind="store", url=f"https://{name.lower()}.test", lang="fr", country="TN")
    s.add(src)
    s.flush()
    i = 0
    for batch, when in ((n_products, seen), (stale or {}, seen - timedelta(days=60))):
        for code, n in batch.items():
            for _ in range(n):
                i += 1
                p = Product(source_id=src.id, url=f"{src.url}/p{i}", name=f"{name} {i}", price=price, currency="TND",
                            rank=i, seen_at=when)
                p.tags = [ProductTag(dimension="shape", code=code, field="spec:Forme", term=code, rules_version=2), type_tag(kind)]
                s.add(p)
    s.commit()


def snapshot(s, code: str, status: str, momentum: float, dimension: str = "shape"):
    s.add(TrendSnapshot(dimension=dimension, code=code, week=WEEK, mentions=10, momentum=momentum, status=status))
    s.commit()


def test_shelf_counts_active_products_per_attribute(s):
    add_store(s, "Alpha", {"square": 20, "aviator": 10}, stale={"round": 30}, price=200)
    add_store(s, "Beta", {"square": 5, "cat_eye": 1}, price=300)
    shelf = retail.shelf_by_attribute(s)
    assert [(st["name"], st["products"]) for st in shelf["stores"]] == [("Alpha", 30), ("Beta", 6)]  # stale excluded
    shapes = shelf["dimensions"]["shape"]
    assert shapes["tagged"] == 36
    assert shapes["items"]["square"]["sku"] == 25 and shapes["items"]["square"]["share"] == pytest.approx(25 / 36)
    assert shapes["items"]["square"]["avg_price"] == {"TND": 220.0}
    assert "round" not in shapes["items"]                                    # only stale products
    assert shelf["dimensions"]["color"]["tagged"] == 0


def test_gaps_find_opportunities_and_stock_risks(s):
    add_store(s, "Alpha", {"square": 30, "aviator": 8, "cat_eye": 1})      # 39 tagged shapes
    snapshot(s, "cat_eye", "en_hausse", 1.5)     # rising, 1/39 = 2.6 % of the shelf  -> opportunity
    snapshot(s, "oval", "au_pic", 0.4)           # peaking, absent from the shelf      -> opportunity
    snapshot(s, "aviator", "en_hausse", 2.0)     # rising but 8/39 = 20 % on the shelf -> no gap
    snapshot(s, "square", "en_baisse", -0.4)     # declining, 77 % of the shelf        -> stock risk
    snapshot(s, "round", "faible", 3.0)          # too little press data               -> never a gap
    gaps = retail.shelf_gaps(s, WEEK)
    assert [(g["code"], g["sku"]) for g in gaps["opportunities"]] == [("cat_eye", 1), ("oval", 0)]  # by momentum
    assert [g["code"] for g in gaps["risks"]] == ["square"]
    assert gaps["risks"][0]["share"] == pytest.approx(30 / 39) and gaps["skipped_dimensions"] == ["color", "material", "style"]


def test_gaps_skip_dimensions_with_too_few_tagged_products(s):
    add_store(s, "Alpha", {"square": 5})                                   # below MIN_TAGGED
    snapshot(s, "cat_eye", "en_hausse", 1.5)
    gaps = retail.shelf_gaps(s, WEEK)
    assert gaps["opportunities"] == [] and "shape" in gaps["skipped_dimensions"]


def test_summary_brief_includes_the_tunisian_shelf(s):
    add_store(s, "Alpha", {"square": 30, "cat_eye": 1})
    snapshot(s, "cat_eye", "en_hausse", 1.5)
    snapshot(s, "square", "en_baisse", -0.4)
    brief = build_brief(s, WEEK)
    assert "Marché tunisien" in brief and "Alpha (31 réf.)" in brief
    assert "Carrée | 30 | 97 %" in brief                                   # label | sku | share of the shape shelf
    assert "Opportunité" in brief and "Œil de chat" in brief and "Risque de stock" in brief


def test_summary_brief_without_store_data_has_no_shelf_section(s):
    snapshot(s, "cat_eye", "en_hausse", 1.5)
    assert "Marché tunisien" not in build_brief(s, WEEK)


def test_dimension_with_unrecognised_store_vocabulary_is_not_compared(s):
    """MyKenza's Style field says Sport / Classique / Tendance: only "Sport" maps, so 'Minimaliste absent
    from shelves' would be a vocabulary artefact, not a real gap."""
    src = Source(name="Kenza", kind="store", url="https://kenza.test", lang="fr", country="TN")
    s.add(src)
    s.flush()
    for i, style in enumerate(["Sport"] * 25 + ["Classique"] * 15 + ["Tendance"] * 10):
        p = Product(source_id=src.id, url=f"{src.url}/p{i}", name=f"P{i}", price=300, currency="TND", rank=i + 1,
                    seen_at=NOW, flags={"raw_specs": {"Style": style, "Forme": "Carrée"}})
        p.tags = [ProductTag(dimension="shape", code="square", field="spec:Forme", term="carree", rules_version=3), type_tag("sun")]
        if style == "Sport":
            p.tags.append(ProductTag(dimension="style", code="sporty", field="spec:Style", term="sport", rules_version=3))
        s.add(p)
    s.commit()
    shelf = retail.shelf_by_attribute(s)
    style = shelf["dimensions"]["style"]
    assert (style["tagged"], style["with_value"], style["unmapped"]) == (25, 50, 25)   # 50 % not understood
    assert not retail.comparable(style) and retail.comparable(shelf["dimensions"]["shape"])
    snapshot(s, "minimalist", "en_hausse", 1.2, dimension="style")
    gaps = retail.shelf_gaps(s, WEEK, shelf)
    assert gaps["opportunities"] == [] and "style" in gaps["skipped_dimensions"] and "shape" not in gaps["skipped_dimensions"]
    assert "vocabulaire des boutiques non reconnu pour 50 %" in build_brief(s, WEEK)


# --- discount signal (list_price) -------------------------------------------------------------------

def add_priced(s, store: str, rows: list[tuple[str, int, float, float | None]], kind: str = "sun"):
    """rows: (shape code, count, price, list_price or None)."""
    src = Source(name=store, kind="store", url=f"https://{store.lower()}.test", lang="fr", country="TN")
    s.add(src)
    s.flush()
    i = 0
    for code, n, price, list_price in rows:
        for _ in range(n):
            i += 1
            p = Product(source_id=src.id, url=f"{src.url}/p{i}", name=f"{store} {i}", price=price, list_price=list_price,
                        currency="TND", rank=i, seen_at=NOW)
            p.tags = [ProductTag(dimension="shape", code=code, field="spec:Forme", term=code, rules_version=3), type_tag(kind)]
            s.add(p)
    s.commit()


def test_markdown_is_relative_to_the_store_wide_promotion(s):
    # Promo runs a store-wide sale: square -30 %, round -60 % (clearance), aviator full price.
    add_priced(s, "Promo", [("square", 30, 70, 100), ("round", 4, 40, 100), ("aviator", 10, 100, None)])
    add_priced(s, "Plain", [("aviator", 10, 45, None), ("round", 3, 45, None)])  # publishes no list prices
    baseline = (30 * 0.3 + 4 * 0.6) / 44
    items = retail.shelf_by_attribute(s)["dimensions"]["shape"]["items"]
    rnd = items["round"]["markdown"]
    assert (rnd["compared"], rnd["discounted"]) == (4, 4)                  # Plain's 3 round frames are not compared
    assert rnd["share_discounted"] == 1.0 and rnd["avg_depth"] == pytest.approx(0.6)
    assert rnd["relative_depth"] == pytest.approx(0.6 - baseline, abs=1e-3)          # deeper than the store's usual sale
    assert items["square"]["markdown"]["relative_depth"] == pytest.approx(0.3 - baseline, abs=1e-3)  # ~ the store-wide sale
    avi = items["aviator"]["markdown"]
    assert (avi["compared"], avi["discounted"], avi["avg_depth"]) == (10, 0, None)
    assert avi["relative_depth"] == pytest.approx(-baseline, abs=1e-3)


def test_markdown_is_none_when_no_store_publishes_list_prices(s):
    add_store(s, "Alpha", {"square": 25})
    assert retail.shelf_by_attribute(s)["dimensions"]["shape"]["items"]["square"]["markdown"] is None


def test_deep_relative_markdown_makes_a_declining_trend_a_clearance_risk(s):
    add_priced(s, "Promo", [("square", 30, 70, 100), ("round", 4, 40, 100), ("aviator", 10, 100, None)])
    add_priced(s, "Plain", [("aviator", 10, 45, None)])
    snapshot(s, "round", "en_baisse", -0.4)    # 4/54 = 7 % of the shelf: below RISK_SHARE, but -60 % vs -26 % usual
    snapshot(s, "square", "en_baisse", -0.3)   # 56 % of the shelf, discounted like the rest of the store
    gaps = retail.shelf_gaps(s, WEEK)
    by_code = {g["code"]: g for g in gaps["risks"]}
    assert set(by_code) == {"round", "square"}
    assert by_code["round"]["clearance"] is True and by_code["square"]["clearance"] is False
    brief = build_brief(s, WEEK)
    assert "déstockage" in brief and "Ronde / Panto" in brief


# --- per product type (prescription vs sunglasses shelves) ------------------------------------------

def test_gaps_are_computed_within_each_product_type(s):
    add_store(s, "Soleil", {"square": 30, "cat_eye": 1}, kind="sun")
    add_store(s, "Vue", {"cat_eye": 25}, kind="optical")
    snapshot(s, "cat_eye", "en_hausse", 1.5)   # 1/31 of the sun shelf, 25/25 of the optical shelf
    snapshot(s, "square", "en_baisse", -0.4)   # 30/31 of the sun shelf, absent from the optical shelf
    gaps = retail.shelf_gaps_by_type(s, WEEK)
    assert [(g["code"], g["product_type"]) for g in gaps["opportunities"]] == [("cat_eye", "sun")]
    assert [(g["code"], g["product_type"]) for g in gaps["risks"]] == [("square", "sun")]
    assert gaps["types"] == {"optical": 25, "sun": 31}


def test_an_empty_product_type_is_skipped_not_full_of_opportunities(s):
    """No prescription shop crawled yet: every rising shape would look 'absent' from an empty shelf."""
    add_store(s, "Soleil", {"square": 30}, kind="sun")
    snapshot(s, "cat_eye", "en_hausse", 1.5)
    gaps = retail.shelf_gaps_by_type(s, WEEK)
    assert [(g["code"], g["product_type"]) for g in gaps["opportunities"]] == [("cat_eye", "sun")]
    assert "shape" in gaps["skipped_dimensions"]["optical"] and "shape" not in gaps["skipped_dimensions"]["sun"]


def test_store_baseline_stays_store_wide_across_product_types(s):
    """A store-wide sale covers both shelves: the baseline must not be recomputed per product type."""
    src = Source(name="Mix", kind="store", url="https://mix.test", lang="fr", country="TN")
    s.add(src)
    s.flush()
    for i, (code, kind, price) in enumerate([("square", "sun", 70.0)] * 20 + [("round", "optical", 40.0)] * 5):
        p = Product(source_id=src.id, url=f"{src.url}/p{i}", name=f"P{i}", price=price, list_price=100.0,
                    currency="TND", rank=i + 1, seen_at=NOW)
        p.tags = [ProductTag(dimension="shape", code=code, field="spec:Forme", term=code, rules_version=4), type_tag(kind)]
        s.add(p)
    s.commit()
    optical = retail.shelf_by_attribute(s, product_type="optical")["dimensions"]["shape"]["items"]["round"]["markdown"]
    assert optical["relative_depth"] == pytest.approx(0.6 - (20 * 0.3 + 5 * 0.6) / 25, abs=1e-3)  # vs the whole store


def test_summary_brief_has_one_shelf_per_product_type(s):
    add_store(s, "Soleil", {"square": 30, "cat_eye": 1}, kind="sun")
    snapshot(s, "cat_eye", "en_hausse", 1.5)
    brief = build_brief(s, WEEK)
    assert "Rayon solaire" in brief and "Rayon optique : couverture insuffisante" in brief
    assert "Opportunité (solaire) : Œil de chat" in brief


def test_sunglasses_only_attributes_are_never_prescription_opportunities(s):
    """Shield / wraparound frames and tinted lenses are sunglasses by nature: absent from optical shelves is normal."""
    add_store(s, "Soleil", {"square": 30}, kind="sun")
    add_store(s, "Vue", {"round": 30}, kind="optical")
    snapshot(s, "shield", "en_hausse", 3.6)
    gaps = retail.shelf_gaps_by_type(s, WEEK)
    assert [(g["code"], g["product_type"]) for g in gaps["opportunities"]] == [("shield", "sun")]
