"""Alembic environment: models from app.models, database URL from app settings."""

from alembic import context

from app import models  # noqa: F401  (register tables on Base.metadata)
from app.db import Base, engine

config = context.config
target_metadata = Base.metadata


def configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True,  # SQLite cannot ALTER most things; batch mode rebuilds the table
        **kwargs,
    )


def run_offline() -> None:
    """`alembic upgrade head --sql`: emit SQL for review instead of executing it."""
    configure(url=str(engine.url), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    # init_db() hands us its open connection; the alembic CLI does not, so connect ourselves.
    connection = config.attributes.get("connection")
    if connection is not None:
        configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
        return
    with engine.connect() as conn:
        configure(connection=conn)
        with context.begin_transaction():
            context.run_migrations()
        conn.commit()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
