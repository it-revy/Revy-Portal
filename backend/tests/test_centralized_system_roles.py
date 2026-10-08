import os
import sys
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.roles.model import Role
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.core.security import get_password_hash

client = TestClient(app)

def create_or_get_user(username: str, password: str = "TestPass123!", global_roles=None, module_roles=None):
    """
    Helper to provision a user with specific global system roles and/or module-specific roles.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                name=username.replace("_", " ").title(),
                username=username,
                email=f"{username}@revyportal.com",
                password_hash=get_password_hash(password),
                status="active"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Assign global roles
        if global_roles is not None:
            user.roles = []
            for r_code in global_roles:
                r_obj = db.query(Role).filter(Role.code == r_code).first()
                if r_obj:
                    user.roles.append(r_obj)

        # Clear existing memberships and assign requested module roles
        if module_roles is not None:
            db.query(UserModuleMembership).filter(UserModuleMembership.user_id == user.id).delete()
            db.commit()

            for mod_code, role_code in module_roles:
                mod_obj = db.query(Module).filter(Module.code == mod_code).first()
                if not mod_obj:
                    continue
                mr_obj = db.query(ModuleRole).filter(
                    ModuleRole.module_id == mod_obj.id,
                    ModuleRole.code == role_code
                ).first()
                if mr_obj:
                    membership = UserModuleMembership(
                        user_id=user.id,
                        module_id=mod_obj.id,
                        role_id=mr_obj.id,
                        is_active=True
                    )
                    db.add(membership)
            db.commit()

        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["token"], user_id

def test_system_global_roles():
    """
    Test Global System Roles: IT_ADMIN and DIRECTOR
    Both have full system access to all modules and all endpoints.
    """
    # 1. IT Admin
    it_token, _ = create_or_get_user("test_it_admin_global", global_roles=["IT_ADMIN"], module_roles=[])
    it_headers = {"Authorization": f"Bearer {it_token}"}

    # Access BMS
    assert client.get("/api/breakfast/today", headers=it_headers).status_code == 200
    # Access USERS
    assert client.get("/api/users", headers=it_headers).status_code == 200
    # Access CRM
    assert client.get("/api/crm/status", headers=it_headers).status_code == 200
    # Access LMS
    assert client.get("/api/lms/status", headers=it_headers).status_code == 200
    # Access IMS
    assert client.get("/api/ims/status", headers=it_headers).status_code == 200
    # Access LEAVE
    assert client.get("/api/leave/status", headers=it_headers).status_code == 200
    # Access MIS
    assert client.get("/api/mis/status", headers=it_headers).status_code == 200
    # Access DWR
    assert client.get("/api/dwr/status", headers=it_headers).status_code == 200

    # 2. Director (Global Role migrated from CEO)
    dir_token, _ = create_or_get_user("test_director_global", global_roles=["DIRECTOR"], module_roles=[])
    dir_headers = {"Authorization": f"Bearer {dir_token}"}

    # Access BMS
    assert client.get("/api/breakfast/today", headers=dir_headers).status_code == 200
    # Access USERS
    assert client.get("/api/users", headers=dir_headers).status_code == 200
    # Access CRM
    assert client.get("/api/crm/status", headers=dir_headers).status_code == 200
    # Access LMS
    assert client.get("/api/lms/status", headers=dir_headers).status_code == 200
    # Access IMS
    assert client.get("/api/ims/status", headers=dir_headers).status_code == 200
    # Access LEAVE
    assert client.get("/api/leave/status", headers=dir_headers).status_code == 200
    # Access MIS
    assert client.get("/api/mis/status", headers=dir_headers).status_code == 200
    # Access DWR
    assert client.get("/api/dwr/status", headers=dir_headers).status_code == 200

def test_bms_admin_isolation():
    """
    Test Module Isolation for BMS_ADMIN:
    Has full access to BMS, but is strictly FORBIDDEN (403) from accessing CRM, LMS, IMS, LEAVE, USERS.
    """
    bms_token, _ = create_or_get_user(
        "test_bms_admin_isolated",
        global_roles=[],
        module_roles=[("BMS", "BMS_ADMIN")]
    )
    bms_headers = {"Authorization": f"Bearer {bms_token}"}

    # Can access BMS
    today_res = client.get("/api/breakfast/today", headers=bms_headers)
    assert today_res.status_code == 200, f"BMS Admin should access BMS today: {today_res.text}"

    employees_res = client.get("/api/employees", headers=bms_headers)
    assert employees_res.status_code == 200, f"BMS Admin should access BMS employees: {employees_res.text}"

    # MUST NOT access USERS
    users_res = client.get("/api/users", headers=bms_headers)
    assert users_res.status_code == 403, f"BMS Admin must NOT access USERS API: {users_res.status_code}"

    # MUST NOT access CRM
    crm_res = client.get("/api/crm/status", headers=bms_headers)
    assert crm_res.status_code == 403, f"BMS Admin must NOT access CRM API: {crm_res.status_code}"

    # MUST NOT access LMS
    lms_res = client.get("/api/lms/status", headers=bms_headers)
    assert lms_res.status_code == 403, f"BMS Admin must NOT access LMS API: {lms_res.status_code}"

    # MUST NOT access IMS
    ims_res = client.get("/api/ims/status", headers=bms_headers)
    assert ims_res.status_code == 403, f"BMS Admin must NOT access IMS API: {ims_res.status_code}"

    # MUST NOT access LEAVE
    leave_res = client.get("/api/leave/status", headers=bms_headers)
    assert leave_res.status_code == 403, f"BMS Admin must NOT access LEAVE API: {leave_res.status_code}"

    # MUST NOT access MIS
    mis_res = client.get("/api/mis/status", headers=bms_headers)
    assert mis_res.status_code == 403, f"BMS Admin must NOT access MIS API: {mis_res.status_code}"

def test_user_management_admin_isolation():
    """
    Test Module Isolation for USER_MANAGEMENT_ADMIN:
    Has access to User Management APIs, but is strictly FORBIDDEN (403) from BMS, CRM, LMS, etc.
    """
    uma_token, _ = create_or_get_user(
        "test_uma_isolated",
        global_roles=[],
        module_roles=[("USERS", "USER_MANAGEMENT_ADMIN")]
    )
    uma_headers = {"Authorization": f"Bearer {uma_token}"}

    # Can access USERS
    users_res = client.get("/api/users", headers=uma_headers)
    assert users_res.status_code == 200, f"User Management Admin should access USERS API: {users_res.text}"

    # MUST NOT access BMS
    bms_res = client.get("/api/breakfast/today", headers=uma_headers)
    assert bms_res.status_code == 403, f"User Management Admin must NOT access BMS today: {bms_res.status_code}"

    # MUST NOT access CRM
    crm_res = client.get("/api/crm/status", headers=uma_headers)
    assert crm_res.status_code == 403, f"User Management Admin must NOT access CRM API: {crm_res.status_code}"

    # MUST NOT access LMS
    lms_res = client.get("/api/lms/status", headers=uma_headers)
    assert lms_res.status_code == 403, f"User Management Admin must NOT access LMS API: {lms_res.status_code}"

def test_crm_admin_isolation():
    """
    Test Module Isolation for CRM_ADMIN:
    Can access CRM, but is strictly FORBIDDEN from BMS, USERS, LMS.
    """
    crm_token, _ = create_or_get_user(
        "test_crm_admin_isolated",
        global_roles=[],
        module_roles=[("CRM", "CRM_ADMIN")]
    )
    crm_headers = {"Authorization": f"Bearer {crm_token}"}

    # Can access CRM
    crm_res = client.get("/api/crm/status", headers=crm_headers)
    assert crm_res.status_code == 200, f"CRM Admin should access CRM API: {crm_res.text}"

    # MUST NOT access BMS
    bms_res = client.get("/api/breakfast/today", headers=crm_headers)
    assert bms_res.status_code == 403, f"CRM Admin must NOT access BMS API: {bms_res.status_code}"

    # MUST NOT access USERS
    users_res = client.get("/api/users", headers=crm_headers)
    assert users_res.status_code == 403, f"CRM Admin must NOT access USERS API: {users_res.status_code}"

    # MUST NOT access LMS
    lms_res = client.get("/api/lms/status", headers=crm_headers)
    assert lms_res.status_code == 403, f"CRM Admin must NOT access LMS API: {lms_res.status_code}"

def test_module_roles_structure():
    """
    Verify that all 9 modules exist in the database and have their module-prefixed roles.
    """
    it_token, _ = create_or_get_user("test_it_admin_modlist", global_roles=["IT_ADMIN"], module_roles=[])
    it_headers = {"Authorization": f"Bearer {it_token}"}

    res = client.get("/api/modules", headers=it_headers)
    assert res.status_code == 200, f"Modules fetch failed: {res.text}"
    modules_data = res.json()

    modules_by_code = {m["code"]: m for m in modules_data}
    expected_codes = ["MIS", "BMS", "CRM", "LMS", "IMS", "LEAVE", "USERS", "DWR", "REPORTS"]
    for code in expected_codes:
        assert code in modules_by_code, f"Missing module {code} in database"

    # BMS roles check
    bms_role_codes = [r["code"] for r in modules_by_code["BMS"]["roles"]]
    for expected_r in ["BMS_ADMIN", "BMS_EMPLOYEE", "BMS_FINANCE_MANAGER", "BMS_DIRECTOR_ANALYTICS"]:
        assert expected_r in bms_role_codes, f"BMS missing role {expected_r}: found {bms_role_codes}"

    # CRM roles check
    crm_role_codes = [r["code"] for r in modules_by_code["CRM"]["roles"]]
    for expected_r in ["CRM_ADMIN", "CRM_SALES_EXECUTIVE", "CRM_SALES_MANAGER", "CRM_SALES_COORDINATOR", "CRM_FINANCE_MANAGER"]:
        assert expected_r in crm_role_codes, f"CRM missing role {expected_r}: found {crm_role_codes}"

    # LMS roles check
    lms_role_codes = [r["code"] for r in modules_by_code["LMS"]["roles"]]
    for expected_r in ["LMS_ADMIN", "LMS_RD_HEAD", "LMS_SUPERVISOR", "LMS_TEAM"]:
        assert expected_r in lms_role_codes, f"LMS missing role {expected_r}: found {lms_role_codes}"

    # USERS roles check
    users_role_codes = [r["code"] for r in modules_by_code["USERS"]["roles"]]
    assert "USER_MANAGEMENT_ADMIN" in users_role_codes, f"USERS missing USER_MANAGEMENT_ADMIN: found {users_role_codes}"

    # Global roles check via database
    db = SessionLocal()
    try:
        global_roles_data = db.query(Role).all()
        global_codes = [r.code for r in global_roles_data]
        assert "IT_ADMIN" in global_codes, "IT_ADMIN must be a global role"
        assert "DIRECTOR" in global_codes, "DIRECTOR must be a global role"
        assert "CEO" not in global_codes, "CEO must be migrated to DIRECTOR"
    finally:
        db.close()
