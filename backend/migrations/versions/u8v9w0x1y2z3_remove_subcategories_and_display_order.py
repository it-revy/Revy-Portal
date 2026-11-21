"""remove_subcategories_and_display_order

Revision ID: u8v9w0x1y2z3
Revises: t7u8v9w0x1y2
Create Date: 2026-11-05 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'u8v9w0x1y2z3'
down_revision = 't7u8v9w0x1y2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    # 1. Backfill category_id for crm_services if any nulls exist
    if 'crm_services' in tables and 'crm_service_subcategories' in tables:
        service_cols = [c['name'] for c in inspector.get_columns('crm_services')]
        if 'subcategory_id' in service_cols:
            bind.execute(sa.text("""
                UPDATE crm_services s
                SET category_id = sub.category_id
                FROM crm_service_subcategories sub
                WHERE s.subcategory_id = sub.id AND (s.category_id IS NULL OR s.category_id = '')
            """))

    # 2. Backfill category_id for crm_packages if any nulls exist
    if 'crm_packages' in tables and 'crm_service_subcategories' in tables:
        package_cols = [c['name'] for c in inspector.get_columns('crm_packages')]
        if 'subcategory_id' in package_cols:
            bind.execute(sa.text("""
                UPDATE crm_packages p
                SET category_id = sub.category_id
                FROM crm_service_subcategories sub
                WHERE p.subcategory_id = sub.id AND (p.category_id IS NULL OR p.category_id = '')
            """))

    # 3. Ensure category_id on crm_services is NOT NULL
    if 'crm_services' in tables:
        service_cols = [c['name'] for c in inspector.get_columns('crm_services')]
        if 'category_id' in service_cols:
            op.alter_column('crm_services', 'category_id', nullable=False)

    # 4. Remove subcategory foreign key constraint and column from crm_services
    if 'crm_services' in tables:
        fks = inspector.get_foreign_keys('crm_services')
        for fk in fks:
            if fk.get('referred_table') == 'crm_service_subcategories':
                fk_name = fk.get('name')
                if fk_name:
                    op.drop_constraint(fk_name, 'crm_services', type_='foreignkey')

        # Drop index on subcategory_id if present
        indices = inspector.get_indexes('crm_services')
        for idx in indices:
            if 'subcategory_id' in idx.get('column_names', []):
                op.drop_index(idx['name'], table_name='crm_services')

        service_cols = [c['name'] for c in inspector.get_columns('crm_services')]
        if 'subcategory_id' in service_cols:
            op.drop_column('crm_services', 'subcategory_id')

    # 5. Remove subcategory foreign key constraint and column from crm_packages
    if 'crm_packages' in tables:
        fks = inspector.get_foreign_keys('crm_packages')
        for fk in fks:
            if fk.get('referred_table') == 'crm_service_subcategories':
                fk_name = fk.get('name')
                if fk_name:
                    op.drop_constraint(fk_name, 'crm_packages', type_='foreignkey')

        indices = inspector.get_indexes('crm_packages')
        for idx in indices:
            if 'subcategory_id' in idx.get('column_names', []):
                op.drop_index(idx['name'], table_name='crm_packages')

        package_cols = [c['name'] for c in inspector.get_columns('crm_packages')]
        if 'subcategory_id' in package_cols:
            op.drop_column('crm_packages', 'subcategory_id')

    # 6. Drop crm_service_subcategories table if present
    if 'crm_service_subcategories' in tables:
        op.drop_table('crm_service_subcategories')

    # 7. Drop display_order columns and valid_display_order constraints if present
    for table_name in ['crm_service_categories', 'crm_services', 'crm_packages']:
        if table_name in tables:
            cols = [c['name'] for c in inspector.get_columns(table_name)]
            if 'display_order' in cols:
                op.drop_column(table_name, 'display_order')

            # Drop any valid_display_order check constraints
            try:
                constrs = inspector.get_check_constraints(table_name)
                for c in constrs:
                    if 'display_order' in c.get('name', '').lower() or 'display' in c.get('name', '').lower():
                        op.drop_constraint(c['name'], table_name, type_='check')
            except Exception:
                pass


def downgrade():
    pass
