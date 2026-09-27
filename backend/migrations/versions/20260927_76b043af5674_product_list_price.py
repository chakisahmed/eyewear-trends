"""product list price

Revision ID: 76b043af5674
Revises: 63ff6c1c91eb
Create Date: 2026-09-27 23:38:58.349230
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '76b043af5674'
down_revision: str | Sequence[str] | None = '63ff6c1c91eb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('list_price', sa.Float(), nullable=True))



def downgrade() -> None:
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('list_price')

