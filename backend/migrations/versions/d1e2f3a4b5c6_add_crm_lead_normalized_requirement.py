"""add crm lead normalized requirement and partial unique indexes

Revision ID: d1e2f3a4b5c6
Revises: c1r2m3l4e5a6
Create Date: 2026-10-10 22:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c1r2m3l4e5a6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    lead_columns = [c["name"] for c in inspector.get_columns("leads")]

    if "normalized_requirement" not in lead_columns:
        op.add_column("leads", sa.Column("normalized_requirement", sa.String(length=255), nullable=True))
        # Backfill existing rows if any
        bind.execute(sa.text("UPDATE leads SET normalized_requirement = lower(trim(requested_product_service)) WHERE normalized_requirement IS NULL"))

    existing_indices = [idx["name"] for idx in inspector.get_indexes("leads")]

    if "ix_leads_normalized_requirement" not in existing_indices:
        op.create_index("ix_leads_normalized_requirement", "leads", ["normalized_requirement"], unique=False)

    where_acc = sa.text("lifecycle_status = 'Open' AND account_id IS NOT NULL")
    if "uq_open_lead_account_product" not in existing_indices:
        op.create_index(
            "uq_open_lead_account_product",
            "leads",
            ["account_id", "normalized_requirement"],
            unique=True,
            postgresql_where=where_acc,
            sqlite_where=where_acc
        )

    where_contact = sa.text("lifecycle_status = 'Open' AND account_id IS NULL")
    if "uq_open_lead_contact_product" not in existing_indices:
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
    existing_indices = [idx["name"] for idx in inspector.get_indexes("leads")]

    if "uq_open_lead_contact_product" in existing_indices:
        op.drop_index("uq_open_lead_contact_product", table_name="leads")
    if "uq_open_lead_account_product" in existing_indices:
        op.drop_index("uq_open_lead_account_product", table_name="leads")
    if "ix_leads_normalized_requirement" in existing_indices:
        op.drop_index("ix_leads_normalized_requirement", table_name="leads")

    lead_columns = [c["name"] for c in inspector.get_columns("leads")]
    if "normalized_requirement" in lead_columns:
        op.drop_column("leads", "normalized_requirement")
