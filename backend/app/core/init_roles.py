import logging
from app.core.database import SessionLocal
import app.models  # noqa: F401 ensures all models and table mappers are loaded
from app.roles.model import Role, Permission
from app.users.model import User

logger = logging.getLogger("revy.roles")

def ensure_roles_and_permissions():
    """
    Centralized Global Roles Setup:
    Ensures that only the two designated system-wide global roles exist in the roles table:
      1. IT_ADMIN (IT Admin)
      2. DIRECTOR (Director) - Migrated from legacy CEO
    Both global roles are granted unrestricted system access (*).
    Optimized with batch queries for sub-second execution.
    """
    db = SessionLocal()
    try:
        # 1. Fetch all existing permissions in one query
        existing_perms = {p.code: p for p in db.query(Permission).all()}

        # Ensure '*' superadmin permission exists
        if "*" not in existing_perms:
            star_perm = Permission(
                code="*",
                name="Full Administrative Access",
                module="PLATFORM",
                description="Unrestricted system-wide access"
            )
            db.add(star_perm)
            db.flush()
            existing_perms["*"] = star_perm

        standard_permissions = [
            ("breakfast.view_own", "View Own Breakfast Status", "BREAKFAST"),
            ("breakfast.submit", "Submit Daily Breakfast Status", "BREAKFAST"),
            ("breakfast.history_own", "View Own Breakfast History", "BREAKFAST"),
            ("breakfast.view", "View All Breakfast Status", "BREAKFAST"),
            ("breakfast.manage", "Manage Daily Breakfast Operations", "BREAKFAST"),
            ("breakfast.report", "Generate Breakfast Reports", "BREAKFAST"),
            ("breakfast.orders.view", "View All Breakfast Orders", "BREAKFAST"),
            ("breakfast.dashboard.view", "View Director Dashboard", "BREAKFAST"),
            ("breakfast.employee.create", "Create Employees", "BREAKFAST"),
            ("breakfast.employee.read", "Read Employee Records", "BREAKFAST"),
            ("breakfast.employee.update", "Update Employee Records", "BREAKFAST"),
            ("breakfast.employee.deactivate", "Deactivate Employees", "BREAKFAST"),
            ("breakfast.holiday.manage", "Manage Public Holidays", "BREAKFAST"),
            ("breakfast.settings.manage", "Manage System Settings", "BREAKFAST"),
            ("breakfast.money.view", "View Breakfast Money Ledger", "MONEY"),
            ("breakfast.money.request", "Request Breakfast Money", "MONEY"),
            ("breakfast.money.receive", "Receive Money from Finance", "MONEY"),
            ("breakfast.money.receipt.verify", "Verify Money Receipt", "MONEY"),
            ("breakfast.money.expense.view", "View Breakfast Expenses", "MONEY"),
            ("breakfast.money.expense.create", "Record Breakfast Expenses", "MONEY"),
            ("breakfast.money.adjust", "Adjust Money Ledger", "MONEY"),
            ("breakfast.money.report", "Generate Money Statements", "MONEY"),
            ("breakfast.actual_status.override", "Override Employee Actual Status", "BREAKFAST"),
            ("breakfast.audit.view", "View Audit Logs", "AUDIT"),
            ("finance.breakfast_fund.view", "View Finance Breakfast Fund Dashboard", "FINANCE"),
            ("finance.breakfast_fund.request.view", "View Fund Requests", "FINANCE"),
            ("finance.breakfast_fund.request.approve", "Approve Fund Requests", "FINANCE"),
            ("finance.breakfast_fund.request.reject", "Reject Fund Requests", "FINANCE"),
            ("finance.breakfast_fund.provide", "Provide Money for Fund Request", "FINANCE"),
            ("finance.breakfast_fund.report", "Finance Fund Reports", "FINANCE"),
            ("users.view", "View Users", "USERS"),
            ("users.create", "Create Users", "USERS"),
            ("users.edit", "Edit Users", "USERS"),
            ("users.deactivate", "Deactivate Users", "USERS"),
            ("user.password.reset", "Reset User Passwords", "PLATFORM"),
        ]

        for code, name, mod in standard_permissions:
            if code not in existing_perms:
                p = Permission(code=code, name=name, module=mod, description=name)
                db.add(p)
                db.flush()
                existing_perms[code] = p

        all_perms_list = list(existing_perms.values())

        # 2. Fetch existing roles
        roles_by_code = {r.code: r for r in db.query(Role).all()}

        # Ensure IT_ADMIN Global Role
        it_role = roles_by_code.get("IT_ADMIN")
        if not it_role:
            it_role = Role(
                code="IT_ADMIN",
                name="IT Admin",
                description="Global IT Administrator with full unrestricted access across all modules"
            )
            db.add(it_role)
            db.flush()
            roles_by_code["IT_ADMIN"] = it_role
        else:
            it_role.name = "IT Admin"
            it_role.description = "Global IT Administrator with full unrestricted access across all modules"
        it_role.permissions = all_perms_list

        # 3. Handle Migration: CEO -> DIRECTOR
        dir_role = roles_by_code.get("DIRECTOR")
        ceo_role = roles_by_code.get("CEO")

        if not dir_role:
            if ceo_role:
                ceo_role.code = "DIRECTOR"
                ceo_role.name = "Director"
                ceo_role.description = "Global Executive Director with full unrestricted access across all modules"
                dir_role = ceo_role
            else:
                dir_role = Role(
                    code="DIRECTOR",
                    name="Director",
                    description="Global Executive Director with full unrestricted access across all modules"
                )
                db.add(dir_role)
                db.flush()
        else:
            dir_role.name = "Director"
            dir_role.description = "Global Executive Director with full unrestricted access across all modules"
            if ceo_role and ceo_role.id != dir_role.id:
                for u in list(ceo_role.users):
                    if dir_role not in u.roles:
                        u.roles.append(dir_role)
                ceo_role.users = []
                ceo_role.permissions = []
                db.delete(ceo_role)

        dir_role.permissions = all_perms_list

        db.commit()
        logger.info("Successfully synced Global System Roles (IT Admin, Director) with full unrestricted access.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error in ensure_roles_and_permissions: {e}", exc_info=True)
        raise
    finally:
        db.close()
