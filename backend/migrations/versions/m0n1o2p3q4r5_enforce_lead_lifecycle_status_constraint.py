"""enforce_lead_lifecycle_status_constraint

Revision ID: m0n1o2p3q4r5
Revises: l9m0n1o2p3q4
Create Date: 2026-10-27 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'm0n1o2p3q4r5'
down_revision = 'l9m0n1o2p3q4'
branch_labels = None
depends_on = None

TARGET_TEST_LEAD_IDS = (
    '1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1',
    'f18ea315-eed4-4bbe-a4de-ab3dfb8a3d20'
)

APPROVED_STATUSES = (
    'Enquiry',
    'Offer',
    'Negotiation',
    'Supply',
    'Payment',
    'Dormant'
)


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    if 'leads' not in existing_tables:
        return

    # 1. Precondition Check A: Verify targeted test leads if present
    # Check if target test leads exist in the database (they exist in Neon)
    target_check = bind.execute(sa.text("""
        SELECT id, lead_id, lifecycle_status, opportunity_id, account_id, contact_id
        FROM leads
        WHERE id IN ('1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1', 'f18ea315-eed4-4bbe-a4de-ab3dfb8a3d20')
    """)).fetchall()

    if target_check:
        for row in target_check:
            lid = str(row[0])
            code = row[1]
            status = row[2]
            if status != 'Open' and status not in APPROVED_STATUSES:
                raise RuntimeError(
                    f"Precondition failed: Target test lead {lid} ({code}) has unexpected status '{status}'."
                )

    # 2. Precondition Check B: Verify that NO other rows contain unapproved statuses
    unapproved_query = sa.text("""
        SELECT id, lead_id, lifecycle_status
        FROM leads
        WHERE id NOT IN ('1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1', 'f18ea315-eed4-4bbe-a4de-ab3dfb8a3d20')
          AND lifecycle_status NOT IN ('Enquiry', 'Offer', 'Negotiation', 'Supply', 'Payment', 'Dormant')
    """)
    unapproved_rows = bind.execute(unapproved_query).fetchall()
    if unapproved_rows:
        rows_summary = ", ".join([f"{r[1]}: '{r[2]}'" for r in unapproved_rows])
        raise RuntimeError(
            f"Precondition failed: Found unexpected unapproved lead statuses in production data: {rows_summary}. "
            "Aborting migration without modifying data."
        )

    # 3. Update only the two verified test leads from Open to Enquiry
    op.execute(sa.text("""
        UPDATE leads
        SET lifecycle_status = 'Enquiry'
        WHERE id IN ('1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1', 'f18ea315-eed4-4bbe-a4de-ab3dfb8a3d20')
          AND lifecycle_status = 'Open';
    """))

    # 4. Change database column default from 'Open' to 'Enquiry'
    if is_sqlite:
        with op.batch_alter_table('leads') as batch_op:
            batch_op.alter_column('lifecycle_status', server_default='Enquiry')
    else:
        op.alter_column('leads', 'lifecycle_status', server_default='Enquiry')

    # 5. Add PostgreSQL CHECK constraint ck_leads_lifecycle_status
    status_list_sql = ", ".join([f"'{s}'" for s in APPROVED_STATUSES])
    check_expr = f"lifecycle_status IN ({status_list_sql})"

    if is_sqlite:
        with op.batch_alter_table('leads') as batch_op:
            batch_op.create_check_constraint('ck_leads_lifecycle_status', check_expr)
    else:
        op.create_check_constraint(
            'ck_leads_lifecycle_status',
            'leads',
            check_expr
        )


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    if 'leads' not in existing_tables:
        return

    # 1. Drop CHECK constraint
    if is_sqlite:
        with op.batch_alter_table('leads') as batch_op:
            batch_op.drop_constraint('ck_leads_lifecycle_status', type_='check')
    else:
        op.drop_constraint('ck_leads_lifecycle_status', 'leads', type_='check')

    # 2. Restore column default to 'Open'
    if is_sqlite:
        with op.batch_alter_table('leads') as batch_op:
            batch_op.alter_column('lifecycle_status', server_default='Open')
    else:
        op.alter_column('leads', 'lifecycle_status', server_default='Open')
