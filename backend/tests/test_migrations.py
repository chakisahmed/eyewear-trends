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
