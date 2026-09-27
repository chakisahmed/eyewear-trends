"""product tags

Revision ID: 63ff6c1c91eb
Revises: 0f8b701a5f57
Create Date: 2026-09-27 17:13:40.935446
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '63ff6c1c91eb'
down_revision: str | Sequence[str] | None = '0f8b701a5f57'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('product_tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('dimension', sa.String(length=20), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('field', sa.String(length=40), nullable=False),
    sa.Column('term', sa.String(length=100), nullable=False),
    sa.Column('rules_version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_tags_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_tags')),
    sa.UniqueConstraint('product_id', 'dimension', 'code', name=op.f('uq_product_tags_product_id_dimension_code'))
    )
    with op.batch_alter_table('product_tags', schema=None) as batch_op:
        batch_op.create_index('ix_product_tags_dimension_code', ['dimension', 'code'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('product_tags', schema=None) as batch_op:
        batch_op.drop_index('ix_product_tags_dimension_code')

    op.drop_table('product_tags')
