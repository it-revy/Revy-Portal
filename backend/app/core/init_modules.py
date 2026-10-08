import logging
from app.core.database import SessionLocal, engine, Base
import app.models  # Ensures all models and tables are registered
from app.users.model import User
from app.employees.model import Employee
from app.roles.model import Role, Permission
from app.modules.model import Module, ModuleRole, UserModuleMembership

logger = logging.getLogger("revy.modules")

def ensure_modules_and_memberships():
    """
    Centralized Module & Module-Role Initialization:
    1. Creates module tables and module_role_permissions table.
    2. Seeds the 9 authoritative modules (MIS, BMS, CRM, LMS, IMS, LEAVE, USERS, DWR, REPORTS).
    3. Seeds module-scoped roles with the standard naming convention (Module Prefix + Role Name).
    4. Maps module permissions directly to module roles.
    5. Migrates existing users and legacy global BMS roles into module-specific roles.
    Optimized with batch fetching for lightning-fast execution.
    """
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Batch load existing modules
        existing_modules = {m.code: m for m in db.query(Module).all()}

        modules_data = [
            {
                "code": "MIS",
                "name": "MIS",
                "description": "Management Information System — Executive analytics and corporate KPIs.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "BMS",
                "name": "Breakfast Management System",
                "description": "Daily meal attendance, catering orders, cutoff enforcement, and authoritative money ledger.",
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
                "code": "LMS",
                "name": "Laboratory Management System",
                "description": "Environmental sample tracking, biological/chemical test workflows, QA/QC audits, and digital lab certificates.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "IMS",
                "name": "Inventory Management System",
                "description": "Track plant materials, lab consumables, hardware inventory, real-time stock alerts, and procurement requisitions.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "LEAVE",
                "name": "Leave Management",
                "description": "Employee leave requests, manager approvals, vacation balance tracking, and corporate attendance calendar.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "USERS",
                "name": "User Management",
                "description": "User identities, reporting manager hierarchies, and module access control.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "DWR",
                "name": "Daily Work Report",
                "description": "Daily task logging, on-site project activities, progress reporting, and manager sign-off workflows.",
                "is_active": True,
                "is_open_to_all": False
            },
            {
                "code": "REPORTS",
                "name": "Reports",
                "description": "Consolidated statutory reports, platform audit trail analysis, compliance reports, and multi-format data exports.",
                "is_active": True,
                "is_open_to_all": False
            }
        ]

        modules_by_code = {}
        for m_data in modules_data:
            mod = existing_modules.get(m_data["code"])
            if not mod:
                mod = Module(**m_data)
                db.add(mod)
                db.flush()
                existing_modules[mod.code] = mod
            else:
                mod.name = m_data["name"]
                mod.description = m_data["description"]
                mod.is_active = m_data["is_active"]
                mod.is_open_to_all = m_data["is_open_to_all"]
            modules_by_code[mod.code] = mod

        # 2. Batch load existing module roles
        existing_module_roles = {(r.module_id, r.code): r for r in db.query(ModuleRole).all()}

        roles_data = [
            # --- MIS Roles ---
            {"module_code": "MIS", "code": "MIS_ADMIN", "name": "MIS Admin", "description": "Full administrative access to MIS."},

            # --- BMS Roles ---
            {"module_code": "BMS", "code": "BMS_ADMIN", "name": "BMS Admin", "description": "Full access to BMS operations, daily entry, employees, money, reports, and settings."},
            {"module_code": "BMS", "code": "BMS_EMPLOYEE", "name": "BMS Employee", "description": "Employee-level BMS access to submit and view daily breakfast status."},
            {"module_code": "BMS", "code": "BMS_FINANCE_MANAGER", "name": "BMS Finance Manager", "description": "Finance-related BMS access to funds, ledgers, and approval workflows."},
            {"module_code": "BMS", "code": "BMS_DIRECTOR_ANALYTICS", "name": "BMS Director Analytics", "description": "Director/analytics-related BMS access to executive dashboards and order insights."},

            # --- CRM Roles ---
            {"module_code": "CRM", "code": "CRM_ADMIN", "name": "CRM Admin", "description": "Full administrative control over CRM configurations and leads."},
            {"module_code": "CRM", "code": "CRM_SALES_MANAGER", "name": "CRM Sales Manager", "description": "Sales team management, pipelines, and account allocations."},
            {"module_code": "CRM", "code": "CRM_SALES_EXECUTIVE", "name": "CRM Sales Executive", "description": "Field sales, customer follow-ups, and quotation management."},
            {"module_code": "CRM", "code": "CRM_SALES_COORDINATOR", "name": "CRM Sales Coordinator", "description": "Sales coordination, proposal scheduling, and client support."},
            {"module_code": "CRM", "code": "CRM_FINANCE_MANAGER", "name": "CRM Finance Manager", "description": "Financial oversight, invoicing, and revenue tracking in CRM."},

            # --- LMS Roles ---
            {"module_code": "LMS", "code": "LMS_ADMIN", "name": "LMS Admin", "description": "Full administrative management of Laboratory System protocols and configurations."},
            {"module_code": "LMS", "code": "LMS_RD_HEAD", "name": "LMS R&D Head", "description": "Research and Development head oversight of lab experiments and methods."},
            {"module_code": "LMS", "code": "LMS_SUPERVISOR", "name": "LMS Supervisor", "description": "Lab supervisor oversight, batch reviews, and sample sign-offs."},
            {"module_code": "LMS", "code": "LMS_TEAM", "name": "LMS Team", "description": "Lab testing team member, sample entry, and test execution."},

            # --- IMS Roles ---
            {"module_code": "IMS", "code": "IMS_ADMIN", "name": "IMS Admin", "description": "Full administrative control of Inventory Management System."},
            {"module_code": "IMS", "code": "IMS_INVENTORY_MANAGER", "name": "IMS Inventory Manager", "description": "Stock inventory oversight, warehouse transfers, and procurement."},
            {"module_code": "IMS", "code": "IMS_STORE_EXECUTIVE", "name": "IMS Store Executive", "description": "Material receipt, store issuance, and inventory count audits."},

            # --- Leave Management Roles ---
            {"module_code": "LEAVE", "code": "LEAVE_ADMIN", "name": "Leave Management Admin", "description": "Full administrative control over leave policies, calendars, and approvals."},

            # --- User Management Roles ---
            {"module_code": "USERS", "code": "USER_MANAGEMENT_ADMIN", "name": "User Management Admin", "description": "Full administrative control over user accounts, managers, and module assignments."},

            # --- DWR Roles ---
            {"module_code": "DWR", "code": "DWR_ADMIN", "name": "DWR Admin", "description": "Full administrative access to Daily Work Report management."},

            # --- Reports Roles ---
            {"module_code": "REPORTS", "code": "REPORTS_ADMIN", "name": "Reports Admin", "description": "Full administrative access to Statutory & Audit Reports."}
        ]

        roles_by_module_and_code = {}
        for r_data in roles_data:
            mod = modules_by_code.get(r_data["module_code"])
            if not mod:
                continue
            key = (mod.id, r_data["code"])
            r = existing_module_roles.get(key)
            if not r:
                r = ModuleRole(
                    module_id=mod.id,
                    code=r_data["code"],
                    name=r_data["name"],
                    description=r_data["description"]
                )
                db.add(r)
                db.flush()
                existing_module_roles[key] = r
            else:
                r.name = r_data["name"]
                r.description = r_data["description"]
            roles_by_module_and_code[(mod.code, r_data["code"])] = r

        # 3. Batch assign permissions to module roles
        all_perms = {p.code: p for p in db.query(Permission).all()}

        bms_employee_perms = [
            all_perms[c] for c in ["breakfast.submit", "breakfast.view_own", "breakfast.history_own"]
            if c in all_perms
        ]
        bms_finance_perms = [
            all_perms[c] for c in [
                "breakfast.submit", "breakfast.view_own", "breakfast.history_own", "breakfast.report",
                "breakfast.money.view", "breakfast.money.report",
                "finance.breakfast_fund.view", "finance.breakfast_fund.request.view",
                "finance.breakfast_fund.request.approve", "finance.breakfast_fund.request.reject",
                "finance.breakfast_fund.provide", "finance.breakfast_fund.report"
            ] if c in all_perms
        ]
        bms_director_perms = [
            all_perms[c] for c in [
                "breakfast.dashboard.view", "breakfast.orders.view", "breakfast.report",
                "breakfast.submit", "breakfast.view_own", "breakfast.history_own"
            ] if c in all_perms
        ]
        bms_admin_perms = [
            p for p in all_perms.values()
            if p.module in ["BREAKFAST", "MONEY", "FINANCE", "AUDIT"] and p.code != "*"
        ]

        bms_admin_role = roles_by_module_and_code.get(("BMS", "BMS_ADMIN"))
        if bms_admin_role:
            bms_admin_role.permissions = bms_admin_perms

        bms_emp_role = roles_by_module_and_code.get(("BMS", "BMS_EMPLOYEE"))
        if bms_emp_role:
            bms_emp_role.permissions = bms_employee_perms

        bms_fin_role = roles_by_module_and_code.get(("BMS", "BMS_FINANCE_MANAGER"))
        if bms_fin_role:
            bms_fin_role.permissions = bms_finance_perms

        bms_dir_role = roles_by_module_and_code.get(("BMS", "BMS_DIRECTOR_ANALYTICS"))
        if bms_dir_role:
            bms_dir_role.permissions = bms_director_perms

        user_admin_role = roles_by_module_and_code.get(("USERS", "USER_MANAGEMENT_ADMIN"))
        if user_admin_role:
            user_admin_role.permissions = [
                all_perms[c] for c in ["users.view", "users.create", "users.edit", "users.deactivate", "user.password.reset"]
                if c in all_perms
            ]

        # 4. Migrate users & memberships
        bms_mod = modules_by_code.get("BMS")
        all_roles = {r.code: r for r in db.query(Role).all()}
        it_global_role = all_roles.get("IT_ADMIN")
        dir_global_role = all_roles.get("DIRECTOR")

        # Handle legacy memberships that had obsolete role codes (e.g. BMS_FINANCE, BMS_VIEWER, BMS_MANAGER)
        legacy_role_mapping = {
            "BMS_VIEWER": "BMS_DIRECTOR_ANALYTICS",
            "BMS_FINANCE": "BMS_FINANCE_MANAGER",
            "BMS_MANAGER": "BMS_ADMIN"
        }
        all_memberships = db.query(UserModuleMembership).filter(UserModuleMembership.module_id == bms_mod.id).all()
        existing_mem_map = {m.user_id: m for m in all_memberships}

        for mem in all_memberships:
            if mem.role and mem.role.code in legacy_role_mapping:
                new_code = legacy_role_mapping[mem.role.code]
                target_role = roles_by_module_and_code.get(("BMS", new_code))
                if target_role:
                    mem.role_id = target_role.id

        users = db.query(User).all()
        for u in users:
            # Sync user name and phone from employee
            if u.employee:
                if not u.name:
                    u.name = u.employee.name or u.username
                if not u.phone:
                    u.phone = u.employee.phone or ""
            elif not u.name:
                u.name = u.username

            user_role_codes = [r.code for r in u.roles]

            has_it_admin = "IT_ADMIN" in user_role_codes
            has_director = "DIRECTOR" in user_role_codes or "CEO" in user_role_codes

            target_bms_role_code = None
            if has_it_admin or "BREAKFAST_ADMIN" in user_role_codes:
                target_bms_role_code = "BMS_ADMIN"
            elif "FINANCE_MANAGER" in user_role_codes:
                target_bms_role_code = "BMS_FINANCE_MANAGER"
            elif has_director or "DIRECTOR_ANALYTICS" in user_role_codes:
                target_bms_role_code = "BMS_DIRECTOR_ANALYTICS"
            elif "EMPLOYEE" in user_role_codes or u.employee:
                target_bms_role_code = "BMS_EMPLOYEE"

            if target_bms_role_code and (u.employee or target_bms_role_code == "BMS_ADMIN"):
                assigned_bms_role = roles_by_module_and_code.get(("BMS", target_bms_role_code))
                mem = existing_mem_map.get(u.id)

                if not mem:
                    mem = UserModuleMembership(
                        user_id=u.id,
                        module_id=bms_mod.id,
                        role_id=assigned_bms_role.id if assigned_bms_role else None,
                        is_active=True
                    )
                    db.add(mem)
                    existing_mem_map[u.id] = mem
                elif assigned_bms_role and (not mem.role or mem.role.code == "BMS_EMPLOYEE"):
                    mem.role_id = assigned_bms_role.id
                    mem.is_active = True

            # Cleanse user.roles to ONLY hold Global Roles: IT_ADMIN and/or DIRECTOR
            new_global_roles = []
            if has_it_admin and it_global_role:
                new_global_roles.append(it_global_role)
            if has_director and dir_global_role and dir_global_role not in new_global_roles:
                new_global_roles.append(dir_global_role)

            u.roles = new_global_roles

        # 5. Cleanse obsolete global roles from user associations
        obsolete_global_role_codes = ["EMPLOYEE", "BREAKFAST_ADMIN", "FINANCE_MANAGER", "DIRECTOR_ANALYTICS", "CEO"]
        for obs_code in obsolete_global_role_codes:
            obs_role = all_roles.get(obs_code)
            if obs_role:
                obs_role.users = []
                obs_role.permissions = []

        # 6. Deactivate legacy un-prefixed module roles so dropdowns only show official module roles
        legacy_obsolete_module_roles = [
            "BMS_VIEWER", "BMS_FINANCE", "BMS_MANAGER",
            "SALES_EXECUTIVE", "SALES_MANAGER",
            "LAB_TECHNICIAN", "QA_QC_MANAGER"
        ]
        for (m_id, r_code), r_obj in existing_module_roles.items():
            if r_code in legacy_obsolete_module_roles:
                r_obj.is_active = False

        db.commit()
        logger.info("Successfully synced modules, module roles, permissions, and migrated all user assignments.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during ensure_modules_and_memberships: {e}", exc_info=True)
        raise
    finally:
        db.close()
