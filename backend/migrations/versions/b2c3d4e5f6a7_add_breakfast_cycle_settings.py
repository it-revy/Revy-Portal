"""add_breakfast_cycle_settings

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-09 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    cols = {c["name"] for c in insp.get_columns("breakfast_settings")}
    with op.batch_alter_table("breakfast_settings") as batch_op:
        if "request_open_time" not in cols:
            batch_op.add_column(sa.Column("request_open_time", sa.String(length=10), server_default="17:30", nullable=False))
        if "request_close_time" not in cols:
            batch_op.add_column(sa.Column("request_close_time", sa.String(length=10), server_default="08:20", nullable=False))

    # Update any existing rows to ensure non-null defaults
    op.execute("UPDATE breakfast_settings SET request_open_time = '17:30' WHERE request_open_time IS NULL")
    op.execute("UPDATE breakfast_settings SET request_close_time = '08:20' WHERE request_close_time IS NULL")
    op.execute("UPDATE breakfast_settings SET cutoff_time = '08:20' WHERE cutoff_time = '12:00' OR cutoff_time = '18:00'")


def downgrade() -> None:
    with op.batch_alter_table("breakfast_settings") as batch_op:
        batch_op.drop_column("request_close_time")
        batch_op.drop_column("request_open_time")
