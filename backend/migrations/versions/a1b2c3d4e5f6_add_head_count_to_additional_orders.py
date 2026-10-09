"""add_head_count_to_additional_orders

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-10-08 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    # 1. breakfast_additional_orders: add head_count and client_name
    add_order_cols = {c["name"] for c in insp.get_columns("breakfast_additional_orders")}
    with op.batch_alter_table("breakfast_additional_orders") as batch_op:
        if "head_count" not in add_order_cols:
            batch_op.add_column(sa.Column("head_count", sa.Integer(), nullable=True))
        if "client_name" not in add_order_cols:
            batch_op.add_column(sa.Column("client_name", sa.String(length=255), nullable=True))

    # 2. breakfast_orders: add head_count
    order_cols = {c["name"] for c in insp.get_columns("breakfast_orders")}
    with op.batch_alter_table("breakfast_orders") as batch_op:
        if "head_count" not in order_cols:
            batch_op.add_column(sa.Column("head_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("breakfast_additional_orders") as batch_op:
        batch_op.drop_column("client_name")
        batch_op.drop_column("head_count")

    with op.batch_alter_table("breakfast_orders") as batch_op:
        batch_op.drop_column("head_count")
