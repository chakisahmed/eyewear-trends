"""initial schema

Revision ID: 3285676d58ba
Revises: 
Create Date: 2026-09-26 12:07:19.547864
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '3285676d58ba'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('job_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('trigger', sa.String(length=12), nullable=False),
    sa.Column('steps', sa.JSON(), nullable=False),
    sa.Column('report', sa.JSON(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_runs'))
    )
    op.create_table('search_interest',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dimension', sa.String(length=20), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('keyword', sa.String(length=200), nullable=False),
    sa.Column('lang', sa.String(length=5), nullable=False),
    sa.Column('geo', sa.String(length=5), nullable=False),
    sa.Column('week', sa.Date(), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_search_interest')),
    sa.UniqueConstraint('code', 'lang', 'geo', 'week', name=op.f('uq_search_interest_code_lang_geo_week'))
    )
    with op.batch_alter_table('search_interest', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_search_interest_code'), ['code'], unique=False)

    op.create_table('sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('url', sa.String(length=1000), nullable=False),
    sa.Column('lang', sa.String(length=5), nullable=False),
    sa.Column('country', sa.String(length=5), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sources')),
    sa.UniqueConstraint('url', name=op.f('uq_sources_url'))
    )
    op.create_table('trend_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dimension', sa.String(length=20), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('week', sa.Date(), nullable=False),
    sa.Column('mentions', sa.Float(), nullable=False),
    sa.Column('search', sa.Float(), nullable=True),
    sa.Column('momentum', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('tone', sa.Float(), nullable=True),
    sa.Column('decline_share', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trend_snapshots')),
    sa.UniqueConstraint('dimension', 'code', 'week', name=op.f('uq_trend_snapshots_dimension_code_week'))
    )
    with op.batch_alter_table('trend_snapshots', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_trend_snapshots_week'), ['week'], unique=False)

    op.create_table('weekly_summaries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('week', sa.Date(), nullable=False),
    sa.Column('text_fr', sa.Text(), nullable=False),
    sa.Column('model', sa.String(length=60), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_weekly_summaries')),
    sa.UniqueConstraint('week', name=op.f('uq_weekly_summaries_week'))
    )
    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=1000), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('lang', sa.String(length=5), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('summary_fr', sa.Text(), nullable=True),
    sa.Column('brands', sa.JSON(), nullable=True),
    sa.Column('prompt_version', sa.String(length=20), nullable=True),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], name=op.f('fk_documents_source_id_sources')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_documents')),
    sa.UniqueConstraint('url', name=op.f('uq_documents_url'))
    )
    op.create_table('products',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=1000), nullable=False),
    sa.Column('name', sa.String(length=300), nullable=False),
    sa.Column('brand', sa.String(length=100), nullable=True),
    sa.Column('price', sa.Float(), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('flags', sa.JSON(), nullable=True),
    sa.Column('image_url', sa.String(length=1000), nullable=True),
    sa.Column('seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], name=op.f('fk_products_source_id_sources')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
    sa.UniqueConstraint('url', name=op.f('uq_products_url'))
    )
    op.create_table('mentions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('dimension', sa.String(length=20), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('stance', sa.String(length=12), nullable=False),
    sa.Column('evidence', sa.Text(), nullable=False),
    sa.Column('occurred_on', sa.Date(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name=op.f('fk_mentions_document_id_documents')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mentions'))
    )
    with op.batch_alter_table('mentions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mentions_code'), ['code'], unique=False)
        batch_op.create_index(batch_op.f('ix_mentions_dimension'), ['dimension'], unique=False)
        batch_op.create_index(batch_op.f('ix_mentions_occurred_on'), ['occurred_on'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('mentions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_mentions_occurred_on'))
        batch_op.drop_index(batch_op.f('ix_mentions_dimension'))
        batch_op.drop_index(batch_op.f('ix_mentions_code'))

    op.drop_table('mentions')
    op.drop_table('products')
    op.drop_table('documents')
    op.drop_table('weekly_summaries')
    with op.batch_alter_table('trend_snapshots', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_trend_snapshots_week'))

    op.drop_table('trend_snapshots')
    op.drop_table('sources')
    with op.batch_alter_table('search_interest', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_search_interest_code'))

    op.drop_table('search_interest')
    op.drop_table('job_runs')
