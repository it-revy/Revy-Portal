"""lead_nurturing_workflow_tables

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-10-30 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'p3q4r5s6t7u8'
down_revision = 'o2p3q4r5s6t7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    # 1. crm_lead_nurturing table
    if 'crm_lead_nurturing' not in existing_tables:
        op.create_table(
            'crm_lead_nurturing',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('nurturing_id', sa.String(length=50), nullable=False, unique=True),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
            sa.Column('assigned_to_user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('current_stage', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('nurturing_status', sa.String(length=50), nullable=False, server_default='Active'),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('next_activity_date', sa.Date(), nullable=True),
            sa.Column('next_activity_id', sa.String(length=36), nullable=True),
            sa.Column('last_activity_at', sa.DateTime(), nullable=True),
            sa.Column('paused_at', sa.DateTime(), nullable=True),
            sa.Column('pause_reason', sa.Text(), nullable=True),
            sa.Column('stopped_at', sa.DateTime(), nullable=True),
            sa.Column('stop_reason', sa.Text(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('restart_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('review_outcome', sa.String(length=50), nullable=True),
            sa.Column('review_notes', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_crm_lead_nurturing_lead_id', 'crm_lead_nurturing', ['lead_id'])
        op.create_index('ix_crm_lead_nurturing_nurturing_id', 'crm_lead_nurturing', ['nurturing_id'])

    # 2. crm_nurturing_activities table
    if 'crm_nurturing_activities' not in existing_tables:
        op.create_table(
            'crm_nurturing_activities',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('activity_id', sa.String(length=50), nullable=False, unique=True),
            sa.Column('nurturing_id', sa.String(length=36), sa.ForeignKey('crm_lead_nurturing.id', ondelete='CASCADE'), nullable=False),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
            sa.Column('stage_number', sa.Integer(), nullable=False),
            sa.Column('activity_type', sa.String(length=50), nullable=False),
            sa.Column('subject', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('scheduled_at', sa.DateTime(), nullable=False),
            sa.Column('due_date', sa.Date(), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('activity_status', sa.String(length=50), nullable=False, server_default='Pending'),
            sa.Column('outcome', sa.String(length=100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('recipient', sa.String(length=255), nullable=True),
            sa.Column('email_message_reference', sa.String(length=255), nullable=True),
            sa.Column('skip_reason', sa.Text(), nullable=True),
            sa.Column('reschedule_reason', sa.Text(), nullable=True),
            sa.Column('callback_requested', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('callback_date', sa.Date(), nullable=True),
            sa.Column('meeting_datetime', sa.DateTime(), nullable=True),
            sa.Column('customer_response_date', sa.DateTime(), nullable=True),
            sa.Column('customer_response_channel', sa.String(length=50), nullable=True),
            sa.Column('customer_response_notes', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('completed_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_crm_nurturing_activities_lead_id', 'crm_nurturing_activities', ['lead_id'])
        op.create_index('ix_crm_nurturing_activities_nurturing_id', 'crm_nurturing_activities', ['nurturing_id'])
        op.create_index('ix_crm_nurturing_activities_due_date', 'crm_nurturing_activities', ['due_date'])
        op.create_index('ix_crm_nurturing_activities_activity_status', 'crm_nurturing_activities', ['activity_status'])


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    if 'crm_nurturing_activities' in existing_tables:
        op.drop_table('crm_nurturing_activities')
    if 'crm_lead_nurturing' in existing_tables:
        op.drop_table('crm_lead_nurturing')

