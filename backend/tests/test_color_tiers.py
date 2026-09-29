"""Three-tier color schema: family (Palier 1) + hex (Palier 2) from the taxonomy, supplier / variant code
(Palier 3) from the crawler; persisted on product_tags without disturbing tags made before it existed."""

import re
import tempfile
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.service import StoreSyncService
from app.collectors.stores.tagger import tag_product
from app.db import SessionLocal, alembic_config, init_db, schema_diff
from app.models import Product, ProductTag
from app.taxonomy import load_taxonomy

from tests.test_store_crawlers import BASE, cfg  # noqa: F401  (cfg is a fixture)

PREVIOUS_REVISION = "76b043af5674"


@pytest.fixture
def temp_engine():
    eng = create_engine(f"sqlite:///{(Path(tempfile.mkdtemp()) / 'm.db').as_posix()}")
    yield eng
    eng.dispose()


# --- taxonomy -------------------------------------------------------------------------------------

def test_every_color_family_has_a_valid_palier_2_hex():
    tax = load_taxonomy()
    assert all(re.fullmatch(r"#[0-9a-f]{6}", it.hex) for it in tax.items["color"].values())


def test_color_tier_carries_family_hex_and_a_cleaned_supplier_code():
    tax = load_taxonomy()
    tier = tax.color_tier("tortoiseshell", "  HV/BL ")
    assert (tier.family, tier.hex, tier.supplier_code) == ("tortoiseshell", tax.get("color", "tortoiseshell").hex, "HV/BL")
    assert tax.color_tier("black").supplier_code is None
    assert tax.color_tier("black", "   ").supplier_code is None
    assert len(tax.color_tier("black", "X" * 200).supplier_code) == 60


def test_a_color_without_a_valid_hex_is_refused(tmp_path):
    bad = tmp_path / "t.yaml"
    bad.write_text("dimensions:\n  color:\n    label_fr: Couleur\n    items:\n      blue:\n        fr: Bleu\n"
                   "        hex: bleu\n        query: {fr: a, en: b}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="blue"):
        load_taxonomy(bad)


# --- tagger ---------------------------------------------------------------------------------------

def test_color_tags_carry_family_and_hex_from_the_taxonomy():
    tags = tag_product("Monture noire", {"raw_specs": {"Forme": "Ronde"}})
    black = next(t for t in tags if t.dimension == "color")
    assert (black.color_family, black.color_hex, black.supplier_code) == ("black", load_taxonomy().get("color", "black").hex, None)
    assert next(t for t in tags if t.dimension == "shape").color_hex is None  # tiers exist for colors only


def test_variant_code_rides_on_the_tag_its_color_label_matches():
    flags = {"variants": [{"code": "HV/BL", "color": "Havana"}, {"code": "BK", "color": "Black"}]}
    got = {(t.code, t.supplier_code, t.field) for t in tag_product("ETNIA X", flags) if t.dimension == "color"}
    assert got == {("tortoiseshell", "HV/BL", "variant"), ("black", "BK", "variant")}


def test_several_variant_codes_of_one_family_are_kept_apart():
    flags = {"variants": [{"code": "HV/BL", "color": "Havana"}, {"code": "HV/BR", "color": "Havana"}]}
    tags = [t for t in tag_product("ETNIA X", flags) if t.dimension == "color"]
    assert sorted(t.supplier_code for t in tags) == ["HV/BL", "HV/BR"]
    assert len({t.color_hex for t in tags}) == 1


def test_a_coded_tag_replaces_the_uncoded_tag_of_the_same_family_only():
    tags = tag_product("Monture noire havane", {"variants": [{"code": "HV/BL", "color": "Havana"}]})
    assert {(t.code, t.supplier_code) for t in tags if t.dimension == "color"} == {("black", None), ("tortoiseshell", "HV/BL")}


def test_an_unrecognised_variant_label_creates_no_tag_and_a_code_is_never_guessed():
    flags = {"variants": [{"code": "ZZ/99", "color": "Xyzzy"}, {"code": "HV"}, {"color": "Noir"}, "junk", None]}
    assert tag_product("ETNIA X", flags) == []
    assert tag_product("X", {"variants": "HV/BL"}) == []  # not a list: ignored


# --- persistence ----------------------------------------------------------------------------------

def test_variant_codes_persist_and_a_resync_updates_them_without_duplicates(cfg):  # noqa: F811
    init_db()
    url = f"{BASE}/p/etnia-like"
    colors = lambda s: sorted((t.code, t.supplier_code, t.color_family, bool(t.color_hex)) for t in s.scalar(
        select(Product).where(Product.url == url)).tags if t.dimension == "color")
    with SessionLocal() as s:
        service = StoreSyncService(s)
        source = service.source_for(cfg)
        variants = [{"code": "HV/BL", "color": "Havana"}, {"code": "HV/BR", "color": "Havana"}]
        service.sync(source.id, [ScrapedProduct(url=url, name="Monture", flags={"variants": variants})])
        assert colors(s) == [("tortoiseshell", "HV/BL", "tortoiseshell", True), ("tortoiseshell", "HV/BR", "tortoiseshell", True)]

        service.sync(source.id, [ScrapedProduct(url=url, name="Monture", flags={"variants": variants[:1]})])
        assert colors(s) == [("tortoiseshell", "HV/BL", "tortoiseshell", True)]  # the dropped variant is gone

        before = s.query(ProductTag).count()
        service.retag_all(source.id)
        assert s.query(ProductTag).count() == before


def test_a_plain_color_tag_gets_family_and_hex_and_no_supplier_code(cfg):  # noqa: F811
    init_db()
    url = f"{BASE}/p/plain-color"
    with SessionLocal() as s:
        service = StoreSyncService(s)
        source = service.source_for(cfg)
        service.sync(source.id, [ScrapedProduct(url=url, name="Monture", flags={"raw_specs": {"Couleur": "Noir"}})])
        tag = next(t for t in s.scalar(select(Product).where(Product.url == url)).tags if t.dimension == "color")
        assert (tag.color_family, tag.supplier_code) == ("black", None) and tag.color_hex.startswith("#")


def test_retag_backfills_family_and_hex_on_tags_made_before_the_upgrade(cfg):  # noqa: F811
    init_db()
    url = f"{BASE}/p/legacy"
    with SessionLocal() as s:
        service = StoreSyncService(s)
        source = service.source_for(cfg)
        service.sync(source.id, [ScrapedProduct(url=url, name="Monture", flags={"raw_specs": {"Couleur": "Noir"}})])
        for t in s.scalar(select(Product).where(Product.url == url)).tags:
            t.color_family = t.color_hex = None  # how a pre-v5 row looks
        s.commit()
        service.retag_all(source.id)
        tag = next(t for t in s.scalar(select(Product).where(Product.url == url)).tags if t.dimension == "color")
        assert (tag.color_family, tag.supplier_code) == ("black", None) and tag.color_hex


# --- migration a41c7d9e2b56 -----------------------------------------------------------------------

def test_upgrade_keeps_existing_product_tags_and_leaves_new_columns_null(temp_engine):
    cfg_ = alembic_config()
    with temp_engine.begin() as conn:
        cfg_.attributes["connection"] = conn
        command.upgrade(cfg_, PREVIOUS_REVISION)
        conn.execute(text("pragma foreign_keys=off"))
        conn.execute(text("insert into product_tags (product_id, dimension, code, field, term, rules_version) values "
                          "(1, 'color', 'black', 'name', 'noir', 4), (1, 'shape', 'round', 'name', 'ronde', 4), "
                          "(2, 'color', 'black', 'spec:Couleur', 'noir', 4)"))
        command.upgrade(cfg_, "head")
    with temp_engine.connect() as conn:
        rows = conn.execute(text("select product_id, dimension, code, field, term, rules_version, color_family, "
                                 "color_hex, supplier_code from product_tags order by id")).all()
        assert rows == [(1, "color", "black", "name", "noir", 4, None, None, None),
                        (1, "shape", "round", "name", "ronde", 4, None, None, None),
                        (2, "color", "black", "spec:Couleur", "noir", 4, None, None, None)]
        assert schema_diff(conn) == []


def test_after_upgrade_variant_codes_coexist_but_exact_duplicates_are_still_refused(temp_engine):
    init_db(temp_engine)
    ins = ("insert into product_tags (product_id, dimension, code, field, term, rules_version, supplier_code) "
           "values (1, 'color', 'tortoiseshell', 'variant', 'havana', 5, {})")
    with temp_engine.begin() as conn:
        conn.execute(text("pragma foreign_keys=off"))
        for supplier in ("'HV/BL'", "'HV/BR'", "NULL"):  # two variants of one family plus the uncoded tag: allowed
            conn.execute(text(ins.format(supplier)))
    for supplier in ("'HV/BL'", "NULL"):  # exact duplicates, coded or not: refused
        with pytest.raises(IntegrityError), temp_engine.begin() as conn:
            conn.execute(text("pragma foreign_keys=off"))
            conn.execute(text(ins.format(supplier)))


def test_downgrade_collapses_variant_duplicates_and_restores_the_old_rule(temp_engine):
    init_db(temp_engine)
    cfg_ = alembic_config()
    with temp_engine.begin() as conn:
        conn.execute(text("pragma foreign_keys=off"))
        conn.execute(text("insert into product_tags (product_id, dimension, code, field, term, rules_version, supplier_code) "
                          "values (1, 'color', 'tortoiseshell', 'variant', 'havana', 5, 'HV/BL'), "
                          "(1, 'color', 'tortoiseshell', 'variant', 'havana', 5, 'HV/BR')"))
        cfg_.attributes["connection"] = conn
        command.downgrade(cfg_, PREVIOUS_REVISION)
    with temp_engine.connect() as conn:
        assert conn.execute(text("select count(*) from product_tags")).scalar() == 1
        assert "supplier_code" not in {c["name"] for c in inspect(conn).get_columns("product_tags")}
