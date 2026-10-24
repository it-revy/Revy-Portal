"""add missing columns to crm_testing_charges

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-10-22 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'h5i6j7k8l9m0'
down_revision = 'g4h5i6j7k8l9'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_tables = inspector.get_table_names()
    if 'crm_testing_charges' in existing_tables:
        existing_cols = [c['name'] for c in inspector.get_columns('crm_testing_charges')]

        cols_to_add = [
            ('charge_type', sa.Column('charge_type', sa.String(length=50), nullable=False, server_default='TEST_CHARGE')),
            ('charge_description', sa.Column('charge_description', sa.String(length=255), nullable=True)),
            ('charge_amount', sa.Column('charge_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00')),
            ('agreed_unit_rate', sa.Column('agreed_unit_rate', sa.Numeric(precision=12, scale=2), nullable=True)),
            ('billable_units', sa.Column('billable_units', sa.Numeric(precision=10, scale=2), nullable=True, server_default='1.00')),
        ]

        if is_sqlite:
            with op.batch_alter_table('crm_testing_charges') as batch_op:
                for col_name, col_def in cols_to_add:
                    if col_name not in existing_cols:
                        batch_op.add_column(col_def)
        else:
            for col_name, col_def in cols_to_add:
                if col_name not in existing_cols:
                    op.add_column('crm_testing_charges', col_def)


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_tables = inspector.get_table_names()
    if 'crm_testing_charges' in existing_tables:
        existing_cols = [c['name'] for c in inspector.get_columns('crm_testing_charges')]
        cols_to_drop = ['charge_type', 'charge_description', 'charge_amount', 'agreed_unit_rate', 'billable_units']

        if is_sqlite:
            with op.batch_alter_table('crm_testing_charges') as batch_op:
                for col_name in cols_to_drop:
                    if col_name in existing_cols:
                        batch_op.drop_column(col_name)
        else:
            for col_name in cols_to_drop:
                if col_name in existing_cols:
                    op.drop_column('crm_testing_charges', col_name)
