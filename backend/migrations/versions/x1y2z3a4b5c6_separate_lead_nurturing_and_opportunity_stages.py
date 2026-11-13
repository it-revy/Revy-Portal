"""Separate lead nurturing and opportunity sales stages

Revision ID: x1y2z3a4b5c6
Revises: w0x1y2z3a4b5
Create Date: 2026-11-13 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'x1y2z3a4b5c6'
down_revision = 'w0x1y2z3a4b5'
branch_labels = None
depends_on = None

APPROVED_LEAD_NURTURING_STATUSES = (
    'New',
    'Contacted',
    'In Discussion',
    'Qualified',
    'Dormant',
    'Disqualified',
    'Open'
)

APPROVED_OPPORTUNITY_STAGES = (
    'Enquiry',
    'Offer',
    'Negotiation',
    'Supply',
    'Payment',
    'Dormant'
)


def upgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table('leads') as batch_op:
            try:
                batch_op.drop_constraint('ck_leads_lifecycle_status', type_='check')
            except Exception:
                pass
            batch_op.alter_column('lifecycle_status', server_default='New')

        bind.execute(sa.text("""
            UPDATE leads
            SET lifecycle_status = 'New'
            WHERE lifecycle_status IN ('Enquiry', 'Offer', 'Negotiation', 'Supply', 'Payment', 'Open');
        """))

        with op.batch_alter_table('leads') as batch_op:
            status_list_sql = ", ".join([f"'{s}'" for s in APPROVED_LEAD_NURTURING_STATUSES])
            batch_op.create_check_constraint('ck_leads_lifecycle_status', f"lifecycle_status IN ({status_list_sql})")

        with op.batch_alter_table('crm_opportunities') as batch_op:
            try:
                batch_op.drop_constraint('ck_crm_opportunities_stage_status', type_='check')
            except Exception:
                pass
            try:
                batch_op.drop_constraint('ck_crm_opportunities_stage', type_='check')
            except Exception:
                pass
            batch_op.alter_column('stage', server_default='Enquiry')

        bind.execute(sa.text("""
            UPDATE crm_opportunities
            SET stage = 'Enquiry'
            WHERE stage IN ('Qualify', 'Develop', 'Propose/Offer', 'Propose', 'Close');
        """))

        with op.batch_alter_table('crm_opportunities') as batch_op:
            opp_stages_sql = ", ".join([f"'{s}'" for s in APPROVED_OPPORTUNITY_STAGES])
            batch_op.create_check_constraint('ck_crm_opportunities_stage', f"stage IN ({opp_stages_sql})")

    else:
        # PostgreSQL
        op.execute(sa.text("ALTER TABLE leads DROP CONSTRAINT IF EXISTS ck_leads_lifecycle_status;"))
        op.execute(sa.text("""
            UPDATE leads
            SET lifecycle_status = 'New'
            WHERE lifecycle_status IN ('Enquiry', 'Offer', 'Negotiation', 'Supply', 'Payment', 'Open');
        """))
        op.alter_column('leads', 'lifecycle_status', server_default='New')
        status_list_sql = ", ".join([f"'{s}'" for s in APPROVED_LEAD_NURTURING_STATUSES])
        op.create_check_constraint(
            'ck_leads_lifecycle_status',
            'leads',
            f"lifecycle_status IN ({status_list_sql})"
        )

        op.execute(sa.text("ALTER TABLE crm_opportunities DROP CONSTRAINT IF EXISTS ck_crm_opportunities_stage_status;"))
        op.execute(sa.text("ALTER TABLE crm_opportunities DROP CONSTRAINT IF EXISTS ck_crm_opportunities_stage;"))
        op.execute(sa.text("""
            UPDATE crm_opportunities
            SET stage = 'Enquiry'
            WHERE stage IN ('Qualify', 'Develop', 'Propose/Offer', 'Propose', 'Close');
        """))
        op.alter_column('crm_opportunities', 'stage', server_default='Enquiry')
        opp_stages_sql = ", ".join([f"'{s}'" for s in APPROVED_OPPORTUNITY_STAGES])
        op.create_check_constraint(
            'ck_crm_opportunities_stage',
            'crm_opportunities',
            f"stage IN ({opp_stages_sql})"
        )


def downgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table('leads') as batch_op:
            batch_op.drop_constraint('ck_leads_lifecycle_status', type_='check')
            batch_op.alter_column('lifecycle_status', server_default='Enquiry')
        with op.batch_alter_table('crm_opportunities') as batch_op:
            batch_op.drop_constraint('ck_crm_opportunities_stage', type_='check')
            batch_op.alter_column('stage', server_default='Qualify')
    else:
        op.drop_constraint('ck_leads_lifecycle_status', 'leads', type_='check')
        op.alter_column('leads', 'lifecycle_status', server_default='Enquiry')
        op.drop_constraint('ck_crm_opportunities_stage', 'crm_opportunities', type_='check')
        op.alter_column('crm_opportunities', 'stage', server_default='Qualify')
