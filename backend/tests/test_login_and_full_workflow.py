import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.roles.model import Role
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.core.security import get_password_hash, verify_password

client = TestClient(app)

def test_1_vasudev_login_and_authentication():
    """Verify vasudev test user exists, password hashes match, and login succeeds."""
    # 1. Test database record directly
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "vasudev").first()
        assert user is not None, "User vasudev must exist in database"
        assert user.status == "active", "User vasudev must be active"
        assert not user.is_hard_deleted, "User vasudev must not be hard deleted"
        assert verify_password("Vasudev123", user.password_hash), "Password verification for Vasudev123 must pass"
    finally:
        db.close()

    # 2. Test Login API endpoint with valid credentials
    res = client.post("/api/auth/login", json={
        "username": "vasudev",
        "password": "Vasudev123"
    })
    assert res.status_code == 200, f"Login failed: {res.text}"
    data = res.json()
    assert data["success"] is True
    assert "token" in data and len(data["token"]) > 20
    assert data["user"]["username"] == "vasudev"
    assert "IT_ADMIN" in data["user"]["roles"]

    # 3. Test Invalid credentials rejection
    res_bad = client.post("/api/auth/login", json={
        "username": "vasudev",
        "password": "WrongPassword999!"
    })
    assert res_bad.status_code == 401
    assert "Invalid username or password" in res_bad.json()["message"]

def test_2_session_restore_and_user_profile():
    """Test token validation and session restoration via /api/auth/me."""
    login_res = client.post("/api/auth/login", json={
        "username": "vasudev",
        "password": "Vasudev123"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_info = me_res.json()["user"]
    assert user_info["username"] == "vasudev"
    assert "IT_ADMIN" in user_info["roles"]
    assert len(user_info["modules"]) >= 1

    # Verify unauthorized request without token is rejected
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401

def test_3_portal_modules_and_role_architecture():
    """Verify all 9 services exist in system and role dropdown values are strictly scoped."""
    login_res = client.post("/api/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    headers = {"Authorization": f"Bearer {login_res.json()['token']}"}

    res = client.get("/api/modules", headers=headers)
    assert res.status_code == 200
    modules = res.json()
    module_codes = {m["code"] for m in modules}

    expected_services = ["MIS", "BMS", "CRM", "LMS", "IMS", "LEAVE", "USERS", "DWR", "REPORTS"]
    for s in expected_services:
        assert s in module_codes, f"Module {s} must exist in portal modules"

    # Verify BMS module roles only contain BMS roles
    bms_mod = next(m for m in modules if m["code"] == "BMS")
    bms_role_codes = [r["code"] for r in bms_mod["roles"]]
    for r_code in bms_role_codes:
        assert r_code.startswith("BMS_"), f"BMS role {r_code} must only have BMS_ prefix"
    assert "BMS_ADMIN" in bms_role_codes
    assert "BMS_EMPLOYEE" in bms_role_codes
    assert "BMS_FINANCE_MANAGER" in bms_role_codes
    assert "BMS_DIRECTOR_ANALYTICS" in bms_role_codes

    # Verify CRM module roles only contain CRM roles
    crm_mod = next(m for m in modules if m["code"] == "CRM")
    crm_role_codes = [r["code"] for r in crm_mod["roles"]]
    for r_code in crm_role_codes:
        assert r_code.startswith("CRM_"), f"CRM role {r_code} must only have CRM_ prefix"

def test_4_bms_workflow_endpoints():
    """Verify vasudev can access all BMS workflow endpoints."""
    login_res = client.post("/api/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    headers = {"Authorization": f"Bearer {login_res.json()['token']}"}

    endpoints = [
        "/api/breakfast/today",
        "/api/breakfast/money/balance",
        "/api/employees",
        "/api/holidays",
        "/api/settings",
        "/api/audit-logs"
    ]
    for ep in endpoints:
        r = client.get(ep, headers=headers)
        assert r.status_code in [200, 204], f"Endpoint {ep} failed: {r.status_code} {r.text}"

def test_5_user_management_workflow():
    """Verify User Management endpoints: list, create, edit, and module assignment."""
    login_res = client.post("/api/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    headers = {"Authorization": f"Bearer {login_res.json()['token']}"}

    # 1. List Users
    users_res = client.get("/api/users", headers=headers)
    assert users_res.status_code == 200
    assert len(users_res.json()) > 0

    # 2. Create User
    uid = uuid.uuid4().hex[:6]
    test_user_payload = {
        "name": f"Workflow Test User {uid}",
        "username": f"wfuser_{uid}",
        "email": f"wfuser_{uid}@company.com",
        "phone": "+91 9123456780",
        "password": "WfPassword123!",
        "status": "active"
    }
    create_res = client.post("/api/users", headers=headers, json=test_user_payload)
    assert create_res.status_code == 200
    created_id = create_res.json()["id"]

    try:
        # 3. Edit User (update phone)
        edit_res = client.put(f"/api/users/{created_id}", headers=headers, json={
            "phone": "+91 9999900000"
        })
        assert edit_res.status_code == 200
        assert edit_res.json()["phone"] == "+91 9999900000"

        # 4. Assign Module & Module Role (Assign to BMS as BMS_EMPLOYEE)
        assign_res = client.put(f"/api/users/{created_id}/modules", headers=headers, json={
            "modules": [
                {
                    "moduleCode": "BMS",
                    "enabled": True,
                    "roleCode": "BMS_EMPLOYEE"
                }
            ]
        })
        assert assign_res.status_code == 200
        memberships = assign_res.json()
        bms_mem = next(m for m in memberships if m["moduleCode"] == "BMS")
        assert bms_mem["isEnabled"] is True
        assert bms_mem["roleCode"] == "BMS_EMPLOYEE"
    finally:
        # Clean up
        db = SessionLocal()
        try:
            from app.employees.model import Employee
            emp = db.query(Employee).filter(Employee.user_id == created_id).first()
            if emp:
                db.delete(emp)
            u = db.query(User).filter(User.id == created_id).first()
            if u:
                db.delete(u)
            db.commit()
        finally:
            db.close()

def test_6_module_role_isolation_and_direct_url_security():
    """
    Verify module-specific roles DO NOT leak to other modules.
    A user with ONLY BMS_ADMIN must be able to access BMS, but direct API access
    to CRM, LMS, IMS, LEAVE, and USERS must be rejected with 403 Forbidden.
    """
    admin_login = client.post("/api/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

    uid = uuid.uuid4().hex[:6]
    bms_only_username = f"bms_admin_{uid}"

    # 1. Create a user without any global roles
    create_res = client.post("/api/users", headers=admin_headers, json={
        "name": f"BMS Only Admin {uid}",
        "username": bms_only_username,
        "email": f"{bms_only_username}@company.com",
        "phone": "+91 9888877777",
        "password": "BmsPassword123!",
        "status": "active"
    })
    assert create_res.status_code == 200
    user_id = create_res.json()["id"]

    try:
        # 2. Assign ONLY BMS module membership with BMS_ADMIN role
        mod_res = client.put(f"/api/users/{user_id}/modules", headers=admin_headers, json={
            "modules": [
                {
                    "moduleCode": "BMS",
                    "enabled": True,
                    "roleCode": "BMS_ADMIN"
                }
            ]
        })
        assert mod_res.status_code == 200

        # 3. Log in as the BMS-only user
        bms_login = client.post("/api/auth/login", json={
            "username": bms_only_username,
            "password": "BmsPassword123!"
        })
        assert bms_login.status_code == 200
        bms_user_token = bms_login.json()["token"]
        bms_user_headers = {"Authorization": f"Bearer {bms_user_token}"}

        # 4. BMS API: ACCESS GRANTED
        bms_access = client.get("/api/breakfast/today", headers=bms_user_headers)
        assert bms_access.status_code == 200, f"BMS access should succeed, got: {bms_access.status_code}"

        # 5. Direct URL security: Accessing CRM, LMS, IMS, LEAVE, USERS must be DENIED (403)
        crm_access = client.get("/api/crm/status", headers=bms_user_headers)
        assert crm_access.status_code == 403, f"Expected 403 for CRM, got: {crm_access.status_code}"

        lms_access = client.get("/api/lms/status", headers=bms_user_headers)
        assert lms_access.status_code == 403, f"Expected 403 for LMS, got: {lms_access.status_code}"

        ims_access = client.get("/api/ims/status", headers=bms_user_headers)
        assert ims_access.status_code == 403, f"Expected 403 for IMS, got: {ims_access.status_code}"

        leave_access = client.get("/api/leave/status", headers=bms_user_headers)
        assert leave_access.status_code == 403, f"Expected 403 for LEAVE, got: {leave_access.status_code}"

        users_access = client.get("/api/users", headers=bms_user_headers)
        assert users_access.status_code == 403, f"Expected 403 for USERS, got: {users_access.status_code}"

    finally:
        # Clean up
        db = SessionLocal()
        try:
            from app.employees.model import Employee
            emp = db.query(Employee).filter(Employee.user_id == user_id).first()
            if emp:
                db.delete(emp)
            u = db.query(User).filter(User.id == user_id).first()
            if u:
                db.delete(u)
            db.commit()
        finally:
            db.close()

def test_7_global_roles_it_admin_and_director_full_access():
    """Verify IT Admin and Director have full unrestricted access across all modules."""
    # 1. IT Admin (vasudev)
    it_login = client.post("/api/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    it_headers = {"Authorization": f"Bearer {it_login.json()['token']}"}

    # Verify access to CRM, LMS, IMS, LEAVE, BMS, USERS
    assert client.get("/api/crm/status", headers=it_headers).status_code == 200
    assert client.get("/api/lms/status", headers=it_headers).status_code == 200
    assert client.get("/api/ims/status", headers=it_headers).status_code == 200
    assert client.get("/api/leave/status", headers=it_headers).status_code == 200
    assert client.get("/api/breakfast/today", headers=it_headers).status_code == 200
    assert client.get("/api/users", headers=it_headers).status_code == 200

    # 2. Director Global Role
    db = SessionLocal()
    dir_id = None
    try:
        dir_role = db.query(Role).filter(Role.code == "DIRECTOR").first()
        uid = uuid.uuid4().hex[:6]
        dir_username = f"director_{uid}"
        dir_user = User(
            name=f"Director Test {uid}",
            username=dir_username,
            email=f"{dir_username}@company.com",
            password_hash=get_password_hash("DirectorPass123!"),
            status="active"
        )
        if dir_role:
            dir_user.roles = [dir_role]
        db.add(dir_user)
        db.commit()
        dir_id = dir_user.id
    finally:
        db.close()

    try:
        dir_login = client.post("/api/auth/login", json={
            "username": dir_username,
            "password": "DirectorPass123!"
        })
        assert dir_login.status_code == 200
        dir_headers = {"Authorization": f"Bearer {dir_login.json()['token']}"}

        # Director has full access without separate module memberships
        assert client.get("/api/crm/status", headers=dir_headers).status_code == 200
        assert client.get("/api/lms/status", headers=dir_headers).status_code == 200
        assert client.get("/api/ims/status", headers=dir_headers).status_code == 200
        assert client.get("/api/leave/status", headers=dir_headers).status_code == 200
        assert client.get("/api/breakfast/today", headers=dir_headers).status_code == 200
        assert client.get("/api/users", headers=dir_headers).status_code == 200
    finally:
        if dir_id:
            db = SessionLocal()
            try:
                u = db.query(User).filter(User.id == dir_id).first()
                if u:
                    db.delete(u)
                    db.commit()
            finally:
                db.close()
