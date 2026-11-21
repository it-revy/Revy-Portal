"""Add proforma invoice and company settings

Revision ID: w0x1y2z3a4b5
Revises: v9w0x1y2z3a4
Create Date: 2026-11-12 14:48:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.dialects import postgresql
import json
from datetime import datetime, timezone
import uuid

# revision identifiers, used by Alembic.
revision = 'w0x1y2z3a4b5'
down_revision = 'v9w0x1y2z3a4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    # 1. Add customer_id to accounts
    if 'accounts' in tables:
        acc_cols = [c['name'] for c in inspector.get_columns('accounts')]
        if 'customer_id' not in acc_cols:
            op.add_column('accounts', sa.Column('customer_id', sa.String(length=100), nullable=True))
            existing_indexes = [ix['name'] for ix in inspector.get_indexes('accounts')]
            if 'ix_accounts_customer_id' not in existing_indexes:
                op.create_index(op.f('ix_accounts_customer_id'), 'accounts', ['customer_id'], unique=False)

    # 2. Add quotation totals & tax fields to crm_opportunity_quotations
    if 'crm_opportunity_quotations' in tables:
        q_cols = [c['name'] for c in inspector.get_columns('crm_opportunity_quotations')]
        if 'subtotal' not in q_cols:
            op.add_column('crm_opportunity_quotations', sa.Column('subtotal', sa.Numeric(14, 2), server_default='0.0', nullable=False))
        if 'tax_type' not in q_cols:
            op.add_column('crm_opportunity_quotations', sa.Column('tax_type', sa.String(length=50), server_default='INTRA_STATE', nullable=True))
        if 'tax_configuration_id' not in q_cols:
            op.add_column('crm_opportunity_quotations', sa.Column('tax_configuration_id', sa.String(length=36), nullable=True))
            if 'crm_tax_configurations' in tables:
                op.create_foreign_key('fk_opp_quote_tax_config', 'crm_opportunity_quotations', 'crm_tax_configurations', ['tax_configuration_id'], ['id'], ondelete='SET NULL')
        if 'cgst_amount' not in q_cols:
            op.add_column('crm_opportunity_quotations', sa.Column('cgst_amount', sa.Numeric(14, 2), server_default='0.0', nullable=False))
        if 'sgst_amount' not in q_cols:
            op.add_column('crm_opportunity_quotations', sa.Column('sgst_amount', sa.Numeric(14, 2), server_default='0.0', nullable=False))
        if 'igst_amount' not in q_cols:
            op.add_column('crm_opportunity_quotations', sa.Column('igst_amount', sa.Numeric(14, 2), server_default='0.0', nullable=False))
        if 'total_tax' not in q_cols:
            op.add_column('crm_opportunity_quotations', sa.Column('total_tax', sa.Numeric(14, 2), server_default='0.0', nullable=False))
        if 'discount_amount' not in q_cols:
            op.add_column('crm_opportunity_quotations', sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0.0', nullable=False))

    # 3. Add discount_amount to crm_opportunity_quotation_items
    if 'crm_opportunity_quotation_items' in tables:
        qi_cols = [c['name'] for c in inspector.get_columns('crm_opportunity_quotation_items')]
        if 'discount_amount' not in qi_cols:
            op.add_column('crm_opportunity_quotation_items', sa.Column('discount_amount', sa.Numeric(18, 4), server_default='0.0', nullable=False))

    # 4. Create crm_company_settings table
    if 'crm_company_settings' not in tables:
        op.create_table(
            'crm_company_settings',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('company_name', sa.String(length=255), nullable=False, server_default='REVY Environmental Solutions Pvt. Ltd.'),
            sa.Column('wordmark', sa.String(length=255), nullable=True, server_default='REVY Environmental Solutions'),
            sa.Column('tagline', sa.String(length=255), nullable=True, server_default='Committed for a Greener Earth!'),
            sa.Column('address_lines', sa.JSON(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=True, server_default='mail@revy.co.in'),
            sa.Column('phone', sa.String(length=50), nullable=True, server_default='+91-9876543210'),
            sa.Column('website', sa.String(length=255), nullable=True, server_default='www.revy.co.in'),
            sa.Column('gstin', sa.String(length=50), nullable=True, server_default='24AAICR4401M1ZD'),
            sa.Column('pan', sa.String(length=50), nullable=True, server_default='AAICR4401M'),
            sa.Column('logo_url', sa.Text(), nullable=True, server_default='/images/logo.png'),
            sa.Column('bank_name', sa.String(length=255), nullable=False, server_default='Bank Of Baroda, Alkapuri Branch'),
            sa.Column('bank_account_number', sa.String(length=100), nullable=False, server_default='01880200001183'),
            sa.Column('bank_ifsc', sa.String(length=50), nullable=False, server_default='BARB0ALKAPU'),
            sa.Column('bank_branch', sa.String(length=255), nullable=True, server_default='Alkapuri Branch'),
            sa.Column('service_description', sa.String(length=255), nullable=True, server_default='Technical Testing & Analysis Services'),
            sa.Column('sac_code', sa.String(length=50), nullable=True, server_default='998346'),
            sa.Column('signatory_name', sa.String(length=255), nullable=True, server_default='Vanita Prasad'),
            sa.Column('signatory_title', sa.String(length=255), nullable=True, server_default='Authorised Signatory'),
            sa.Column('signatory_company_label', sa.String(length=255), nullable=True, server_default='For REVY Environmental Solutions Pvt. Ltd.'),
            sa.Column('signature_image_url', sa.Text(), nullable=True, server_default='/images/signature.png'),
            sa.Column('default_terms', sa.JSON(), nullable=False),
            sa.Column('footer_text', sa.Text(), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )

    # Ensure default REVY company settings seeded
    conn = op.get_bind()
    settings_count = conn.execute(sa.text("SELECT count(*) FROM crm_company_settings")).scalar()
    if settings_count == 0:
        settings_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        conn.execute(
            sa.text("""
                INSERT INTO crm_company_settings (
                    id, company_name, wordmark, tagline, address_lines,
                    email, phone, website, gstin, pan, logo_url,
                    bank_name, bank_account_number, bank_ifsc, bank_branch,
                    service_description, sac_code,
                    signatory_name, signatory_title, signatory_company_label, signature_image_url,
                    default_terms, footer_text, created_at, updated_at
                ) VALUES (
                    :id, :company_name, :wordmark, :tagline, :address_lines,
                    :email, :phone, :website, :gstin, :pan, :logo_url,
                    :bank_name, :bank_account_number, :bank_ifsc, :bank_branch,
                    :service_description, :sac_code,
                    :signatory_name, :signatory_title, :signatory_company_label, :signature_image_url,
                    :default_terms, :footer_text, :created_at, :updated_at
                )
            """),
            {
                "id": settings_id,
                "company_name": "REVY Environmental Solutions Pvt. Ltd.",
                "wordmark": "REVY Environmental Solutions",
                "tagline": "Committed for a Greener Earth!",
                "address_lines": json.dumps([
                    "313-314, Siddharth Upscale Vasna Road",
                    "Vadodara-390007, Gujarat, India"
                ]),
                "email": "mail@revy.co.in",
                "phone": "+91-9876543210",
                "website": "www.revy.co.in",
                "gstin": "24AAICR4401M1ZD",
                "pan": "AAICR4401M",
                "logo_url": "/images/logo.png",
                "bank_name": "Bank Of Baroda, Alkapuri Branch",
                "bank_account_number": "01880200001183",
                "bank_ifsc": "BARB0ALKAPU",
                "bank_branch": "Alkapuri Branch",
                "service_description": "Technical Testing & Analysis Services",
                "sac_code": "998346",
                "signatory_name": "Vanita Prasad",
                "signatory_title": "Authorised Signatory",
                "signatory_company_label": "For REVY Environmental Solutions Pvt. Ltd.",
                "signature_image_url": "/images/signature.png",
                "default_terms": json.dumps([
                    "100 % Advance alongwith PO or Work order",
                    'Payment to be made in Favour of " REVY Environmental Solutions Pvt.Ltd.',
                    "Transportation cost for delivery or rendering services will be charged extra as actual",
                    "We will not be any storing sample provided by client after 7 days post  analysis"
                ]),
                "footer_text": "REVY Environmental Solutions Pvt. Ltd. | 313-314, Siddharth Upscale Vasna Road, Vadodara-390007, Gujarat, India | www.revy.co.in",
                "created_at": now,
                "updated_at": now
            }
        )

    # 5. Create crm_proforma_invoices table
    if 'crm_proforma_invoices' not in tables:
        op.create_table(
            'crm_proforma_invoices',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('pi_number', sa.String(length=50), nullable=False),
            sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('quotation_id', sa.String(length=36), sa.ForeignKey('crm_opportunity_quotations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
            sa.Column('current_revision_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('financial_year', sa.String(length=20), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Issued'),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index(op.f('ix_crm_proforma_invoices_pi_number'), 'crm_proforma_invoices', ['pi_number'], unique=True)
        op.create_index(op.f('ix_crm_proforma_invoices_opportunity_id'), 'crm_proforma_invoices', ['opportunity_id'], unique=False)
        op.create_index(op.f('ix_crm_proforma_invoices_quotation_id'), 'crm_proforma_invoices', ['quotation_id'], unique=False)
        op.create_index(op.f('ix_crm_proforma_invoices_account_id'), 'crm_proforma_invoices', ['account_id'], unique=False)
        op.create_index(op.f('ix_crm_proforma_invoices_financial_year'), 'crm_proforma_invoices', ['financial_year'], unique=False)
        op.create_index(op.f('ix_crm_proforma_invoices_status'), 'crm_proforma_invoices', ['status'], unique=False)

    # 6. Create crm_proforma_invoice_revisions table
    if 'crm_proforma_invoice_revisions' not in tables:
        op.create_table(
            'crm_proforma_invoice_revisions',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('proforma_invoice_id', sa.String(length=36), sa.ForeignKey('crm_proforma_invoices.id', ondelete='CASCADE'), nullable=False),
            sa.Column('revision_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('pi_number', sa.String(length=50), nullable=False),
            sa.Column('pi_date', sa.Date(), nullable=False),
            sa.Column('financial_year', sa.String(length=20), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Issued'),
            sa.Column('reference_note', sa.Text(), nullable=True),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
            sa.Column('subtotal', sa.Numeric(18, 4), nullable=False, server_default='0.0'),
            sa.Column('tax_type', sa.String(length=50), nullable=False, server_default='INTRA_STATE'),
            sa.Column('tax_configuration_id', sa.String(length=36), sa.ForeignKey('crm_tax_configurations.id', ondelete='SET NULL'), nullable=True),
            sa.Column('cgst_rate', sa.Numeric(6, 4), nullable=False, server_default='0.0'),
            sa.Column('cgst_amount', sa.Numeric(18, 4), nullable=False, server_default='0.0'),
            sa.Column('sgst_rate', sa.Numeric(6, 4), nullable=False, server_default='0.0'),
            sa.Column('sgst_amount', sa.Numeric(18, 4), nullable=False, server_default='0.0'),
            sa.Column('igst_rate', sa.Numeric(6, 4), nullable=False, server_default='0.0'),
            sa.Column('igst_amount', sa.Numeric(18, 4), nullable=False, server_default='0.0'),
            sa.Column('total_tax', sa.Numeric(18, 4), nullable=False, server_default='0.0'),
            sa.Column('grand_total', sa.Numeric(18, 4), nullable=False, server_default='0.0'),
            sa.Column('company_snapshot', sa.JSON(), nullable=False),
            sa.Column('customer_snapshot', sa.JSON(), nullable=False),
            sa.Column('terms_snapshot', sa.JSON(), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('proforma_invoice_id', 'revision_number', name='uq_pi_rev_num')
        )
        op.create_index(op.f('ix_crm_proforma_invoice_revisions_proforma_invoice_id'), 'crm_proforma_invoice_revisions', ['proforma_invoice_id'], unique=False)
        op.create_index(op.f('ix_crm_proforma_invoice_revisions_pi_number'), 'crm_proforma_invoice_revisions', ['pi_number'], unique=False)

    # 7. Create crm_proforma_invoice_items table
    if 'crm_proforma_invoice_items' not in tables:
        op.create_table(
            'crm_proforma_invoice_items',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('revision_id', sa.String(length=36), sa.ForeignKey('crm_proforma_invoice_revisions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('sr_no', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('item_type', sa.String(length=50), nullable=False, server_default='SERVICE'),
            sa.Column('service_id', sa.String(length=36), sa.ForeignKey('crm_services.id', ondelete='SET NULL'), nullable=True),
            sa.Column('package_id', sa.String(length=36), sa.ForeignKey('crm_packages.id', ondelete='SET NULL'), nullable=True),
            sa.Column('item_code', sa.String(length=50), nullable=True),
            sa.Column('item_name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('quantity', sa.Numeric(18, 4), nullable=False, server_default='1.0'),
            sa.Column('unit', sa.String(length=50), nullable=True),
            sa.Column('rate', sa.Numeric(18, 4), nullable=False, server_default='0.0'),
            sa.Column('amount', sa.Numeric(18, 4), nullable=False, server_default='0.0'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index(op.f('ix_crm_proforma_invoice_items_revision_id'), 'crm_proforma_invoice_items', ['revision_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'crm_proforma_invoice_items' in tables:
        op.drop_table('crm_proforma_invoice_items')
    if 'crm_proforma_invoice_revisions' in tables:
        op.drop_table('crm_proforma_invoice_revisions')
    if 'crm_proforma_invoices' in tables:
        op.drop_table('crm_proforma_invoices')
    if 'crm_company_settings' in tables:
        op.drop_table('crm_company_settings')

    if 'crm_opportunity_quotation_items' in tables:
        qi_cols = [c['name'] for c in inspector.get_columns('crm_opportunity_quotation_items')]
        if 'discount_amount' in qi_cols:
            op.drop_column('crm_opportunity_quotation_items', 'discount_amount')

    if 'crm_opportunity_quotations' in tables:
        q_cols = [c['name'] for c in inspector.get_columns('crm_opportunity_quotations')]
        fks = [fk['name'] for fk in inspector.get_foreign_keys('crm_opportunity_quotations')]
        if 'fk_opp_quote_tax_config' in fks:
            op.drop_constraint('fk_opp_quote_tax_config', 'crm_opportunity_quotations', type_='foreignkey')
        for col in ['discount_amount', 'total_tax', 'igst_amount', 'sgst_amount', 'cgst_amount', 'tax_configuration_id', 'tax_type', 'subtotal']:
            if col in q_cols:
                op.drop_column('crm_opportunity_quotations', col)

    if 'accounts' in tables:
        acc_cols = [c['name'] for c in inspector.get_columns('accounts')]
        indexes = [ix['name'] for ix in inspector.get_indexes('accounts')]
        if 'ix_accounts_customer_id' in indexes:
            op.drop_index(op.f('ix_accounts_customer_id'), table_name='accounts')
        if 'customer_id' in acc_cols:
            op.drop_column('accounts', 'customer_id')
