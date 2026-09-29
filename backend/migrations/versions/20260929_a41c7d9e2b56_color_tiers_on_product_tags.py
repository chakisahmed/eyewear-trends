"""color tiers on product tags

Palier 1 (color_family), Palier 2 (color_hex) and Palier 3 (supplier_code) on product_tags, all nullable, and a
uniqueness rule that admits several variant codes of one color family on one product.

Revision ID: a41c7d9e2b56
Revises: 76b043af5674
Create Date: 2026-09-29 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a41c7d9e2b56'
down_revision: str | Sequence[str] | None = '76b043af5674'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_UQ = 'uq_product_tags_product_id_dimension_code'
NEW_UQ = 'uq_product_tags_product_id_dimension_code_supplier_code'
UNCODED = 'uq_product_tags_uncoded'


def upgrade() -> None:
    # Existing rows keep every value; the new columns are NULL until `retag-products` fills them (no reader needs them yet).
    with op.batch_alter_table('product_tags', schema=None) as batch_op:
        batch_op.add_column(sa.Column('color_family', sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column('color_hex', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('supplier_code', sa.String(length=60), nullable=True))
        batch_op.drop_constraint(OLD_UQ, type_='unique')
        batch_op.create_unique_constraint(NEW_UQ, ['product_id', 'dimension', 'code', 'supplier_code'])
        batch_op.create_index(UNCODED, ['product_id', 'dimension', 'code'], unique=True,
                              sqlite_where=sa.text('supplier_code IS NULL'),
                              postgresql_where=sa.text('supplier_code IS NULL'))


def downgrade() -> None:
    # The old rule allows one tag per (product, dimension, code): keep the oldest of any variant-coded duplicates.
    op.execute("DELETE FROM product_tags WHERE id NOT IN "
               "(SELECT MIN(id) FROM product_tags GROUP BY product_id, dimension, code)")
    with op.batch_alter_table('product_tags', schema=None) as batch_op:
        batch_op.drop_index(UNCODED, sqlite_where=sa.text('supplier_code IS NULL'),
                            postgresql_where=sa.text('supplier_code IS NULL'))
        batch_op.drop_constraint(NEW_UQ, type_='unique')
        batch_op.create_unique_constraint(OLD_UQ, ['product_id', 'dimension', 'code'])
        batch_op.drop_column('supplier_code')
        batch_op.drop_column('color_hex')
        batch_op.drop_column('color_family')
