"""crm_schema_enhancements

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2026-11-02 14:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'r5s6t7u8v9w0'
down_revision = 'q4r5s6t7u8v9'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    tables = inspector.get_table_names()

    # 1. ACCOUNTS TABLE ENHANCEMENTS
    if 'accounts' in tables:
        acc_cols = [c['name'] for c in inspector.get_columns('accounts')]

        if is_sqlite:
            with op.batch_alter_table('accounts') as batch_op:
                if 'business_area' not in acc_cols:
                    batch_op.add_column(sa.Column('business_area', sa.String(length=50), nullable=True))
                if 'country' not in acc_cols:
                    batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True))
                if 'state' not in acc_cols:
                    batch_op.add_column(sa.Column('state', sa.String(length=100), nullable=True))
                if 'city' not in acc_cols:
                    batch_op.add_column(sa.Column('city', sa.String(length=100), nullable=True))
                if 'billing_address' not in acc_cols:
                    batch_op.add_column(sa.Column('billing_address', sa.Text(), nullable=True))
                if 'shipping_address' not in acc_cols:
                    batch_op.add_column(sa.Column('shipping_address', sa.Text(), nullable=True))
                if 'gst_number' not in acc_cols:
                    batch_op.add_column(sa.Column('gst_number', sa.String(length=30), nullable=True))
                if 'pan_number' not in acc_cols:
                    batch_op.add_column(sa.Column('pan_number', sa.String(length=20), nullable=True))
                if 'parent_account_id' not in acc_cols:
                    batch_op.add_column(sa.Column('parent_account_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_accounts_parent_account_id',
                        'accounts',
                        ['parent_account_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
                if 'created_by_id' not in acc_cols:
                    batch_op.add_column(sa.Column('created_by_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_accounts_created_by_id',
                        'users',
                        ['created_by_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
                if 'updated_by_id' not in acc_cols:
                    batch_op.add_column(sa.Column('updated_by_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_accounts_updated_by_id',
                        'users',
                        ['updated_by_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
        else:
            if 'business_area' not in acc_cols:
                op.add_column('accounts', sa.Column('business_area', sa.String(length=50), nullable=True))
            if 'country' not in acc_cols:
                op.add_column('accounts', sa.Column('country', sa.String(length=100), nullable=True))
            if 'state' not in acc_cols:
                op.add_column('accounts', sa.Column('state', sa.String(length=100), nullable=True))
            if 'city' not in acc_cols:
                op.add_column('accounts', sa.Column('city', sa.String(length=100), nullable=True))
            if 'billing_address' not in acc_cols:
                op.add_column('accounts', sa.Column('billing_address', sa.Text(), nullable=True))
            if 'shipping_address' not in acc_cols:
                op.add_column('accounts', sa.Column('shipping_address', sa.Text(), nullable=True))
            if 'gst_number' not in acc_cols:
                op.add_column('accounts', sa.Column('gst_number', sa.String(length=30), nullable=True))
            if 'pan_number' not in acc_cols:
                op.add_column('accounts', sa.Column('pan_number', sa.String(length=20), nullable=True))
            if 'parent_account_id' not in acc_cols:
                op.add_column('accounts', sa.Column('parent_account_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_accounts_parent_account_id',
                    'accounts',
                    'accounts',
                    ['parent_account_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
            if 'created_by_id' not in acc_cols:
                op.add_column('accounts', sa.Column('created_by_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_accounts_created_by_id',
                    'accounts',
                    'users',
                    ['created_by_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
            if 'updated_by_id' not in acc_cols:
                op.add_column('accounts', sa.Column('updated_by_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_accounts_updated_by_id',
                    'accounts',
                    'users',
                    ['updated_by_id'],
                    ['id'],
                    ondelete='SET NULL'
                )

        existing_acc_indexes = [ix['name'] for ix in inspector.get_indexes('accounts')]
        if 'ix_accounts_parent_account_id' not in existing_acc_indexes:
            op.create_index('ix_accounts_parent_account_id', 'accounts', ['parent_account_id'])

    # 2. CONTACTS TABLE ENHANCEMENTS
    if 'contacts' in tables:
        con_cols = [c['name'] for c in inspector.get_columns('contacts')]

        if is_sqlite:
            with op.batch_alter_table('contacts') as batch_op:
                if 'first_name' not in con_cols:
                    batch_op.add_column(sa.Column('first_name', sa.String(length=100), nullable=True))
                if 'last_name' not in con_cols:
                    batch_op.add_column(sa.Column('last_name', sa.String(length=100), nullable=True))
                if 'whatsapp_number' not in con_cols:
                    batch_op.add_column(sa.Column('whatsapp_number', sa.String(length=30), nullable=True))
                if 'is_primary' not in con_cols:
                    batch_op.add_column(sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('0')))
                if 'created_by_id' not in con_cols:
                    batch_op.add_column(sa.Column('created_by_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_contacts_created_by_id',
                        'users',
                        ['created_by_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
                if 'updated_by_id' not in con_cols:
                    batch_op.add_column(sa.Column('updated_by_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_contacts_updated_by_id',
                        'users',
                        ['updated_by_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
        else:
            if 'first_name' not in con_cols:
                op.add_column('contacts', sa.Column('first_name', sa.String(length=100), nullable=True))
            if 'last_name' not in con_cols:
                op.add_column('contacts', sa.Column('last_name', sa.String(length=100), nullable=True))
            if 'whatsapp_number' not in con_cols:
                op.add_column('contacts', sa.Column('whatsapp_number', sa.String(length=30), nullable=True))
            if 'is_primary' not in con_cols:
                op.add_column('contacts', sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')))
            if 'created_by_id' not in con_cols:
                op.add_column('contacts', sa.Column('created_by_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_contacts_created_by_id',
                    'contacts',
                    'users',
                    ['created_by_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
            if 'updated_by_id' not in con_cols:
                op.add_column('contacts', sa.Column('updated_by_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_contacts_updated_by_id',
                    'contacts',
                    'users',
                    ['updated_by_id'],
                    ['id'],
                    ondelete='SET NULL'
                )

        existing_con_indexes = [ix['name'] for ix in inspector.get_indexes('contacts')]
        if 'ix_contacts_is_primary' not in existing_con_indexes:
            op.create_index('ix_contacts_is_primary', 'contacts', ['account_id', 'is_primary'])

        # Data Backfill: split existing name into first_name and last_name
        contacts_table = sa.table(
            'contacts',
            sa.column('id', sa.String),
            sa.column('name', sa.String),
            sa.column('first_name', sa.String),
            sa.column('last_name', sa.String),
        )
        try:
            results = bind.execute(sa.select(contacts_table.c.id, contacts_table.c.name)).fetchall()
            for row in results:
                c_id, full_name = row[0], row[1]
                if full_name and full_name.strip():
                    parts = full_name.strip().split(None, 1)
                    fn = parts[0]
                    ln = parts[1] if len(parts) > 1 else None
                    bind.execute(
                        contacts_table.update()
                        .where(contacts_table.c.id == c_id)
                        .values(first_name=fn, last_name=ln)
                    )
        except Exception:
            pass

    # 3. LEADS TABLE ENHANCEMENTS
    if 'leads' in tables:
        lead_cols = [c['name'] for c in inspector.get_columns('leads')]

        if is_sqlite:
            with op.batch_alter_table('leads') as batch_op:
                if 'disqualification_reason' not in lead_cols:
                    batch_op.add_column(sa.Column('disqualification_reason', sa.Text(), nullable=True))
                if 'converted_at' not in lead_cols:
                    batch_op.add_column(sa.Column('converted_at', sa.DateTime(), nullable=True))
                if 'converted_by_id' not in lead_cols:
                    batch_op.add_column(sa.Column('converted_by_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_leads_converted_by_id',
                        'users',
                        ['converted_by_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
        else:
            if 'disqualification_reason' not in lead_cols:
                op.add_column('leads', sa.Column('disqualification_reason', sa.Text(), nullable=True))
            if 'converted_at' not in lead_cols:
                op.add_column('leads', sa.Column('converted_at', sa.DateTime(), nullable=True))
            if 'converted_by_id' not in lead_cols:
                op.add_column('leads', sa.Column('converted_by_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_leads_converted_by_id',
                    'leads',
                    'users',
                    ['converted_by_id'],
                    ['id'],
                    ondelete='SET NULL'
                )

        # Backfill converted_at/converted_by_id from qualified_at/qualified_by_id if qualified
        leads_table = sa.table(
            'leads',
            sa.column('id', sa.String),
            sa.column('qualified_at', sa.DateTime),
            sa.column('qualified_by_id', sa.String),
            sa.column('converted_at', sa.DateTime),
            sa.column('converted_by_id', sa.String),
        )
        try:
            bind.execute(
                leads_table.update()
                .where(leads_table.c.qualified_at.isnot(None))
                .where(leads_table.c.converted_at.is_(None))
                .values(
                    converted_at=leads_table.c.qualified_at,
                    converted_by_id=leads_table.c.qualified_by_id
                )
            )
        except Exception:
            pass

    # 4. OPPORTUNITIES TABLE ENHANCEMENTS
    if 'crm_opportunities' in tables:
        opp_cols = [c['name'] for c in inspector.get_columns('crm_opportunities')]

        if is_sqlite:
            with op.batch_alter_table('crm_opportunities') as batch_op:
                if 'won_reason' not in opp_cols:
                    batch_op.add_column(sa.Column('won_reason', sa.Text(), nullable=True))
                if 'closed_by_id' not in opp_cols:
                    batch_op.add_column(sa.Column('closed_by_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_opps_closed_by_id',
                        'users',
                        ['closed_by_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
                if 'reopened_at' not in opp_cols:
                    batch_op.add_column(sa.Column('reopened_at', sa.DateTime(), nullable=True))
                if 'reopened_by_id' not in opp_cols:
                    batch_op.add_column(sa.Column('reopened_by_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_opps_reopened_by_id',
                        'users',
                        ['reopened_by_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
        else:
            if 'won_reason' not in opp_cols:
                op.add_column('crm_opportunities', sa.Column('won_reason', sa.Text(), nullable=True))
            if 'closed_by_id' not in opp_cols:
                op.add_column('crm_opportunities', sa.Column('closed_by_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_opps_closed_by_id',
                    'crm_opportunities',
                    'users',
                    ['closed_by_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
            if 'reopened_at' not in opp_cols:
                op.add_column('crm_opportunities', sa.Column('reopened_at', sa.DateTime(), nullable=True))
            if 'reopened_by_id' not in opp_cols:
                op.add_column('crm_opportunities', sa.Column('reopened_by_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_opps_reopened_by_id',
                    'crm_opportunities',
                    'users',
                    ['reopened_by_id'],
                    ['id'],
                    ondelete='SET NULL'
                )


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    tables = inspector.get_table_names()

    if 'crm_opportunities' in tables:
        opp_cols = [c['name'] for c in inspector.get_columns('crm_opportunities')]
        if is_sqlite:
            with op.batch_alter_table('crm_opportunities') as batch_op:
                for col in ['won_reason', 'closed_by_id', 'reopened_at', 'reopened_by_id']:
                    if col in opp_cols:
                        batch_op.drop_column(col)
        else:
            for col in ['won_reason', 'closed_by_id', 'reopened_at', 'reopened_by_id']:
                if col in opp_cols:
                    op.drop_column('crm_opportunities', col)

    if 'leads' in tables:
        lead_cols = [c['name'] for c in inspector.get_columns('leads')]
        if is_sqlite:
            with op.batch_alter_table('leads') as batch_op:
                for col in ['disqualification_reason', 'converted_at', 'converted_by_id']:
                    if col in lead_cols:
                        batch_op.drop_column(col)
        else:
            for col in ['disqualification_reason', 'converted_at', 'converted_by_id']:
                if col in lead_cols:
                    op.drop_column('leads', col)

    if 'contacts' in tables:
        con_cols = [c['name'] for c in inspector.get_columns('contacts')]
        if is_sqlite:
            with op.batch_alter_table('contacts') as batch_op:
                for col in ['first_name', 'last_name', 'whatsapp_number', 'is_primary', 'created_by_id', 'updated_by_id']:
                    if col in con_cols:
                        batch_op.drop_column(col)
        else:
            for col in ['first_name', 'last_name', 'whatsapp_number', 'is_primary', 'created_by_id', 'updated_by_id']:
                if col in con_cols:
                    op.drop_column('contacts', col)

    if 'accounts' in tables:
        acc_cols = [c['name'] for c in inspector.get_columns('accounts')]
        if is_sqlite:
            with op.batch_alter_table('accounts') as batch_op:
                for col in ['business_area', 'country', 'state', 'city', 'billing_address', 'shipping_address', 'gst_number', 'pan_number', 'parent_account_id', 'created_by_id', 'updated_by_id']:
                    if col in acc_cols:
                        batch_op.drop_column(col)
        else:
            for col in ['business_area', 'country', 'state', 'city', 'billing_address', 'shipping_address', 'gst_number', 'pan_number', 'parent_account_id', 'created_by_id', 'updated_by_id']:
                if col in acc_cols:
                    op.drop_column('accounts', col)

