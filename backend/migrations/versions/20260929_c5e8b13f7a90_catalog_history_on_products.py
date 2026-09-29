"""catalog history on products

first_seen_at (set once, at insert), is_active (in the store's latest complete crawl) and dropped_at (when a crawl
noticed the product gone). seen_at keeps its column and is read as last_seen_at. Nothing reads the new columns yet;
the sync rules that maintain them come next, so this migration changes no behaviour.

Revision ID: c5e8b13f7a90
Revises: a41c7d9e2b56
Create Date: 2026-09-29 18:00:00.000000
"""
from collections.abc import Sequence
from datetime import timedelta

import sqlalchemy as sa
from alembic import op


revision: str = 'c5e8b13f7a90'
down_revision: str | Sequence[str] | None = 'a41c7d9e2b56'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_DAYS = 14  # retail.ACTIVE_DAYS today, copied: a migration must not follow later changes to app code
INDEX = 'ix_products_source_id_is_active'
products = sa.table('products', sa.column('source_id', sa.Integer), sa.column('seen_at', sa.DateTime(timezone=True)),
                    sa.column('first_seen_at', sa.DateTime(timezone=True)), sa.column('is_active', sa.Boolean))


def upgrade() -> None:
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=True))  # NOT NULL after the backfill
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('dropped_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill 1: first_seen_at = seen_at. For a product that existed before this migration that is "no later than",
    # not a real arrival date (the plan defines "new" against each store's baseline, never on this value alone).
    op.execute(products.update().values(first_seen_at=products.c.seen_at))
    # Backfill 2: is_active by the rule retail.active_products applies today: seen within ACTIVE_DAYS of the store's
    # latest sighting. Python side: SQLite date arithmetic on stored strings is fragile. dropped_at stays NULL:
    # the date of an old drop is unknown.
    newest = op.get_bind().execute(
        sa.select(products.c.source_id, sa.func.max(products.c.seen_at)).group_by(products.c.source_id)).all()
    for source_id, latest in newest:
        op.execute(products.update().where(products.c.source_id == source_id,
                                           products.c.seen_at < latest - timedelta(days=ACTIVE_DAYS))
                   .values(is_active=False))

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.alter_column('first_seen_at', existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.create_index(INDEX, ['source_id', 'is_active'])


def downgrade() -> None:
    # Restores the previous schema exactly; the three columns' data is lost. seen_at is never advanced for a dropped
    # product, so the old 14-day reader rebuilds nearly the same shelf (a product dropped in the last 14 days reads
    # as active again until the next crawl ages it out).
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_index(INDEX)
        batch_op.drop_column('dropped_at')
        batch_op.drop_column('is_active')
        batch_op.drop_column('first_seen_at')
