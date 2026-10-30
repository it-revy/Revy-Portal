"""phase5a_opportunity_lifecycle_and_quotations

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-10-27 12:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'n1o2p3q4r5s6'
down_revision = 'm0n1o2p3q4r5'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'crm_opportunity_quotations' not in existing_tables:
        op.create_table(
            'crm_opportunity_quotations',
            sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
            sa.Column('quotation_number', sa.String(length=50), nullable=False),
            sa.Column('opportunity_id', sa.String(length=36), nullable=False),
            sa.Column('revision_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('version', sa.String(length=10), nullable=False, server_default='v1'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('title', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Draft'),
            sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.0'),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
            sa.Column('quotation_date', sa.Date(), nullable=False, server_default=sa.func.current_date()),
            sa.Column('valid_until_date', sa.Date(), nullable=True),
            sa.Column('terms_and_conditions', sa.Text(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('file_id', sa.String(length=100), nullable=True),
            sa.Column('document_name', sa.String(length=255), nullable=True),
            sa.Column('approved_by_id', sa.String(length=36), nullable=True),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('sent_method', sa.String(length=50), nullable=True),
            sa.Column('sent_to', sa.String(length=255), nullable=True),
            sa.Column('sent_at', sa.DateTime(), nullable=True),
            sa.Column('sent_by_id', sa.String(length=36), nullable=True),
            sa.Column('sending_evidence', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.String(length=36), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['opportunity_id'], ['crm_opportunities.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['sent_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.UniqueConstraint('quotation_number', 'revision_number', name='uq_crm_opportunity_quotations_num_rev')
        )

        op.create_index('ix_crm_opportunity_quotations_quotation_number', 'crm_opportunity_quotations', ['quotation_number'])
        op.create_index('ix_crm_opportunity_quotations_opportunity_id', 'crm_opportunity_quotations', ['opportunity_id'])
        op.create_index('ix_crm_opportunity_quotations_is_active', 'crm_opportunity_quotations', ['is_active'])
        op.create_index('ix_crm_opportunity_quotations_status', 'crm_opportunity_quotations', ['status'])
        op.create_index('ix_crm_opportunity_quotations_file_id', 'crm_opportunity_quotations', ['file_id'])
        op.create_index('ix_crm_opportunity_quotations_created_at', 'crm_opportunity_quotations', ['created_at'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'crm_opportunity_quotations' in existing_tables:
        op.drop_table('crm_opportunity_quotations')
