"""add_crm_lead_account_contact_tables

Revision ID: c1r2m3l4e5a6
Revises: f1a2b3c4d5e6
Create Date: 2026-10-10 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1r2m3l4e5a6'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. Accounts Table
    if "accounts" not in existing_tables:
        op.create_table(
            "accounts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("account_id", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("industry", sa.String(length=100), nullable=True),
            sa.Column("website", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_accounts_account_id"), "accounts", ["account_id"], unique=True)
        op.create_index(op.f("ix_accounts_name"), "accounts", ["name"], unique=False)

    # 2. Contacts Table
    if "contacts" not in existing_tables:
        op.create_table(
            "contacts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("contact_id", sa.String(length=50), nullable=False),
            sa.Column("account_id", sa.String(length=36), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("mobile_number", sa.String(length=50), nullable=True),
            sa.Column("designation", sa.String(length=100), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_contacts_contact_id"), "contacts", ["contact_id"], unique=True)
        op.create_index(op.f("ix_contacts_account_id"), "contacts", ["account_id"], unique=False)
        op.create_index(op.f("ix_contacts_name"), "contacts", ["name"], unique=False)
        op.create_index(op.f("ix_contacts_email"), "contacts", ["email"], unique=False)
        op.create_index(op.f("ix_contacts_mobile_number"), "contacts", ["mobile_number"], unique=False)

    # 3. Leads Table
    if "leads" not in existing_tables:
        op.create_table(
            "leads",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("lead_id", sa.String(length=50), nullable=False),
            sa.Column("lead_name", sa.String(length=255), nullable=False),
            sa.Column("website_link", sa.String(length=255), nullable=True),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column("site_name", sa.String(length=255), nullable=True),
            sa.Column("business_area", sa.String(length=50), nullable=False),
            sa.Column("requirement_type", sa.String(length=50), nullable=False),
            sa.Column("requirement_summary", sa.Text(), nullable=True),
            sa.Column("requested_product_service", sa.String(length=255), nullable=False),
            sa.Column("lead_source", sa.String(length=50), nullable=False, server_default="Website"),
            sa.Column("account_id", sa.String(length=36), nullable=True),
            sa.Column("contact_id", sa.String(length=36), nullable=False),
            sa.Column("assigned_to_user_id", sa.String(length=36), nullable=True),
            sa.Column("lifecycle_status", sa.String(length=50), nullable=False, server_default="Open"),
            sa.Column("communication_channel", sa.String(length=50), nullable=True, server_default="Email"),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.Column("next_follow_up_date", sa.DateTime(), nullable=True),
            sa.Column("next_follow_up_action", sa.Text(), nullable=True),
            sa.Column("last_connected_date", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.String(length=36), nullable=True),
            sa.Column("updated_by_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_leads_lead_id"), "leads", ["lead_id"], unique=True)
        op.create_index(op.f("ix_leads_lead_name"), "leads", ["lead_name"], unique=False)
        op.create_index(op.f("ix_leads_account_id"), "leads", ["account_id"], unique=False)
        op.create_index(op.f("ix_leads_contact_id"), "leads", ["contact_id"], unique=False)
        op.create_index(op.f("ix_leads_assigned_to_user_id"), "leads", ["assigned_to_user_id"], unique=False)
        op.create_index(op.f("ix_leads_lifecycle_status"), "leads", ["lifecycle_status"], unique=False)
        op.create_index(op.f("ix_leads_requested_product_service"), "leads", ["requested_product_service"], unique=False)
        op.create_index(op.f("ix_leads_next_follow_up_date"), "leads", ["next_follow_up_date"], unique=False)
        op.create_index(op.f("ix_leads_created_at"), "leads", ["created_at"], unique=False)
        op.create_index("ix_leads_lifecycle_followup", "leads", ["lifecycle_status", "next_follow_up_date"], unique=False)
        op.create_index("ix_leads_account_product", "leads", ["account_id", "requested_product_service"], unique=False)
        op.create_index("ix_leads_contact_product", "leads", ["contact_id", "requested_product_service"], unique=False)

    # 4. Lead Communication History Table
    if "lead_communications" not in existing_tables:
        op.create_table(
            "lead_communications",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("communication_id", sa.String(length=50), nullable=False),
            sa.Column("lead_id", sa.String(length=36), nullable=False),
            sa.Column("communication_date", sa.DateTime(), nullable=False),
            sa.Column("channel", sa.String(length=50), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("outcome", sa.Text(), nullable=True),
            sa.Column("next_action", sa.Text(), nullable=True),
            sa.Column("follow_up_date", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_lead_communications_communication_id"), "lead_communications", ["communication_id"], unique=True)
        op.create_index(op.f("ix_lead_communications_lead_id"), "lead_communications", ["lead_id"], unique=False)
        op.create_index(op.f("ix_lead_communications_communication_date"), "lead_communications", ["communication_date"], unique=False)

    # 5. CRM Sequences Table
    if "crm_sequences" not in existing_tables:
        op.create_table(
            "crm_sequences",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("entity_name", sa.String(length=50), nullable=False),
            sa.Column("current_value", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_crm_sequences_entity_name"), "crm_sequences", ["entity_name"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if "lead_communications" in existing_tables:
        op.drop_table("lead_communications")
    if "leads" in existing_tables:
        op.drop_table("leads")
    if "contacts" in existing_tables:
        op.drop_table("contacts")
    if "accounts" in existing_tables:
        op.drop_table("accounts")
    if "crm_sequences" in existing_tables:
        op.drop_table("crm_sequences")
