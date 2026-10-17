"""make requested_product_service optional, next_follow_up_date date-only, and update partial indexes

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-10-13 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    # 1. Alter requested_product_service to nullable=True on leads
    if not is_sqlite:
        op.alter_column('leads', 'requested_product_service', existing_type=sa.String(length=255), nullable=True)
        # 2. Alter next_follow_up_date to DATE on leads
        op.execute(sa.text("ALTER TABLE leads ALTER COLUMN next_follow_up_date TYPE DATE USING (next_follow_up_date::date)"))
        # 3. Alter follow_up_date to DATE on lead_communications
        op.execute(sa.text("ALTER TABLE lead_communications ALTER COLUMN follow_up_date TYPE DATE USING (follow_up_date::date)"))
    
    # 4. Update partial unique indexes to only apply when normalized_requirement IS NOT NULL
    existing_indices = [idx["name"] for idx in inspector.get_indexes("leads")]

    if "uq_open_lead_account_product" in existing_indices:
        op.drop_index("uq_open_lead_account_product", table_name="leads")
    
    if "uq_open_lead_contact_product" in existing_indices:
        op.drop_index("uq_open_lead_contact_product", table_name="leads")

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


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_indices = [idx["name"] for idx in inspector.get_indexes("leads")]

    if "uq_open_lead_contact_product" in existing_indices:
        op.drop_index("uq_open_lead_contact_product", table_name="leads")
    if "uq_open_lead_account_product" in existing_indices:
        op.drop_index("uq_open_lead_account_product", table_name="leads")

    where_acc = sa.text("lifecycle_status = 'Open' AND account_id IS NOT NULL")
    op.create_index(
        "uq_open_lead_account_product",
        "leads",
        ["account_id", "normalized_requirement"],
        unique=True,
        postgresql_where=where_acc,
        sqlite_where=where_acc
    )

    where_contact = sa.text("lifecycle_status = 'Open' AND account_id IS NULL")
    op.create_index(
        "uq_open_lead_contact_product",
        "leads",
        ["contact_id", "normalized_requirement"],
        unique=True,
        postgresql_where=where_contact,
        sqlite_where=where_contact
    )

    if not is_sqlite:
        op.execute(sa.text("ALTER TABLE lead_communications ALTER COLUMN follow_up_date TYPE TIMESTAMP WITHOUT TIME ZONE USING (follow_up_date::timestamp)"))
        op.execute(sa.text("ALTER TABLE leads ALTER COLUMN next_follow_up_date TYPE TIMESTAMP WITHOUT TIME ZONE USING (next_follow_up_date::timestamp)"))
        op.alter_column('leads', 'requested_product_service', existing_type=sa.String(length=255), nullable=False)
