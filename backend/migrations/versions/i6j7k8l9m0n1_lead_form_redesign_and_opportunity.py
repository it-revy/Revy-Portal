"""lead form redesign direct fields, contact methods, and opportunity

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-10-23 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'i6j7k8l9m0n1'
down_revision = 'h5i6j7k8l9m0'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    # 1. Create crm_opportunities Table
    if 'crm_opportunities' not in existing_tables:
        op.create_table(
            'crm_opportunities',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('opportunity_id', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('contact_id', sa.String(length=36), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
            sa.Column('originating_lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Open'),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
            sa.Column('estimated_value', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('requirement_summary', sa.Text(), nullable=True),
            sa.Column('requirement_types', sa.Text(), nullable=True),
            sa.Column('assigned_to_user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_crm_opportunities_opportunity_id', 'crm_opportunities', ['opportunity_id'], unique=True)
        op.create_index('ix_crm_opportunities_name', 'crm_opportunities', ['name'], unique=False)
        op.create_index('ix_crm_opportunities_account_id', 'crm_opportunities', ['account_id'], unique=False)
        op.create_index('ix_crm_opportunities_contact_id', 'crm_opportunities', ['contact_id'], unique=False)
        op.create_index('ix_crm_opportunities_originating_lead_id', 'crm_opportunities', ['originating_lead_id'], unique=False)
        op.create_index('ix_crm_opportunities_status', 'crm_opportunities', ['status'], unique=False)
        op.create_index('ix_crm_opportunities_assigned_to_user_id', 'crm_opportunities', ['assigned_to_user_id'], unique=False)

    # 2. Create lead_contact_methods Table
    if 'lead_contact_methods' not in existing_tables:
        op.create_table(
            'lead_contact_methods',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
            sa.Column('contact_method', sa.String(length=50), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('lead_id', 'contact_method', name='uq_lead_contact_method')
        )
        op.create_index('ix_lead_contact_methods_lead_id', 'lead_contact_methods', ['lead_id'], unique=False)

    # 3. Add Columns to leads and Make contact_id Nullable
    if 'leads' in existing_tables:
        existing_cols = [c['name'] for c in inspector.get_columns('leads')]

        cols_to_add = [
            ('first_name', sa.Column('first_name', sa.String(length=100), nullable=True)),
            ('last_name', sa.Column('last_name', sa.String(length=100), nullable=True)),
            ('job_title', sa.Column('job_title', sa.String(length=100), nullable=True)),
            ('business_phone', sa.Column('business_phone', sa.String(length=50), nullable=True)),
            ('mobile_phone', sa.Column('mobile_phone', sa.String(length=50), nullable=True)),
            ('contact_email', sa.Column('contact_email', sa.String(length=255), nullable=True)),
            ('company_name', sa.Column('company_name', sa.String(length=255), nullable=True)),
            ('company_email', sa.Column('company_email', sa.String(length=255), nullable=True)),
            ('rating', sa.Column('rating', sa.String(length=50), nullable=True)),
            ('client_status', sa.Column('client_status', sa.String(length=50), nullable=False, server_default='New')),
            ('description', sa.Column('description', sa.Text(), nullable=True)),
            ('industry', sa.Column('industry', sa.String(length=100), nullable=True)),
            ('number_of_employees', sa.Column('number_of_employees', sa.Integer(), nullable=True)),
            ('currency', sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR')),
            ('preferred_contact_method', sa.Column('preferred_contact_method', sa.String(length=50), nullable=True)),
            ('opportunity_id', sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='SET NULL'), nullable=True)),
            ('qualified_at', sa.Column('qualified_at', sa.DateTime(), nullable=True)),
            ('qualified_by_id', sa.Column('qualified_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)),
        ]

        if is_sqlite:
            with op.batch_alter_table('leads') as batch_op:
                batch_op.alter_column('contact_id', existing_type=sa.String(length=36), nullable=True)
                batch_op.alter_column('business_area', existing_type=sa.String(length=50), server_default='Biogas')
                for col_name, col_def in cols_to_add:
                    if col_name not in existing_cols:
                        batch_op.add_column(col_def)
        else:
            op.alter_column('leads', 'contact_id', existing_type=sa.String(length=36), nullable=True)
            op.alter_column('leads', 'business_area', existing_type=sa.String(length=50), server_default='Biogas')
            for col_name, col_def in cols_to_add:
                if col_name not in existing_cols:
                    op.add_column('leads', col_def)

        # Create indexes for new columns if not present
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('leads')]
        if 'ix_leads_contact_email' not in existing_indexes:
            op.create_index('ix_leads_contact_email', 'leads', ['contact_email'], unique=False)
        if 'ix_leads_company_name' not in existing_indexes:
            op.create_index('ix_leads_company_name', 'leads', ['company_name'], unique=False)
        if 'ix_leads_opportunity_id' not in existing_indexes:
            op.create_index('ix_leads_opportunity_id', 'leads', ['opportunity_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    if 'leads' in existing_tables:
        existing_cols = [c['name'] for c in inspector.get_columns('leads')]
        cols_to_drop = [
            'first_name', 'last_name', 'job_title', 'business_phone', 'mobile_phone',
            'contact_email', 'company_name', 'company_email', 'rating', 'client_status',
            'description', 'industry', 'number_of_employees', 'currency',
            'preferred_contact_method', 'opportunity_id', 'qualified_at', 'qualified_by_id'
        ]

        existing_indexes = [idx['name'] for idx in inspector.get_indexes('leads')]
        for idx in ['ix_leads_opportunity_id', 'ix_leads_company_name', 'ix_leads_contact_email']:
            if idx in existing_indexes:
                op.drop_index(idx, table_name='leads')

        if is_sqlite:
            with op.batch_alter_table('leads') as batch_op:
                for col_name in cols_to_drop:
                    if col_name in existing_cols:
                        batch_op.drop_column(col_name)
        else:
            for col_name in cols_to_drop:
                if col_name in existing_cols:
                    op.drop_column('leads', col_name)

    if 'lead_contact_methods' in existing_tables:
        op.drop_table('lead_contact_methods')

    if 'crm_opportunities' in existing_tables:
        op.drop_table('crm_opportunities')
