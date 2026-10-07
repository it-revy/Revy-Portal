import logging
from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base
import app.models  # Ensures all models and tables are registered
from app.users.model import User
from app.employees.model import Employee
from app.modules.model import Module, ModuleRole, UserModuleMembership

logger = logging.getLogger("revy.modules")

def ensure_modules_and_memberships():
    """
    Ensures new database columns on users, creates module tables, seeds
    standard modules (BMS, LMS, CRM, MIS, DWR, REPORTS) and module-scoped roles,
    populates User name/phone from Employee, and grants BMS membership to all
    existing employees so zero data or access is lost.
    """
    # 1. Run direct ALTER TABLE statements to add columns to users table safely if missing
    with engine.connect() as conn:
        with conn.begin():
            # Check and add name to users
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'name'
                    ) THEN
                        ALTER TABLE users ADD COLUMN name VARCHAR(150) DEFAULT '' NOT NULL;
                    END IF;
                END $$;
            """))

            # Check and add phone to users
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'phone'
                    ) THEN
                        ALTER TABLE users ADD COLUMN phone VARCHAR(50) DEFAULT '' NOT NULL;
                    END IF;
                END $$;
            """))

            # Check and add manager_id to users
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'manager_id'
                    ) THEN
                        ALTER TABLE users ADD COLUMN manager_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;
                    END IF;
                END $$;
            """))

    # 2. Ensure all tables are created (modules, module_roles, user_module_memberships)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 3. Define Standard Modules
        modules_data = [
            {
                "code": "BMS",
                "name": "Breakfast Management System",
                "description": "Daily meal attendance, catering orders, cutoff enforcement, and authoritative money ledger.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "LMS",
                "name": "Laboratory Management System",
                "description": "Environmental sample tracking, biological/chemical test workflows, QA/QC audits, and digital lab certificates.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "CRM",
                "name": "Customer Relationship Management",
                "description": "Client accounts, lead pipeline, sales tracking, and customer communications.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "MIS",
                "name": "Management Information System",
                "description": "Executive analytics, operational metrics, cross-department dashboards, and high-level KPIs.",
                "is_active": True,
                "is_open_to_all": True
            },
            {
                "code": "DWR",
                "name": "Daily Work Report",
                "description": "Daily task logging, on-site project activities, progress reporting, and manager sign-off workflows.",
                "is_active": True,
                "is_open_to_all": True
            },
            {
                "code": "REPORTS",
                "name": "Statutory & Audit Reports",
                "description": "Consolidated statutory reports, platform audit trail analysis, compliance reports, and multi-format data exports.",
                "is_active": True,
                "is_open_to_all": True
            }
        ]

        modules_by_code = {}
        for m_data in modules_data:
            mod = db.query(Module).filter(Module.code == m_data["code"]).first()
            if not mod:
                mod = Module(**m_data)
                db.add(mod)
                db.flush()
                logger.info(f"Created module: {mod.code}")
            else:
                mod.name = m_data["name"]
                mod.description = m_data["description"]
                mod.is_active = m_data["is_active"]
                mod.is_open_to_all = m_data["is_open_to_all"]
            modules_by_code[mod.code] = mod

        # 4. Define Module-Scoped Roles
        roles_data = [
            # BMS Roles
            {"module_code": "BMS", "code": "BMS_ADMIN", "name": "BMS Administrator", "description": "Full administration of BMS operations, menus, and attendance."},
            {"module_code": "BMS", "code": "BMS_MANAGER", "name": "BMS Manager", "description": "Operational oversight and review of breakfast records."},
            {"module_code": "BMS", "code": "BMS_FINANCE", "name": "BMS Finance", "description": "Financial ledger management and fund requests in BMS."},
            {"module_code": "BMS", "code": "BMS_EMPLOYEE", "name": "BMS Employee", "description": "Daily breakfast taker and individual meal requests."},
            {"module_code": "BMS", "code": "BMS_VIEWER", "name": "BMS Viewer", "description": "Read-only access to breakfast entries and statistics."},
            # CRM Roles
            {"module_code": "CRM", "code": "CRM_ADMIN", "name": "CRM Administrator", "description": "Full administrative control over CRM configurations and leads."},
            {"module_code": "CRM", "code": "SALES_MANAGER", "name": "Sales Manager", "description": "Team lead managing client accounts and sales pipelines."},
            {"module_code": "CRM", "code": "SALES_EXECUTIVE", "name": "Sales Executive", "description": "Field sales, customer follow-ups, and quotation management."},
            # LMS Roles
            {"module_code": "LMS", "code": "LMS_ADMIN", "name": "LMS Administrator", "description": "Laboratory system management and protocol configuration."},
            {"module_code": "LMS", "code": "LAB_TECHNICIAN", "name": "Lab Technician", "description": "Sample processing and laboratory result entry."},
            {"module_code": "LMS", "code": "QA_QC_MANAGER", "name": "QA/QC Manager", "description": "Quality assurance and lab certificate verification."}
        ]

        roles_by_module_and_code = {}
        for r_data in roles_data:
            mod = modules_by_code.get(r_data["module_code"])
            if not mod:
                continue
            r = db.query(ModuleRole).filter(
                ModuleRole.module_id == mod.id,
                ModuleRole.code == r_data["code"]
            ).first()
            if not r:
                r = ModuleRole(
                    module_id=mod.id,
                    code=r_data["code"],
                    name=r_data["name"],
                    description=r_data["description"]
                )
                db.add(r)
                db.flush()
                logger.info(f"Created module role: {mod.code} -> {r.code}")
            else:
                r.name = r_data["name"]
                r.description = r_data["description"]
            roles_by_module_and_code[(mod.code, r.code)] = r

        # 5. Populate User name & phone from Employee records
        users = db.query(User).all()
        for u in users:
            if u.employee:
                if not u.name:
                    u.name = u.employee.name or u.username
                if not u.phone:
                    u.phone = u.employee.phone or ""
            elif not u.name:
                u.name = u.username

        # 6. Migrate existing employees to BMS Module Membership
        bms_mod = modules_by_code.get("BMS")
        if bms_mod:
            for u in users:
                if u.employee:
                    # Determine appropriate BMS role based on user's current global roles
                    user_role_codes = [r.code for r in u.roles]
                    target_bms_role_code = "BMS_EMPLOYEE"
                    if "IT_ADMIN" in user_role_codes or "BREAKFAST_ADMIN" in user_role_codes:
                        target_bms_role_code = "BMS_ADMIN"
                    elif "FINANCE_MANAGER" in user_role_codes:
                        target_bms_role_code = "BMS_FINANCE"
                    elif "CEO" in user_role_codes or "DIRECTOR_ANALYTICS" in user_role_codes:
                        target_bms_role_code = "BMS_VIEWER"

                    assigned_role = roles_by_module_and_code.get(("BMS", target_bms_role_code))
                    existing_membership = db.query(UserModuleMembership).filter(
                        UserModuleMembership.user_id == u.id,
                        UserModuleMembership.module_id == bms_mod.id
                    ).first()

                    if not existing_membership:
                        membership = UserModuleMembership(
                            user_id=u.id,
                            module_id=bms_mod.id,
                            role_id=assigned_role.id if assigned_role else None,
                            is_active=True
                        )
                        db.add(membership)
                        logger.info(f"Granted BMS membership to {u.username} with role {target_bms_role_code}")

        db.commit()
        logger.info("Successfully initialized modules, module roles, and migrated existing user memberships.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during ensure_modules_and_memberships: {e}", exc_info=True)
        raise
    finally:
        db.close()
