"""crm_catalogue_management

Revision ID: t7u8v9w0x1y2
Revises: s6t7u8v9w0x1
Create Date: 2026-11-04 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 't7u8v9w0x1y2'
down_revision = 's6t7u8v9w0x1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    # 1. Main Categories
    if 'crm_service_categories' not in tables:
        op.create_table(
            'crm_service_categories',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('prefix', sa.String(length=10), nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('is_deleted', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_service_categories_code', 'crm_service_categories', ['code'])
        op.create_index('ix_crm_service_categories_name', 'crm_service_categories', ['name'])
        op.create_index('ix_crm_service_categories_active', 'crm_service_categories', ['is_active'])

    # 2. Subcategories
    if 'crm_service_subcategories' not in tables:
        op.create_table(
            'crm_service_subcategories',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('category_id', sa.String(length=36), sa.ForeignKey('crm_service_categories.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('is_deleted', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_service_subcategories_cat_id', 'crm_service_subcategories', ['category_id'])
        op.create_index('ix_crm_service_subcategories_code', 'crm_service_subcategories', ['code'])
        op.create_index('ix_crm_service_subcategories_active', 'crm_service_subcategories', ['is_active'])

    # 3. Billing Units
    if 'crm_billing_units' not in tables:
        op.create_table(
            'crm_billing_units',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_billing_units_code', 'crm_billing_units', ['code'])

    # 4. Reporting Units
    if 'crm_reporting_units' not in tables:
        op.create_table(
            'crm_reporting_units',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('symbol', sa.String(length=50), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_reporting_units_code', 'crm_reporting_units', ['code'])

    # 5. Sample Types
    if 'crm_sample_types' not in tables:
        op.create_table(
            'crm_sample_types',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_sample_types_code', 'crm_sample_types', ['code'])

    # 6. Testing Methods
    if 'crm_testing_methods' not in tables:
        op.create_table(
            'crm_testing_methods',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('method_name', sa.String(length=255), nullable=False),
            sa.Column('standard_reference', sa.String(length=255), nullable=True),
            sa.Column('revision', sa.String(length=50), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_testing_methods_code', 'crm_testing_methods', ['code'])

    # 7. Currencies
    if 'crm_currencies' not in tables:
        op.create_table(
            'crm_currencies',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('code', sa.String(length=10), nullable=False, unique=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('symbol', sa.String(length=10), nullable=False),
            sa.Column('is_default', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_currencies_code', 'crm_currencies', ['code'])

    # 8. Tax Configurations & Rates
    if 'crm_tax_configurations' not in tables:
        op.create_table(
            'crm_tax_configurations',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('tax_type', sa.String(length=50), server_default='INTRA_STATE', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_tax_configurations_code', 'crm_tax_configurations', ['code'])

    if 'crm_tax_rates' not in tables:
        op.create_table(
            'crm_tax_rates',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('configuration_id', sa.String(length=36), sa.ForeignKey('crm_tax_configurations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('component_name', sa.String(length=50), nullable=False),
            sa.Column('rate_percentage', sa.Numeric(precision=6, scale=4), nullable=False, server_default='0.0000'),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_tax_rates_config_id', 'crm_tax_rates', ['configuration_id'])

    # 9. Services
    if 'crm_services' not in tables:
        op.create_table(
            'crm_services',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('service_code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('category_id', sa.String(length=36), sa.ForeignKey('crm_service_categories.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('subcategory_id', sa.String(length=36), sa.ForeignKey('crm_service_subcategories.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('billing_unit_id', sa.String(length=36), sa.ForeignKey('crm_billing_units.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('currency_id', sa.String(length=36), sa.ForeignKey('crm_currencies.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('minimum_billing_quantity', sa.Integer(), server_default='1', nullable=False),
            sa.Column('standard_price', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('effective_date', sa.Date(), nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('is_deleted', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('is_addon_eligible', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('can_have_addons', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('source_note', sa.String(length=255), nullable=True),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint('minimum_billing_quantity >= 1', name='ck_service_min_billing_qty_pos'),
            sa.CheckConstraint('standard_price >= 0', name='ck_service_standard_price_non_neg')
        )
        op.create_index('ix_crm_services_code', 'crm_services', ['service_code'])
        op.create_index('ix_crm_services_name', 'crm_services', ['name'])
        op.create_index('ix_crm_services_cat_id', 'crm_services', ['category_id'])
        op.create_index('ix_crm_services_subcat_id', 'crm_services', ['subcategory_id'])
        op.create_index('ix_crm_services_active', 'crm_services', ['is_active'])

    # 10. Service M2M & Sub-entities
    if 'crm_service_sample_types' not in tables:
        op.create_table(
            'crm_service_sample_types',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('service_id', sa.String(length=36), sa.ForeignKey('crm_services.id', ondelete='CASCADE'), nullable=False),
            sa.Column('sample_type_id', sa.String(length=36), sa.ForeignKey('crm_sample_types.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('service_id', 'sample_type_id', name='uq_service_sample_type')
        )
        op.create_index('ix_crm_service_sample_types_svc', 'crm_service_sample_types', ['service_id'])
        op.create_index('ix_crm_service_sample_types_st', 'crm_service_sample_types', ['sample_type_id'])

    if 'crm_service_testing_methods' not in tables:
        op.create_table(
            'crm_service_testing_methods',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('service_id', sa.String(length=36), sa.ForeignKey('crm_services.id', ondelete='CASCADE'), nullable=False),
            sa.Column('testing_method_id', sa.String(length=36), sa.ForeignKey('crm_testing_methods.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('is_default', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('service_id', 'testing_method_id', name='uq_service_testing_method')
        )
        op.create_index('ix_crm_service_testing_methods_svc', 'crm_service_testing_methods', ['service_id'])
        op.create_index('ix_crm_service_testing_methods_tm', 'crm_service_testing_methods', ['testing_method_id'])

    if 'crm_service_reporting_parameters' not in tables:
        op.create_table(
            'crm_service_reporting_parameters',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('service_id', sa.String(length=36), sa.ForeignKey('crm_services.id', ondelete='CASCADE'), nullable=False),
            sa.Column('testing_method_id', sa.String(length=36), sa.ForeignKey('crm_testing_methods.id', ondelete='SET NULL'), nullable=True),
            sa.Column('parameter_name', sa.String(length=255), nullable=False),
            sa.Column('reporting_unit_id', sa.String(length=36), sa.ForeignKey('crm_reporting_units.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('min_range', sa.Numeric(precision=18, scale=4), nullable=True),
            sa.Column('max_range', sa.Numeric(precision=18, scale=4), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_crm_service_reporting_params_svc', 'crm_service_reporting_parameters', ['service_id'])

    if 'crm_service_price_history' not in tables:
        op.create_table(
            'crm_service_price_history',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('service_id', sa.String(length=36), sa.ForeignKey('crm_services.id', ondelete='CASCADE'), nullable=False),
            sa.Column('price', sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column('currency_id', sa.String(length=36), sa.ForeignKey('crm_currencies.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('effective_date', sa.Date(), nullable=False),
            sa.Column('changed_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint('price >= 0', name='ck_service_price_history_non_neg')
        )
        op.create_index('ix_crm_service_price_history_svc', 'crm_service_price_history', ['service_id'])
        op.create_index('ix_crm_service_price_history_eff_date', 'crm_service_price_history', ['effective_date'])

    # 11. Packages & Package Versions
    if 'crm_packages' not in tables:
        op.create_table(
            'crm_packages',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('package_code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('category_id', sa.String(length=36), sa.ForeignKey('crm_service_categories.id', ondelete='SET NULL'), nullable=True),
            sa.Column('subcategory_id', sa.String(length=36), sa.ForeignKey('crm_service_subcategories.id', ondelete='SET NULL'), nullable=True),
            sa.Column('currency_id', sa.String(length=36), sa.ForeignKey('crm_currencies.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('fixed_package_price', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('current_version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('is_deleted', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint('fixed_package_price >= 0', name='ck_package_price_non_neg')
        )
        op.create_index('ix_crm_packages_code', 'crm_packages', ['package_code'])
        op.create_index('ix_crm_packages_name', 'crm_packages', ['name'])

    if 'crm_package_versions' not in tables:
        op.create_table(
            'crm_package_versions',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('package_id', sa.String(length=36), sa.ForeignKey('crm_packages.id', ondelete='CASCADE'), nullable=False),
            sa.Column('version_number', sa.Integer(), nullable=False),
            sa.Column('fixed_price', sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column('currency_id', sa.String(length=36), sa.ForeignKey('crm_currencies.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('change_summary', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('effective_date', sa.Date(), nullable=False),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('package_id', 'version_number', name='uq_package_version_num'),
            sa.CheckConstraint('fixed_price >= 0', name='ck_package_ver_price_non_neg')
        )
        op.create_index('ix_crm_package_versions_pkg_id', 'crm_package_versions', ['package_id'])

    if 'crm_package_components' not in tables:
        op.create_table(
            'crm_package_components',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('package_version_id', sa.String(length=36), sa.ForeignKey('crm_package_versions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('service_id', sa.String(length=36), sa.ForeignKey('crm_services.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
            sa.Column('reference_price', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('package_version_id', 'service_id', name='uq_pkg_ver_service'),
            sa.CheckConstraint('quantity >= 1', name='ck_pkg_comp_qty_pos')
        )
        op.create_index('ix_crm_package_components_ver_id', 'crm_package_components', ['package_version_id'])

    if 'crm_package_addon_configurations' not in tables:
        op.create_table(
            'crm_package_addon_configurations',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('package_version_id', sa.String(length=36), sa.ForeignKey('crm_package_versions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('addon_service_id', sa.String(length=36), sa.ForeignKey('crm_services.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('default_quantity', sa.Integer(), server_default='1', nullable=False),
            sa.Column('override_price', sa.Numeric(precision=18, scale=4), nullable=True),
            sa.Column('is_mandatory', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('package_version_id', 'addon_service_id', name='uq_pkg_ver_addon_service'),
            sa.CheckConstraint('default_quantity >= 1', name='ck_pkg_addon_qty_pos')
        )
        op.create_index('ix_crm_pkg_addon_config_ver_id', 'crm_package_addon_configurations', ['package_version_id'])

    # 12. Quotation Line Items (Immutable Historical Snapshot)
    if 'crm_opportunity_quotation_items' not in tables:
        op.create_table(
            'crm_opportunity_quotation_items',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('quotation_id', sa.String(length=36), sa.ForeignKey('crm_opportunity_quotations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('item_type', sa.String(length=20), nullable=False),  # "SERVICE", "PACKAGE", "ADDON"
            sa.Column('service_id', sa.String(length=36), sa.ForeignKey('crm_services.id', ondelete='SET NULL'), nullable=True),
            sa.Column('package_id', sa.String(length=36), sa.ForeignKey('crm_packages.id', ondelete='SET NULL'), nullable=True),
            sa.Column('package_version_id', sa.String(length=36), sa.ForeignKey('crm_package_versions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('parent_item_id', sa.String(length=36), sa.ForeignKey('crm_opportunity_quotation_items.id', ondelete='CASCADE'), nullable=True),
            sa.Column('item_code', sa.String(length=50), nullable=False),
            sa.Column('item_name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('billing_unit', sa.String(length=50), nullable=True),
            sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
            sa.Column('standard_price', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('unit_price', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('total_price', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
            sa.Column('testing_method_snapshot', sa.Text(), nullable=True),
            sa.Column('reporting_parameters_snapshot', sa.Text(), nullable=True),
            sa.Column('package_components_snapshot', sa.Text(), nullable=True),
            sa.Column('tax_configuration_id', sa.String(length=36), sa.ForeignKey('crm_tax_configurations.id', ondelete='SET NULL'), nullable=True),
            sa.Column('tax_type', sa.String(length=50), nullable=True),
            sa.Column('taxable_amount', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('cgst_rate', sa.Numeric(precision=6, scale=4), server_default='0.0000', nullable=False),
            sa.Column('cgst_amount', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('sgst_rate', sa.Numeric(precision=6, scale=4), server_default='0.0000', nullable=False),
            sa.Column('sgst_amount', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('igst_rate', sa.Numeric(precision=6, scale=4), server_default='0.0000', nullable=False),
            sa.Column('igst_amount', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('total_tax', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('final_total', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint('quantity >= 1', name='ck_quotation_item_qty_pos'),
            sa.CheckConstraint('unit_price >= 0', name='ck_quotation_item_price_non_neg')
        )
        op.create_index('ix_crm_opp_quote_items_qid', 'crm_opportunity_quotation_items', ['quotation_id'])
        op.create_index('ix_crm_opp_quote_items_parent', 'crm_opportunity_quotation_items', ['parent_item_id'])


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    # Drop in reverse dependency order
    table_order = [
        'crm_opportunity_quotation_items',
        'crm_package_addon_configurations',
        'crm_package_components',
        'crm_package_versions',
        'crm_packages',
        'crm_service_price_history',
        'crm_service_reporting_parameters',
        'crm_service_testing_methods',
        'crm_service_sample_types',
        'crm_services',
        'crm_tax_rates',
        'crm_tax_configurations',
        'crm_currencies',
        'crm_testing_methods',
        'crm_sample_types',
        'crm_reporting_units',
        'crm_billing_units',
        'crm_service_subcategories',
        'crm_service_categories'
    ]

    for tbl in table_order:
        if tbl in tables:
            op.drop_table(tbl)
