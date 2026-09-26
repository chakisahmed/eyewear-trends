"""job run progress

Revision ID: 0f8b701a5f57
Revises: 3285676d58ba
Create Date: 2026-09-26 22:39:34.246547
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0f8b701a5f57'
down_revision: str | Sequence[str] | None = '3285676d58ba'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('job_runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_step', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('step_done', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('step_total', sa.Integer(), nullable=True))



def downgrade() -> None:
    with op.batch_alter_table('job_runs', schema=None) as batch_op:
        batch_op.drop_column('step_total')
        batch_op.drop_column('step_done')
        batch_op.drop_column('current_step')

