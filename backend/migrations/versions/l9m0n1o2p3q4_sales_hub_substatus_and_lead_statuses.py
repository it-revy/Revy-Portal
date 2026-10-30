"""sales_hub_substatus_and_lead_statuses

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-10-26 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'l9m0n1o2p3q4'
down_revision = 'k8l9m0n1o2p3'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    # 1. Add sub_status to crm_opportunities if absent
    if 'crm_opportunities' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('crm_opportunities')]
        if 'sub_status' not in cols:
            if is_sqlite:
                with op.batch_alter_table('crm_opportunities') as batch_op:
                    batch_op.add_column(sa.Column('sub_status', sa.String(length=255), nullable=True))
            else:
                op.add_column('crm_opportunities', sa.Column('sub_status', sa.String(length=255), nullable=True))

    # 2. Add legacy_lifecycle_status to leads if absent
    if 'leads' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('leads')]
        if 'legacy_lifecycle_status' not in cols:
            if is_sqlite:
                with op.batch_alter_table('leads') as batch_op:
                    batch_op.add_column(sa.Column('legacy_lifecycle_status', sa.String(length=50), nullable=True))
            else:
                op.add_column('leads', sa.Column('legacy_lifecycle_status', sa.String(length=50), nullable=True))

        # 3. Preserve legacy lifecycle status for safe rollback
        op.execute(sa.text("""
            UPDATE leads
            SET legacy_lifecycle_status = lifecycle_status
            WHERE legacy_lifecycle_status IS NULL AND lifecycle_status IS NOT NULL;
        """))

        # 4. Apply approved business status mapping
        # 4a. Open leads -> Enquiry
        op.execute(sa.text("""
            UPDATE leads
            SET lifecycle_status = 'Enquiry'
            WHERE lifecycle_status = 'Open';
        """))

        # 4b. Qualified leads with Won Opportunities -> Supply
        op.execute(sa.text("""
            UPDATE leads
            SET lifecycle_status = 'Supply'
            WHERE lifecycle_status = 'Qualified'
              AND opportunity_id IN (
                  SELECT id FROM crm_opportunities WHERE status = 'Won'
              );
        """))

        # 4c. Qualified leads with Open Opportunities -> Negotiation
        op.execute(sa.text("""
            UPDATE leads
            SET lifecycle_status = 'Negotiation'
            WHERE lifecycle_status = 'Qualified'
              AND opportunity_id IN (
                  SELECT id FROM crm_opportunities WHERE status = 'Open'
              );
        """))

        # 4d. Remaining Qualified leads (no opportunity linked) -> Enquiry
        op.execute(sa.text("""
            UPDATE leads
            SET lifecycle_status = 'Enquiry'
            WHERE lifecycle_status = 'Qualified';
        """))

        # 4e. Disqualified leads -> Dormant
        op.execute(sa.text("""
            UPDATE leads
            SET lifecycle_status = 'Dormant'
            WHERE lifecycle_status = 'Disqualified';
        """))


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    # 1. Restore legacy lifecycle status
    if 'leads' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('leads')]
        if 'legacy_lifecycle_status' in cols:
            op.execute(sa.text("""
                UPDATE leads
                SET lifecycle_status = legacy_lifecycle_status
                WHERE legacy_lifecycle_status IS NOT NULL;
            """))
            if is_sqlite:
                with op.batch_alter_table('leads') as batch_op:
                    batch_op.drop_column('legacy_lifecycle_status')
            else:
                op.drop_column('leads', 'legacy_lifecycle_status')

    # 2. Drop sub_status from crm_opportunities
    if 'crm_opportunities' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('crm_opportunities')]
        if 'sub_status' in cols:
            if is_sqlite:
                with op.batch_alter_table('crm_opportunities') as batch_op:
                    batch_op.drop_column('sub_status')
            else:
                op.drop_column('crm_opportunities', 'sub_status')
