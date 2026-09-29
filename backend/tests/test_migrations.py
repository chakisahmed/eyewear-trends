"""Migrations must build exactly the schema the models describe, on a fresh or a pre-Alembic database."""

import tempfile
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text

from app import models  # noqa: F401
from app.db import Base, SchemaMismatch, alembic_config, init_db, schema_diff


@pytest.fixture
def temp_engine():
    eng = create_engine(f"sqlite:///{(Path(tempfile.mkdtemp()) / 'm.db').as_posix()}")
    yield eng
    eng.dispose()


def test_migrations_match_models(temp_engine):
    """Fails when a model changed without a migration: run `alembic revision --autogenerate`."""
    init_db(temp_engine)
    with temp_engine.connect() as conn:
        assert schema_diff(conn) == []
        assert conn.execute(text("select count(*) from alembic_version")).scalar() == 1


def test_downgrade_to_base_and_back(temp_engine):
    init_db(temp_engine)
    cfg = alembic_config()
    with temp_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
    assert set(inspect(temp_engine).get_table_names()) == {"alembic_version"}
    init_db(temp_engine)
    with temp_engine.connect() as conn:
        assert schema_diff(conn) == []


def test_pre_alembic_database_matching_models_is_adopted(temp_engine):
    Base.metadata.create_all(temp_engine)  # how databases were created before migrations
    init_db(temp_engine)
    tables = set(inspect(temp_engine).get_table_names())
    assert "alembic_version" in tables and "documents" in tables


def test_pre_alembic_database_with_old_schema_is_refused(temp_engine):
    Base.metadata.create_all(temp_engine)
    with temp_engine.begin() as conn:
        conn.execute(text("alter table trend_snapshots drop column tone"))
    with pytest.raises(SchemaMismatch, match="tone"):
        init_db(temp_engine)
    assert "alembic_version" not in inspect(temp_engine).get_table_names()


# --- catalog history on products (c5e8b13f7a90) ----------------------------------------------------

BEFORE = "a41c7d9e2b56"
STAMP = "2026-09-29 12:00:00.000000"


def days_ago(n: int) -> str:
    return f"2026-09-{29 - n:02d} 12:00:00.000000"


def seed_before_history(conn) -> None:
    """Two stores as the previous schema stored them: A seen now / 10 / 20 days before its latest sighting, B alone."""
    for sid, name in ((1, "A"), (2, "B")):
        conn.execute(text("insert into sources (id, name, kind, url, lang, active) values (:i, :n, 'store', :u, 'fr', 1)"),
                     {"i": sid, "n": name, "u": f"https://{name.lower()}.test"})
    products = [(1, 1, "a-new", STAMP), (2, 1, "a-10d", days_ago(10)), (3, 1, "a-20d", days_ago(20)),
                (4, 2, "b-lone", days_ago(25))]  # alone in its store: newest by definition, so still active
    for pid, sid, slug, seen in products:
        conn.execute(text("insert into products (id, source_id, url, name, seen_at) values (:i, :s, :u, :n, :t)"),
                     {"i": pid, "s": sid, "u": f"https://x.test/{slug}", "n": slug.upper(), "t": seen})
        conn.execute(text("insert into product_tags (product_id, dimension, code, field, term, rules_version) "
                          "values (:i, 'color', 'blue', 'name', 'blue', 10)"), {"i": pid})


def test_catalog_history_backfill_keeps_rows_and_judges_activity_per_store(temp_engine):
    cfg = alembic_config()
    with temp_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, BEFORE)
        seed_before_history(conn)
        command.upgrade(cfg, "head")
        rows = conn.execute(text("select url, seen_at, first_seen_at, is_active, dropped_at from products order by id")).all()
        assert all(r.first_seen_at == r.seen_at for r in rows)                 # the only date we have: last sighting
        assert [bool(r.is_active) for r in rows] == [True, True, False, True]  # only a-20d is past the 14-day window
        assert all(r.dropped_at is None for r in rows)                          # the date of an old drop is unknown
        assert conn.execute(text("select count(*) from products")).scalar() == 4
        assert conn.execute(text("select count(*) from product_tags")).scalar() == 4  # the table rebuild cascades nothing
        assert schema_diff(conn) == []


def test_catalog_history_downgrade_drops_only_the_new_columns(temp_engine):
    cfg = alembic_config()
    with temp_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, BEFORE)
        seed_before_history(conn)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, BEFORE)
        columns = {c["name"] for c in inspect(conn).get_columns("products")}
        assert not columns & {"first_seen_at", "is_active", "dropped_at"} and "seen_at" in columns
        assert "ix_products_source_id_is_active" not in {i["name"] for i in inspect(conn).get_indexes("products")}
        assert conn.execute(text("select count(*) from products")).scalar() == 4
        assert conn.execute(text("select count(*) from product_tags")).scalar() == 4
        command.upgrade(cfg, "head")                                              # and it goes forward again
        assert schema_diff(conn) == []


def test_a_new_product_starts_active_and_first_seen_now(temp_engine):
    from sqlalchemy.orm import Session
    from app.models import Product, Source
    init_db(temp_engine)
    with Session(temp_engine) as s:
        src = Source(name="S", kind="store", url="https://s.test", lang="fr")
        s.add(src)
        s.flush()
        p = Product(source_id=src.id, url="https://s.test/p", name="P")
        s.add(p)
        s.commit()
        assert p.is_active is True and p.dropped_at is None and p.first_seen_at is not None


# --- store crawl log (d7a3c94e1b28) -----------------------------------------------------------------

def test_store_crawls_migration_adds_only_a_table_and_downgrades_cleanly(temp_engine):
    cfg = alembic_config()
    with temp_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "c5e8b13f7a90")
        conn.execute(text("insert into sources (id, name, kind, url, lang, active) values (1, 'A', 'store', 'https://a.test', 'fr', 1)"))
        for pid in range(1, 5):                                                 # products and tags as the previous revision stores them
            conn.execute(text("insert into products (id, source_id, url, name, seen_at, first_seen_at, is_active) "
                              "values (:i, 1, :u, 'P', :t, :t, 1)"), {"i": pid, "u": f"https://a.test/{pid}", "t": STAMP})
            conn.execute(text("insert into product_tags (product_id, dimension, code, field, term, rules_version) "
                              "values (:i, 'color', 'blue', 'name', 'blue', 10)"), {"i": pid})
        assert "store_crawls" not in inspect(conn).get_table_names()
        command.upgrade(cfg, "head")
        assert "store_crawls" in inspect(conn).get_table_names()
        assert conn.execute(text("select count(*) from products")).scalar() == 4
        assert conn.execute(text("select count(*) from store_crawls")).scalar() == 0   # nothing to backfill
        assert schema_diff(conn) == []
        conn.execute(text("insert into store_crawls (source_id, started_at, status, trigger) "
                          "values (1, '2026-09-29 20:00:00', 'running', 'batch')"))
        command.downgrade(cfg, "c5e8b13f7a90")
        assert "store_crawls" not in inspect(conn).get_table_names()
        assert conn.execute(text("select count(*) from products")).scalar() == 4       # the log goes, the catalog stays
        assert conn.execute(text("select count(*) from product_tags")).scalar() == 4
        command.upgrade(cfg, "head")
        assert schema_diff(conn) == []
