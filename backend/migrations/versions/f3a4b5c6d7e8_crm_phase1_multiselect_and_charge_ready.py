"""crm phase 1 multiselect requirement types, optional lead title, remove duplicate constraints, and charge-ready data model

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-10-22 12:00:00.000000

"""
import uuid
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    # 1. Alter lead_name to nullable=True on leads
    if is_sqlite:
        with op.batch_alter_table('leads') as batch_op:
            batch_op.alter_column('lead_name', existing_type=sa.String(length=255), nullable=True)
            batch_op.alter_column('requirement_type', existing_type=sa.String(length=50), nullable=True)
    else:
        op.alter_column('leads', 'lead_name', existing_type=sa.String(length=255), nullable=True)
        op.alter_column('leads', 'requirement_type', existing_type=sa.String(length=50), nullable=True)

    # 2. Drop the duplicate-prevention partial unique indexes
    existing_indices = [idx["name"] for idx in inspector.get_indexes("leads")]
    if "uq_open_lead_account_product" in existing_indices:
        op.drop_index("uq_open_lead_account_product", table_name="leads")
    if "uq_open_lead_contact_product" in existing_indices:
        op.drop_index("uq_open_lead_contact_product", table_name="leads")

    # 3. Create lead_requirement_types table
    existing_tables = inspector.get_table_names()
    if "lead_requirement_types" not in existing_tables:
        op.create_table(
            'lead_requirement_types',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
            sa.Column('requirement_type', sa.String(length=50), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('lead_id', 'requirement_type', name='uq_lead_requirement_type')
        )
        op.create_index('ix_lead_requirement_types_lead_id', 'lead_requirement_types', ['lead_id'])
        op.create_index('ix_lead_requirement_types_requirement_type', 'lead_requirement_types', ['requirement_type'])

        # 4. Migrate existing leads' requirement_type to lead_requirement_types
        connection = bind
        leads_select = sa.text("SELECT id, requirement_type, created_at FROM leads")
        leads_rows = connection.execute(leads_select).fetchall()

        insert_stmt = sa.text(
            "INSERT INTO lead_requirement_types (id, lead_id, requirement_type, created_at) "
            "VALUES (:id, :lead_id, :requirement_type, :created_at)"
        )

        for row in leads_rows:
            lead_id = row[0]
            raw_req = row[1] or ""
            created_at = row[2] or datetime.now(timezone.utc)

            # Safe historical mapping:
            # "Direct Product/Service" -> "Product"
            # "Sample Testing" -> "Sample Testing"
            # "Undetermined" -> "Consulting" (or appropriate fallback)
            clean = raw_req.strip().lower()
            if "sample" in clean:
                mapped = "Sample Testing"
            elif "direct" in clean or "product" in clean:
                mapped = "Product"
            elif "consult" in clean:
                mapped = "Consulting"
            else:
                mapped = "Product" if not clean else "Consulting"

            connection.execute(insert_stmt, {
                "id": str(uuid.uuid4()),
                "lead_id": lead_id,
                "requirement_type": mapped,
                "created_at": created_at
            })

    # 5. Create charge-ready tables
    if "crm_consulting_engagements" not in existing_tables:
        op.create_table(
            'crm_consulting_engagements',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('engagement_id', sa.String(length=50), nullable=False),
            sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
            sa.Column('contact_id', sa.String(length=36), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('scope_description', sa.Text(), nullable=True),
            sa.Column('contract_start_date', sa.Date(), nullable=True),
            sa.Column('contract_end_date', sa.Date(), nullable=True),
            sa.Column('duration_months', sa.Integer(), nullable=True),
            sa.Column('agreed_fee', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('billing_arrangement', sa.String(length=100), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Draft'),
            sa.Column('renewal_history', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_crm_consulting_engagements_engagement_id', 'crm_consulting_engagements', ['engagement_id'], unique=True)
        op.create_index('ix_crm_consulting_engagements_account_id', 'crm_consulting_engagements', ['account_id'])
        op.create_index('ix_crm_consulting_engagements_contact_id', 'crm_consulting_engagements', ['contact_id'])
        op.create_index('ix_crm_consulting_engagements_lead_id', 'crm_consulting_engagements', ['lead_id'])

    if "crm_sample_submissions" not in existing_tables:
        op.create_table(
            'crm_sample_submissions',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('sample_id', sa.String(length=50), nullable=False),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True),
            sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
            sa.Column('contact_id', sa.String(length=36), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
            sa.Column('sample_description', sa.String(length=255), nullable=False),
            sa.Column('sample_type', sa.String(length=100), nullable=True),
            sa.Column('receipt_date', sa.Date(), nullable=True),
            sa.Column('condition_on_receipt', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Received'),
            sa.Column('sample_level_charge', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('is_unsuitable', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('failure_reason', sa.String(length=255), nullable=True),
            sa.Column('stage_reached', sa.String(length=100), nullable=True),
            sa.Column('work_performed', sa.Text(), nullable=True),
            sa.Column('charge_decision', sa.String(length=50), nullable=True),
            sa.Column('authorized_charge_amount', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('replacement_of_sample_id', sa.String(length=36), sa.ForeignKey('crm_sample_submissions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_crm_sample_submissions_sample_id', 'crm_sample_submissions', ['sample_id'], unique=True)
        op.create_index('ix_crm_sample_submissions_lead_id', 'crm_sample_submissions', ['lead_id'])
        op.create_index('ix_crm_sample_submissions_account_id', 'crm_sample_submissions', ['account_id'])
        op.create_index('ix_crm_sample_submissions_contact_id', 'crm_sample_submissions', ['contact_id'])
        op.create_index('ix_crm_sample_submissions_replacement_of', 'crm_sample_submissions', ['replacement_of_sample_id'])

    if "crm_sample_tests" not in existing_tables:
        op.create_table(
            'crm_sample_tests',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('test_record_id', sa.String(length=50), nullable=False),
            sa.Column('sample_id', sa.String(length=36), sa.ForeignKey('crm_sample_submissions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('test_name', sa.String(length=255), nullable=False),
            sa.Column('test_type', sa.String(length=100), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Pending'),
            sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False, server_default='1.00'),
            sa.Column('test_result_reference', sa.String(length=255), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_crm_sample_tests_test_record_id', 'crm_sample_tests', ['test_record_id'], unique=True)
        op.create_index('ix_crm_sample_tests_sample_id', 'crm_sample_tests', ['sample_id'])

    if "crm_testing_charges" not in existing_tables:
        op.create_table(
            'crm_testing_charges',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('charge_id', sa.String(length=50), nullable=False),
            sa.Column('sample_id', sa.String(length=36), sa.ForeignKey('crm_sample_submissions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True),
            sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
            sa.Column('charge_type', sa.String(length=50), nullable=False, server_default='TEST_CHARGE'),
            sa.Column('charge_description', sa.String(length=255), nullable=True),
            sa.Column('charge_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('agreed_unit_rate', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('billable_units', sa.Numeric(precision=10, scale=2), nullable=True, server_default='1.00'),
            sa.Column('sample_charge_applied', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('tests_total', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('approved_additional_charges', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('applicable_discounts', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('final_calculated_total', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
            sa.Column('billing_status', sa.String(length=50), nullable=False, server_default='Pending'),
            sa.Column('idempotency_key', sa.String(length=100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_crm_testing_charges_charge_id', 'crm_testing_charges', ['charge_id'], unique=True)
        op.create_index('ix_crm_testing_charges_sample_id', 'crm_testing_charges', ['sample_id'])
        op.create_index('ix_crm_testing_charges_lead_id', 'crm_testing_charges', ['lead_id'])
        op.create_index('ix_crm_testing_charges_account_id', 'crm_testing_charges', ['account_id'])
        op.create_index('ix_crm_testing_charges_idempotency_key', 'crm_testing_charges', ['idempotency_key'], unique=True)

    if "crm_product_transactions" not in existing_tables:
        op.create_table(
            'crm_product_transactions',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('transaction_id', sa.String(length=50), nullable=False),
            sa.Column('lead_id', sa.String(length=36), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True),
            sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
            sa.Column('contact_id', sa.String(length=36), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
            sa.Column('product_name', sa.String(length=255), nullable=False),
            sa.Column('sku_code', sa.String(length=100), nullable=True),
            sa.Column('transaction_type', sa.String(length=50), nullable=False, server_default='Recommendation'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Pending'),
            sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False, server_default='1.00'),
            sa.Column('unit_of_measure', sa.String(length=50), nullable=False, server_default='litres'),
            sa.Column('unit_rate', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('calculated_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_crm_product_transactions_transaction_id', 'crm_product_transactions', ['transaction_id'], unique=True)
        op.create_index('ix_crm_product_transactions_lead_id', 'crm_product_transactions', ['lead_id'])
        op.create_index('ix_crm_product_transactions_account_id', 'crm_product_transactions', ['account_id'])
        op.create_index('ix_crm_product_transactions_contact_id', 'crm_product_transactions', ['contact_id'])


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_tables = inspector.get_table_names()
    if "crm_product_transactions" in existing_tables:
        op.drop_table('crm_product_transactions')
    if "crm_testing_charges" in existing_tables:
        op.drop_table('crm_testing_charges')
    if "crm_sample_tests" in existing_tables:
        op.drop_table('crm_sample_tests')
    if "crm_sample_submissions" in existing_tables:
        op.drop_table('crm_sample_submissions')
    if "crm_consulting_engagements" in existing_tables:
        op.drop_table('crm_consulting_engagements')
    if "lead_requirement_types" in existing_tables:
        op.drop_table('lead_requirement_types')

    # Re-create partial unique indexes
    where_acc = sa.text("lifecycle_status = 'Open' AND account_id IS NOT NULL AND normalized_requirement IS NOT NULL")
    op.create_index(
        "uq_open_lead_account_product",
        "leads",
        ["account_id", "normalized_requirement"],
        unique=True,
        postgresql_where=where_acc,
        sqlite_where=where_acc
    )

    where_contact = sa.text("lifecycle_status = 'Open' AND account_id IS NULL AND normalized_requirement IS NOT NULL")
    op.create_index(
        "uq_open_lead_contact_product",
        "leads",
        ["contact_id", "normalized_requirement"],
        unique=True,
        postgresql_where=where_contact,
        sqlite_where=where_contact
    )

    if not is_sqlite:
        op.execute(sa.text("UPDATE leads SET lead_name = 'Untitled Lead' WHERE lead_name IS NULL"))
        op.alter_column('leads', 'lead_name', existing_type=sa.String(length=255), nullable=False)
