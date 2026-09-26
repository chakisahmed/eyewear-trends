from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, MetaData, create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import BACKEND_DIR, settings

# Deterministic constraint names: migrations can then drop/alter constraints by name,
# including on SQLite (batch mode) where unnamed constraints cannot be targeted.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


if settings.database_url.startswith("sqlite:///"):
    Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class SchemaMismatch(RuntimeError):
    pass


def alembic_config():
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return cfg


def schema_diff(connection) -> list:
    """Differences between the models and the live database (empty list = in sync)."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app import models  # noqa: F401  (register tables)

    ctx = MigrationContext.configure(connection, opts={"compare_type": True})
    return compare_metadata(ctx, Base.metadata)


def init_db(bind: Engine | None = None) -> None:
    """Bring the database (default: the app's) to the latest migration.

    A database created before Alembic (no alembic_version table) is adopted only if its
    schema already matches the models exactly; otherwise we refuse rather than guess.
    """
    from alembic import command

    cfg = alembic_config()
    with (bind or engine).begin() as conn:
        tables = set(inspect(conn).get_table_names())
        cfg.attributes["connection"] = conn
        if tables and "alembic_version" not in tables:
            diff = schema_diff(conn)
            if diff:
                raise SchemaMismatch(
                    "This database predates migrations and does not match the current models:\n"
                    + "\n".join(f"  {d}" for d in diff[:20])
                    + "\nBack it up and recreate it, or migrate it by hand, then run `alembic stamp head`."
                )
            command.stamp(cfg, "head")
        else:
            command.upgrade(cfg, "head")


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
