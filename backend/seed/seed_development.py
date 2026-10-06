import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, init_db
from app.core.security import get_password_hash
from app.roles.model import Role, Permission
from app.users.model import User
from app.employees.model import Employee, Department
from app.breakfast.model import BreakfastSetting, BreakfastReason

PERMISSIONS_DATA = [
    {"code": "*", "name": "Full Administrative Access", "module": "PLATFORM", "description": "Unrestricted system access"},
    {"code": "breakfast.view_own", "name": "View Own Breakfast Status", "module": "BREAKFAST", "description": "View daily form and history"},
    {"code": "breakfast.submit", "name": "Submit Daily Breakfast Status", "module": "BREAKFAST", "description": "Submit YES/NO daily response"},
    {"code": "breakfast.history_own", "name": "View Own Breakfast History", "module": "BREAKFAST", "description": "View personal historical records"},
    {"code": "breakfast.view", "name": "View All Breakfast Status", "module": "BREAKFAST", "description": "View company wide daily status"},
    {"code": "breakfast.manage", "name": "Manage Daily Breakfast Operations", "module": "BREAKFAST", "description": "Manage records, actual status, and orders"},
    {"code": "breakfast.report", "name": "Generate Breakfast Reports", "module": "BREAKFAST", "description": "Access daily and monthly reports"},
    {"code": "breakfast.orders.view", "name": "View All Breakfast Orders", "module": "BREAKFAST", "description": "View all company breakfast orders and order history"},
    {"code": "breakfast.dashboard.view", "name": "View Director Analytics Dashboard", "module": "BREAKFAST", "description": "Executive Director view of summary analytics"},
    {"code": "breakfast.employee.create", "name": "Create Employees", "module": "BREAKFAST", "description": "Add new employee records"},
    {"code": "breakfast.employee.read", "name": "Read Employee Records", "module": "BREAKFAST", "description": "View employee profiles and status"},
    {"code": "breakfast.employee.update", "name": "Update Employee Records", "module": "BREAKFAST", "description": "Modify employee info, participation types, and roles"},
    {"code": "breakfast.employee.deactivate", "name": "Deactivate Employees", "module": "BREAKFAST", "description": "Soft deactivate employee accounts"},
    {"code": "breakfast.holiday.manage", "name": "Manage Public Holidays", "module": "BREAKFAST", "description": "Add, view, and delete public company holidays"},
    {"code": "breakfast.settings.manage", "name": "Manage System Settings", "module": "BREAKFAST", "description": "Configure cutoff times and reason options"},
    {"code": "breakfast.money.view", "name": "View Breakfast Money Ledger", "module": "MONEY", "description": "View money balance and transactions"},
    {"code": "breakfast.money.request", "name": "Request Breakfast Money", "module": "MONEY", "description": "Request fund replenishment from Finance"},
    {"code": "breakfast.money.receive", "name": "Receive Money from Finance", "module": "MONEY", "description": "Record cash received from Finance"},
    {"code": "breakfast.money.receipt.verify", "name": "Verify Money Receipt", "module": "MONEY", "description": "Confirm money received"},
    {"code": "breakfast.money.expense.view", "name": "View Breakfast Expenses", "module": "MONEY", "description": "View expenses breakdown"},
    {"code": "breakfast.money.expense.create", "name": "Record Breakfast Expenses", "module": "MONEY", "description": "Create manual breakfast expenses"},
    {"code": "breakfast.money.adjust", "name": "Adjust Money Ledger", "module": "MONEY", "description": "Perform ledger adjustments"},
    {"code": "breakfast.money.report", "name": "Generate Money Statements", "module": "MONEY", "description": "Access daily and monthly money statements"},
    {"code": "finance.breakfast_fund.view", "name": "View Finance Breakfast Fund Dashboard", "module": "FINANCE", "description": "Access Finance Manager dashboard"},
    {"code": "finance.breakfast_fund.request.view", "name": "View Fund Requests", "module": "FINANCE", "description": "View pending and past fund requests"},
    {"code": "finance.breakfast_fund.request.approve", "name": "Approve Fund Requests", "module": "FINANCE", "description": "Approve breakfast fund request"},
    {"code": "finance.breakfast_fund.request.reject", "name": "Reject Fund Requests", "module": "FINANCE", "description": "Reject breakfast fund request"},
    {"code": "finance.breakfast_fund.provide", "name": "Provide Money for Fund Request", "module": "FINANCE", "description": "Record money provision for approved request"},
    {"code": "finance.breakfast_fund.report", "name": "Finance Fund Reports", "module": "FINANCE", "description": "View financial fund reports"},
    {"code": "breakfast.actual_status.override", "name": "Override Employee Actual Status", "module": "BREAKFAST", "description": "Override employee actual breakfast status"},
    {"code": "breakfast.audit.view", "name": "View Audit Logs", "module": "AUDIT", "description": "View system audit logs"},
    {"code": "user.password.reset", "name": "Reset User Passwords", "module": "PLATFORM", "description": "Reset employee login passwords"}
]

ROLES_DATA = [
    {
        "code": "IT_ADMIN",
        "name": "IT Administrator",
        "description": "Full administrative access and system management",
        "permissions": [
            "*", "user.password.reset", "breakfast.view", "breakfast.manage", "breakfast.report",
            "breakfast.employee.create", "breakfast.employee.read", "breakfast.employee.update",
            "breakfast.employee.deactivate", "breakfast.holiday.manage", "breakfast.settings.manage",
            "breakfast.audit.view", "breakfast.submit", "breakfast.view_own", "breakfast.history_own",
            "breakfast.money.view", "breakfast.money.request", "breakfast.money.receive",
            "breakfast.money.receipt.verify", "breakfast.money.expense.view", "breakfast.money.expense.create",
            "breakfast.money.adjust", "breakfast.money.report", "finance.breakfast_fund.view",
            "finance.breakfast_fund.request.view", "finance.breakfast_fund.request.approve",
            "finance.breakfast_fund.request.reject", "finance.breakfast_fund.provide",
            "finance.breakfast_fund.report", "breakfast.actual_status.override"
        ]
    },
    {
        "code": "BREAKFAST_ADMIN",
        "name": "Breakfast Administrator",
        "description": "Manages daily breakfast process, orders, reports, and holidays",
        "permissions": [
            "breakfast.view", "breakfast.manage", "breakfast.report", "breakfast.employee.read",
            "breakfast.holiday.manage", "breakfast.submit", "breakfast.view_own", "breakfast.history_own",
            "breakfast.money.view", "breakfast.money.request", "breakfast.money.receive",
            "breakfast.money.receipt.verify", "breakfast.money.expense.view", "breakfast.money.expense.create",
            "breakfast.money.adjust", "breakfast.money.report", "breakfast.actual_status.override"
        ]
    },
    {
        "code": "FINANCE_MANAGER",
        "name": "Finance Manager",
        "description": "Manages fund approvals, provisions, and financial reports",
        "permissions": [
            "finance.breakfast_fund.view", "finance.breakfast_fund.request.view",
            "finance.breakfast_fund.request.approve", "finance.breakfast_fund.request.reject",
            "finance.breakfast_fund.provide", "finance.breakfast_fund.report",
            "breakfast.money.view", "breakfast.money.report", "breakfast.report", "breakfast.view_own",
            "breakfast.submit", "breakfast.history_own"
        ]
    },
    {
        "code": "EMPLOYEE",
        "name": "Standard Employee",
        "description": "Standard employee submitting daily breakfast status",
        "permissions": [
            "breakfast.view_own", "breakfast.submit", "breakfast.history_own"
        ]
    },
    {
        "code": "DIRECTOR_ANALYTICS",
        "name": "Director Analytics",
        "description": "Executive Director Analytics dashboard and management insights",
        "permissions": [
            "breakfast.dashboard.view", "breakfast.view_own", "breakfast.submit", "breakfast.history_own"
        ]
    },
    {
        "code": "CEO",
        "name": "Chief Executive Officer",
        "description": "Executive reporting, employee management, holiday overview, and company-wide breakfast orders overview",
        "permissions": [
            "breakfast.report", "breakfast.orders.view", "breakfast.holiday.manage",
            "breakfast.employee.create", "breakfast.employee.read", "breakfast.employee.update",
            "breakfast.employee.deactivate", "breakfast.view_own", "breakfast.submit",
            "breakfast.history_own"
        ]
    }
]

DEFAULT_REASONS = [
    {"code": "FASTING", "label": "Fasting", "isCustomAllowed": False, "displayOrder": 1},
    {"code": "ON_LEAVE", "label": "On Leave", "isCustomAllowed": False, "displayOrder": 2},
    {"code": "WORKING_OUTSIDE", "label": "Working Outside", "isCustomAllowed": False, "displayOrder": 3},
    {"code": "PERSONAL", "label": "Personal Reason", "isCustomAllowed": False, "displayOrder": 4},
    {"code": "NOT_REQUIRED", "label": "Not Required", "isCustomAllowed": False, "displayOrder": 5},
    {"code": "OTHER", "label": "Other", "isCustomAllowed": True, "displayOrder": 6}
]

DEFAULT_ACCOUNTS = [
    {
        "employeeId": "EMP-0001",
        "username": "vasudev",
        "name": "Vasudev Kava",
        "email": "vasudev@company.com",
        "initialPasswordText": "Vasudev123",
        "phone": "+91 9876543210",
        "department": "IT Infrastructure",
        "designation": "IT Administrator",
        "status": "active",
        "roles": ["IT_ADMIN", "BREAKFAST_ADMIN", "EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    },
    {
        "employeeId": "EMP-0002",
        "username": "faiz",
        "name": "Faiz Saiyad",
        "email": "faiz@company.com",
        "initialPasswordText": "Faiz123",
        "phone": "+91 9876543211",
        "department": "Administration",
        "designation": "Breakfast Manager",
        "status": "active",
        "roles": ["BREAKFAST_ADMIN", "EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    },
    {
        "employeeId": "EMP-0003",
        "username": "rajneesh",
        "name": "Rajneesh Prasad",
        "email": "rajneesh@company.com",
        "initialPasswordText": "Rajneesh123",
        "phone": "+91 9876543212",
        "department": "Executive Office",
        "designation": "Chief Executive Officer",
        "status": "active",
        "roles": ["CEO", "EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    },
    {
        "employeeId": "EMP-0004",
        "username": "jyoti",
        "name": "Jyoti Dutta",
        "email": "jyoti@company.com",
        "initialPasswordText": "Jyoti123",
        "phone": "+91 9876543213",
        "department": "Engineering",
        "designation": "Software Engineer",
        "status": "active",
        "roles": ["EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    },
    {
        "employeeId": "EMP-0005",
        "username": "hritika",
        "name": "Hritika",
        "email": "hritika@company.com",
        "initialPasswordText": "Hritika123",
        "phone": "+91 9876543214",
        "department": "Quality Assurance",
        "designation": "QA Specialist",
        "status": "active",
        "roles": ["EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    },
    {
        "employeeId": "EMP-0006",
        "username": "nisha",
        "name": "Nisha",
        "email": "nisha@company.com",
        "initialPasswordText": "Nisha123",
        "phone": "+91 9876543215",
        "department": "Research & Development",
        "designation": "R&D Analyst",
        "status": "active",
        "roles": ["EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    },
    {
        "employeeId": "EMP-0007",
        "username": "himani",
        "name": "Himani",
        "email": "himani@company.com",
        "initialPasswordText": "Himani123",
        "phone": "+91 9876543216",
        "department": "Human Resources",
        "designation": "HR Executive",
        "status": "active",
        "roles": ["EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    },
    {
        "employeeId": "EMP-0008",
        "username": "shahil",
        "name": "Shahil",
        "email": "shahil@company.com",
        "initialPasswordText": "Shahil123",
        "phone": "+91 9876543217",
        "department": "Operations",
        "designation": "Operations Associate",
        "status": "active",
        "roles": ["EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    },
    {
        "employeeId": "EMP-0009",
        "username": "finance.manager",
        "name": "Finance Manager",
        "email": "finance@company.com",
        "initialPasswordText": "Finance123",
        "phone": "+91 9876543218",
        "department": "Finance & Accounts",
        "designation": "Finance Manager",
        "status": "active",
        "roles": ["FINANCE_MANAGER", "EMPLOYEE"],
        "breakfastParticipationType": "NORMAL"
    }
]

def seed_database():
    print("[Seed] Initializing database tables...")
    init_db()
    db = SessionLocal()

    try:
        print("[Seed] Seeding permissions...")
        perm_map = {}
        for p_data in PERMISSIONS_DATA:
            p = db.query(Permission).filter(Permission.code == p_data["code"]).first()
            if not p:
                p = Permission(
                    code=p_data["code"],
                    name=p_data["name"],
                    module=p_data["module"],
                    description=p_data["description"]
                )
                db.add(p)
                db.flush()
            perm_map[p.code] = p

        print("[Seed] Seeding roles...")
        role_map = {}
        for r_data in ROLES_DATA:
            role = db.query(Role).filter(Role.code == r_data["code"]).first()
            if not role:
                role = Role(
                    code=r_data["code"],
                    name=r_data["name"],
                    description=r_data["description"]
                )
                db.add(role)
                db.flush()

            # Assign permissions
            role_perms = [perm_map[code] for code in r_data["permissions"] if code in perm_map]
            role.permissions = role_perms
            role_map[role.code] = role

        print("[Seed] Seeding breakfast settings...")
        setting = db.query(BreakfastSetting).first()
        if not setting:
            setting = BreakfastSetting(
                cutoff_time="12:00",
                timezone="Asia/Kolkata",
                auto_lock_enabled=True,
                breakfast_fund_limit=2500.0
            )
            db.add(setting)

        print("[Seed] Seeding breakfast rejection reasons...")
        for reason in DEFAULT_REASONS:
            r = db.query(BreakfastReason).filter(BreakfastReason.code == reason["code"]).first()
            if not r:
                r = BreakfastReason(
                    code=reason["code"],
                    label=reason["label"],
                    is_custom_allowed=reason["isCustomAllowed"],
                    display_order=reason["displayOrder"]
                )
                db.add(r)

        print("[Seed] Seeding departments...")
        dept_names = set(a["department"] for a in DEFAULT_ACCOUNTS)
        for d_name in dept_names:
            d = db.query(Department).filter(Department.name == d_name).first()
            if not d:
                d = Department(name=d_name)
                db.add(d)

        print("[Seed] Seeding default accounts...")
        for acc in DEFAULT_ACCOUNTS:
            emp = db.query(Employee).filter(Employee.employee_id == acc["employeeId"]).first()
            user = db.query(User).filter(User.username == acc["username"]).first()

            if not user:
                pwd_hash = get_password_hash(acc["initialPasswordText"])
                user = User(
                    username=acc["username"].lower(),
                    email=acc["email"].lower(),
                    password_hash=pwd_hash,
                    status=acc["status"],
                    force_password_change=True,
                    is_hard_deleted=False
                )
                user.roles = [role_map[rc] for rc in acc["roles"] if rc in role_map]
                db.add(user)
                db.flush()
            else:
                user.password_hash = get_password_hash(acc["initialPasswordText"])
                user.roles = [role_map[rc] for rc in acc["roles"] if rc in role_map]
                db.flush()

            if not emp:
                emp = Employee(
                    user_id=user.id,
                    employee_id=acc["employeeId"],
                    name=acc["name"],
                    email=acc["email"].lower(),
                    phone=acc["phone"],
                    department=acc["department"],
                    designation=acc["designation"],
                    status=acc["status"],
                    breakfast_participation_type=acc["breakfastParticipationType"],
                    is_hard_deleted=False
                )
                db.add(emp)
                print(f"[Seed] Created user account: {acc['username']} ({acc['employeeId']})")

        db.commit()
        print("[Seed] Development seed completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"[Seed] FATAL: Seeding error: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
