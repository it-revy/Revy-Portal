"""Add BMS Beverage Catalogue and Consumption Entries Tables

Revision ID: y2z3a4b5c6d7
Revises: x1y2z3a4b5c6
Create Date: 2026-11-14 14:30:00.000000

"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = 'y2z3a4b5c6d7'
down_revision: Union[str, None] = 'x1y2z3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create bms_beverages table
    op.create_table(
        'bms_beverages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(length=20), server_default='Cups', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bms_beverages_name'), 'bms_beverages', ['name'], unique=True)

    # 2. Create bms_beverage_entries table
    op.create_table(
        'bms_beverage_entries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('employee_id', sa.String(length=50), nullable=False),
        sa.Column('employee_name_snapshot', sa.String(length=150), nullable=False),
        sa.Column('beverage_id', sa.String(length=36), nullable=False),
        sa.Column('beverage_name_snapshot', sa.String(length=100), nullable=False),
        sa.Column('business_date', sa.String(length=10), nullable=False),
        sa.Column('session', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit', sa.String(length=20), server_default='Cups', nullable=False),
        sa.Column('source', sa.String(length=30), server_default='EMPLOYEE', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.String(length=150), nullable=True),
        sa.Column('deletion_reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=150), nullable=True),
        sa.Column('updated_by', sa.String(length=150), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['beverage_id'], ['bms_beverages.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'business_date', 'session', name='uq_bms_beverage_entries_emp_date_session')
    )
    op.create_index(op.f('ix_bms_beverage_entries_employee_id'), 'bms_beverage_entries', ['employee_id'], unique=False)
    op.create_index(op.f('ix_bms_beverage_entries_beverage_id'), 'bms_beverage_entries', ['beverage_id'], unique=False)
    op.create_index(op.f('ix_bms_beverage_entries_business_date'), 'bms_beverage_entries', ['business_date'], unique=False)
    op.create_index(op.f('ix_bms_beverage_entries_session'), 'bms_beverage_entries', ['session'], unique=False)
    op.create_index(op.f('ix_bms_beverage_entries_is_deleted'), 'bms_beverage_entries', ['is_deleted'], unique=False)
    op.create_index('ix_bms_beverage_entries_emp_date', 'bms_beverage_entries', ['employee_id', 'business_date'], unique=False)
    op.create_index('ix_bms_beverage_entries_date_session', 'bms_beverage_entries', ['business_date', 'session'], unique=False)

    # 3. Seed initial beverages: Tea, Green Tea, Coffee
    beverages_table = table(
        'bms_beverages',
        column('id', sa.String),
        column('name', sa.String),
        column('description', sa.Text),
        column('unit', sa.String),
        column('display_order', sa.Integer),
        column('is_active', sa.Boolean),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )

    now = datetime.now(timezone.utc)
    op.bulk_insert(
        beverages_table,
        [
            {
                'id': str(uuid.uuid4()),
                'name': 'Tea',
                'description': 'Traditional hot brewed tea',
                'unit': 'Cups',
                'display_order': 1,
                'is_active': True,
                'created_at': now,
                'updated_at': now
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Green Tea',
                'description': 'Refreshing herbal green tea',
                'unit': 'Cups',
                'display_order': 2,
                'is_active': True,
                'created_at': now,
                'updated_at': now
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Coffee',
                'description': 'Hot freshly brewed coffee',
                'unit': 'Cups',
                'display_order': 3,
                'is_active': True,
                'created_at': now,
                'updated_at': now
            }
        ]
    )


def downgrade() -> None:
    op.drop_table('bms_beverage_entries')
    op.drop_table('bms_beverages')
