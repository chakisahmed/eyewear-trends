"""store crawls

One row per store per crawl (crawl-store, crawl-stores): status, counts, why drops were skipped. Crawls run outside the
app (Windows Task Scheduler), so this is what the dashboard can read, and what `crawl-stores` uses to judge which
stores are due. A store with no row has simply never been crawled by the new command.

Revision ID: d7a3c94e1b28
Revises: c5e8b13f7a90
Create Date: 2026-09-29 20:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd7a3c94e1b28'
down_revision: str | Sequence[str] | None = 'c5e8b13f7a90'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX = 'ix_store_crawls_source_id_started_at'


def upgrade() -> None:
    op.create_table(
        'store_crawls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('trigger', sa.String(length=12), nullable=False),
        sa.Column('listed', sa.Integer(), nullable=True),
        sa.Column('crawled', sa.Integer(), nullable=True),
        sa.Column('inserted', sa.Integer(), nullable=True),
        sa.Column('updated', sa.Integer(), nullable=True),
        sa.Column('reactivated', sa.Integer(), nullable=True),
        sa.Column('dropped', sa.Integer(), nullable=True),
        sa.Column('drop_skipped', sa.String(length=300), nullable=True),
        sa.Column('problems', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(INDEX, 'store_crawls', ['source_id', 'started_at'])


def downgrade() -> None:
    # Only the crawl log is lost; products and their history are untouched.
    op.drop_index(INDEX, table_name='store_crawls')
    op.drop_table('store_crawls')
