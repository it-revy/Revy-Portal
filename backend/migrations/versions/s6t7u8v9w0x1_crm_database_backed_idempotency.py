"""crm_database_backed_idempotency

Revision ID: s6t7u8v9w0x1
Revises: r5s6t7u8v9w0
Create Date: 2026-11-04 13:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 's6t7u8v9w0x1'
down_revision = 'r5s6t7u8v9w0'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'crm_idempotency_records' not in tables:
        op.create_table(
            'crm_idempotency_records',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('client_request_id', sa.String(length=100), nullable=False),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True),
            sa.Column('status', sa.String(length=20), server_default='PROCESSING', nullable=False),
            sa.Column('response_code', sa.Integer(), server_default='201', nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'client_request_id', name='uq_crm_idempotency_user_request')
        )
        op.create_index('ix_crm_idempotency_user_id', 'crm_idempotency_records', ['user_id'])
        op.create_index('ix_crm_idempotency_client_req_id', 'crm_idempotency_records', ['client_request_id'])
        op.create_index('ix_crm_idempotency_lead_id', 'crm_idempotency_records', ['lead_id'])
        op.create_index('ix_crm_idempotency_user_req', 'crm_idempotency_records', ['user_id', 'client_request_id'])


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'crm_idempotency_records' in tables:
        op.drop_index('ix_crm_idempotency_user_req', table_name='crm_idempotency_records')
        op.drop_index('ix_crm_idempotency_lead_id', table_name='crm_idempotency_records')
        op.drop_index('ix_crm_idempotency_client_req_id', table_name='crm_idempotency_records')
        op.drop_index('ix_crm_idempotency_user_id', table_name='crm_idempotency_records')
        op.drop_table('crm_idempotency_records')

