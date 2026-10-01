"""add_historical_fields_to_daily_entry

Revision ID: c7a21f839d01
Revises: bdd18bae01e7
Create Date: 2026-09-29 15:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a21f839d01'
down_revision: Union[str, None] = 'bdd18bae01e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('breakfast_daily_entries') as batch_op:
        batch_op.add_column(sa.Column('record_type', sa.String(length=20), server_default='CURRENT', nullable=False))
        batch_op.add_column(sa.Column('paid_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('payment_type', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=50), server_default='OPERATIONAL', nullable=False))
        batch_op.add_column(sa.Column('source_id', sa.String(length=100), nullable=True))
        batch_op.create_index(op.f('ix_breakfast_daily_entries_record_type'), ['record_type'], unique=False)
        batch_op.create_index(op.f('ix_breakfast_daily_entries_source_id'), ['source_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('breakfast_daily_entries') as batch_op:
        batch_op.drop_index(op.f('ix_breakfast_daily_entries_source_id'))
        batch_op.drop_index(op.f('ix_breakfast_daily_entries_record_type'))
        batch_op.drop_column('source_id')
        batch_op.drop_column('source')
        batch_op.drop_column('payment_type')
        batch_op.drop_column('paid_by')
        batch_op.drop_column('record_type')
