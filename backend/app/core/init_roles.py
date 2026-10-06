import logging
from app.core.database import SessionLocal
import app.models  # noqa: F401 ensures all models and table mappers are loaded
from app.roles.model import Role, Permission
from app.users.model import User

logger = logging.getLogger("revy.breakfast")

def ensure_roles_and_permissions():
    """
    Ensure the DIRECTOR_ANALYTICS role, orders permission, and updated
    CEO / Finance Manager role assignments exist in the database without
    affecting existing user accounts.
    """
    db = SessionLocal()
    try:
        # 1. Ensure permissions
        orders_perm = db.query(Permission).filter(Permission.code == "breakfast.orders.view").first()
        if not orders_perm:
            orders_perm = Permission(
                code="breakfast.orders.view",
                name="View All Breakfast Orders",
                module="BREAKFAST",
                description="View all company breakfast orders and order history"
            )
            db.add(orders_perm)
            db.flush()

        dash_perm = db.query(Permission).filter(Permission.code == "breakfast.dashboard.view").first()
        if not dash_perm:
            dash_perm = Permission(
                code="breakfast.dashboard.view",
                name="View Director Analytics Dashboard",
                module="BREAKFAST",
                description="Executive view of summary analytics"
            )
            db.add(dash_perm)
            db.flush()
        else:
            dash_perm.name = "View Director Analytics Dashboard"

        report_perm = db.query(Permission).filter(Permission.code == "breakfast.report").first()
        if not report_perm:
            report_perm = Permission(
                code="breakfast.report",
                name="Generate Breakfast Reports",
                module="BREAKFAST",
                description="Access daily and monthly reports"
            )
            db.add(report_perm)
            db.flush()

        # 2. Ensure DIRECTOR_ANALYTICS role
        dir_role = db.query(Role).filter(Role.code == "DIRECTOR_ANALYTICS").first()
        if not dir_role:
            dir_role = Role(
                code="DIRECTOR_ANALYTICS",
                name="Director Analytics",
                description="Executive Director Analytics dashboard and management insights"
            )
            db.add(dir_role)
            db.flush()

        dir_perms = [p for p in [dash_perm] if p]
        for code in ["breakfast.view_own", "breakfast.submit", "breakfast.history_own"]:
            p = db.query(Permission).filter(Permission.code == code).first()
            if p and p not in dir_perms:
                dir_perms.append(p)
        dir_role.permissions = dir_perms

        # 3. Update CEO role permissions:
        # - Remove breakfast.dashboard.view (Director Analytics is restricted to DIRECTOR_ANALYTICS role)
        # - Add breakfast.orders.view (CEO can view all orders across all employees)
        ceo_role = db.query(Role).filter(Role.code == "CEO").first()
        if ceo_role:
            ceo_perms = [p for p in ceo_role.permissions if p.code != "breakfast.dashboard.view"]
            if orders_perm and not any(p.code == "breakfast.orders.view" for p in ceo_perms):
                ceo_perms.append(orders_perm)
            ceo_role.permissions = ceo_perms

        # 4. Update FINANCE_MANAGER role permissions:
        # - Ensure breakfast.report is present for full reports viewing and downloading
        fin_role = db.query(Role).filter(Role.code == "FINANCE_MANAGER").first()
        if fin_role:
            fin_perms = list(fin_role.permissions)
            if report_perm and not any(p.code == "breakfast.report" for p in fin_perms):
                fin_perms.append(report_perm)
            fin_role.permissions = fin_perms

        db.commit()
        logger.info("Successfully verified and synced RBAC roles and permissions (DIRECTOR_ANALYTICS, CEO, FINANCE_MANAGER).")
    except Exception as e:
        db.rollback()
        logger.warning(f"ensure_roles_and_permissions note: {e}")
    finally:
        db.close()
