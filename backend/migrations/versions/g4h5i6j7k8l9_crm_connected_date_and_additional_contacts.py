"""crm connected date and additional contacts association table

Revision ID: g4h5i6j7k8l9
Revises: f3a4b5c6d7e8
Create Date: 2026-10-22 14:30:00.000000

"""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'g4h5i6j7k8l9'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    # 1. Add connected_date column to leads table if it doesn't already exist
    leads_columns = [col['name'] for col in inspector.get_columns('leads')]
    if 'connected_date' not in leads_columns:
        if is_sqlite:
            with op.batch_alter_table('leads') as batch_op:
                batch_op.add_column(sa.Column('connected_date', sa.Date(), nullable=True))
                batch_op.create_index('ix_leads_connected_date', ['connected_date'], unique=False)
        else:
            op.add_column('leads', sa.Column('connected_date', sa.Date(), nullable=True))
            op.create_index('ix_leads_connected_date', 'leads', ['connected_date'], unique=False)

    # 2. Create lead_additional_contacts association table if it doesn't already exist
    existing_tables = inspector.get_table_names()
    if 'lead_additional_contacts' not in existing_tables:
        op.create_table(
            'lead_additional_contacts',
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='CASCADE'), primary_key=True, nullable=False),
            sa.Column('contact_id', sa.String(length=36), sa.ForeignKey('contacts.id', ondelete='CASCADE'), primary_key=True, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
        )
        op.create_index('ix_lead_additional_contacts_lead_id', 'lead_additional_contacts', ['lead_id'], unique=False)
        op.create_index('ix_lead_additional_contacts_contact_id', 'lead_additional_contacts', ['contact_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_tables = inspector.get_table_names()
    if 'lead_additional_contacts' in existing_tables:
        op.drop_table('lead_additional_contacts')

    leads_columns = [col['name'] for col in inspector.get_columns('leads')]
    if 'connected_date' in leads_columns:
        if is_sqlite:
            with op.batch_alter_table('leads') as batch_op:
                batch_op.drop_index('ix_leads_connected_date')
                batch_op.drop_column('connected_date')
        else:
            op.drop_index('ix_leads_connected_date', table_name='leads')
            op.drop_column('leads', 'connected_date')
