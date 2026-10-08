"""add_missing_user_fields

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-10-08 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. Ensure centralized module tables exist if not already present
    if "modules" not in existing_tables:
        op.create_table(
            "modules",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_open_to_all", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_modules_code"), "modules", ["code"], unique=True)

    if "module_roles" not in existing_tables:
        op.create_table(
            "module_roles",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("module_id", sa.String(length=36), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("module_id", "code", name="uq_module_role_code"),
        )
        op.create_index(op.f("ix_module_roles_code"), "module_roles", ["code"], unique=False)

    if "module_role_permissions" not in existing_tables:
        op.create_table(
            "module_role_permissions",
            sa.Column("module_role_id", sa.String(length=36), nullable=False),
            sa.Column("permission_id", sa.String(length=36), nullable=False),
            sa.ForeignKeyConstraint(["module_role_id"], ["module_roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("module_role_id", "permission_id"),
        )

    if "user_module_memberships" not in existing_tables:
        op.create_table(
            "user_module_memberships",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("module_id", sa.String(length=36), nullable=False),
            sa.Column("role_id", sa.String(length=36), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["module_roles.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "module_id", name="uq_user_module_membership"),
        )

    # 2. Add missing fields to users table safely
    user_columns = {c["name"] for c in insp.get_columns("users")}

    # Phase A: Add columns temporarily nullable or with default
    if "name" not in user_columns:
        op.add_column("users", sa.Column("name", sa.String(length=150), nullable=True, server_default=""))

    if "phone" not in user_columns:
        op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True, server_default=""))

    if "manager_id" not in user_columns:
        op.add_column("users", sa.Column("manager_id", sa.String(length=36), nullable=True))
        # Add foreign key constraint if not present
        existing_fks = {fk.get("name") for fk in insp.get_foreign_keys("users")}
        if "fk_users_manager_id_users" not in existing_fks:
            op.create_foreign_key(
                "fk_users_manager_id_users",
                "users",
                "users",
                ["manager_id"],
                ["id"],
                ondelete="SET NULL"
            )

    # Phase B: Populate data for existing rows from employees table if linked
    if "employees" in existing_tables:
        emp_cols = {c["name"] for c in insp.get_columns("employees")}
        if "user_id" in emp_cols and "name" in emp_cols and "phone" in emp_cols:
            emp_rows = bind.execute(sa.text("SELECT user_id, name, phone FROM employees")).fetchall()
            for row in emp_rows:
                u_id, emp_name, emp_phone = row[0], row[1], row[2]
                if u_id:
                    bind.execute(
                        sa.text("UPDATE users SET name = :name WHERE id = :id AND (name IS NULL OR name = '')"),
                        {"name": emp_name or "", "id": u_id}
                    )
                    if emp_phone:
                        bind.execute(
                            sa.text("UPDATE users SET phone = :phone WHERE id = :id AND (phone IS NULL OR phone = '')"),
                            {"phone": emp_phone, "id": u_id}
                        )

    # Ensure no NULL or empty name remains for any user (fallback to username)
    bind.execute(sa.text("UPDATE users SET name = username WHERE name IS NULL OR name = ''"))
    bind.execute(sa.text("UPDATE users SET phone = '' WHERE phone IS NULL"))

    # Phase C: Alter columns to final NOT NULL constraint matching User model
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=150),
            nullable=False,
            server_default=""
        )
        batch_op.alter_column(
            "phone",
            existing_type=sa.String(length=50),
            nullable=False,
            server_default=""
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    user_columns = {c["name"] for c in insp.get_columns("users")}

    if "manager_id" in user_columns:
        with op.batch_alter_table("users") as batch_op:
            try:
                batch_op.drop_constraint("fk_users_manager_id_users", type_="foreignkey")
            except Exception:
                pass
            batch_op.drop_column("manager_id")

    if "phone" in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("phone")

    if "name" in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("name")
