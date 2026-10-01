"""support_decimal_quantity_and_total_quantity

Revision ID: e1f2a3b4c5d6
Revises: c7a21f839d01
Create Date: 2026-10-01 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'c7a21f839d01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('breakfast_order_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('breakfast_daily_entries') as batch_op:
        batch_op.add_column(sa.Column('total_quantity', sa.Float(), nullable=True, server_default='0'))

    with op.batch_alter_table('breakfast_additional_orders') as batch_op:
        batch_op.add_column(sa.Column('total_quantity', sa.Float(), nullable=True, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('breakfast_additional_orders') as batch_op:
        batch_op.drop_column('total_quantity')

    with op.batch_alter_table('breakfast_daily_entries') as batch_op:
        batch_op.drop_column('total_quantity')

    with op.batch_alter_table('breakfast_order_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)
