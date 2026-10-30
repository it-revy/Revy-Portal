"""opportunity_kanban_and_relationship_rules

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-10-29 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'o2p3q4r5s6t7'
down_revision = 'n1o2p3q4r5s6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    if 'crm_opportunities' in existing_tables:
        # 1. First ensure data compliance for test data before constraints
        # Ensure OPP-00008 & OPP-00012 or any Close+Open are consistent
        op.execute(sa.text("""
            UPDATE crm_opportunities
            SET status = 'Won',
                actual_close_date = COALESCE(actual_close_date, updated_at, CURRENT_TIMESTAMP)
            WHERE stage = 'Close' AND status = 'Open'
              AND originating_lead_id IN (
                  SELECT id FROM leads WHERE lifecycle_status = 'Supply'
              );
        """))

        # Any remaining Close+Open moved to Negotiate
        op.execute(sa.text("""
            UPDATE crm_opportunities
            SET stage = 'Negotiate'
            WHERE stage = 'Close' AND status = 'Open';
        """))

        if is_sqlite:
            with op.batch_alter_table('crm_opportunities') as batch_op:
                batch_op.alter_column('account_id', existing_type=sa.String(length=36), nullable=True)
                batch_op.create_check_constraint(
                    'ck_crm_opportunities_account_or_contact',
                    'account_id IS NOT NULL OR contact_id IS NOT NULL'
                )
                batch_op.create_check_constraint(
                    'ck_crm_opportunities_amount_non_negative',
                    'estimated_value IS NULL OR estimated_value >= 0'
                )
                batch_op.create_check_constraint(
                    'ck_crm_opportunities_stage_status',
                    "(status = 'Open' AND stage != 'Close') OR (status IN ('Won', 'Lost') AND stage = 'Close')"
                )
        else:
            op.alter_column('crm_opportunities', 'account_id', existing_type=sa.String(length=36), nullable=True)
            op.create_check_constraint(
                'ck_crm_opportunities_account_or_contact',
                'crm_opportunities',
                'account_id IS NOT NULL OR contact_id IS NOT NULL'
            )
            op.create_check_constraint(
                'ck_crm_opportunities_amount_non_negative',
                'crm_opportunities',
                'estimated_value IS NULL OR estimated_value >= 0'
            )
            op.create_check_constraint(
                'ck_crm_opportunities_stage_status',
                'crm_opportunities',
                "(status = 'Open' AND stage != 'Close') OR (status IN ('Won', 'Lost') AND stage = 'Close')"
            )


def downgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table('crm_opportunities') as batch_op:
            batch_op.drop_constraint('ck_crm_opportunities_stage_status', type_='check')
            batch_op.drop_constraint('ck_crm_opportunities_amount_non_negative', type_='check')
            batch_op.drop_constraint('ck_crm_opportunities_account_or_contact', type_='check')
            batch_op.alter_column('account_id', existing_type=sa.String(length=36), nullable=False)
    else:
        op.drop_constraint('ck_crm_opportunities_stage_status', 'crm_opportunities', type_='check')
        op.drop_constraint('ck_crm_opportunities_amount_non_negative', 'crm_opportunities', type_='check')
        op.drop_constraint('ck_crm_opportunities_account_or_contact', 'crm_opportunities', type_='check')
        op.alter_column('crm_opportunities', 'account_id', existing_type=sa.String(length=36), nullable=False)

