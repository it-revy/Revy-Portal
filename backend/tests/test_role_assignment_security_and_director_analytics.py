import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.roles.model import Role, Permission
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.employees.model import Employee
from app.core.security import get_password_hash

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_roles_and_test_users():
    """Seed test users and ensure DB connections are closed before tests run."""
    db = SessionLocal()
    try:
        # Global IT Admin
        it_admin = db.query(User).filter(User.username == "test_sec_it_admin").first()
        if not it_admin:
            it_admin = User(
                name="Security IT Admin",
                username="test_sec_it_admin",
                email="test_sec_it_admin@company.com",
                password_hash=get_password_hash("Admin123!"),
                status="active"
            )
            db.add(it_admin)
            db.commit()
            db.refresh(it_admin)
        it_role = db.query(Role).filter(Role.code == "IT_ADMIN").first()
        if it_role:
            it_admin.roles = [it_role]
            db.commit()

        # Global Director
        director = db.query(User).filter(User.username == "test_sec_director").first()
        if not director:
            director = User(
                name="Security Director",
                username="test_sec_director",
                email="test_sec_director@company.com",
                password_hash=get_password_hash("Director123!"),
                status="active"
            )
            db.add(director)
            db.commit()
            db.refresh(director)
        dir_role = db.query(Role).filter(Role.code == "DIRECTOR").first()
        if dir_role:
            director.roles = [dir_role]
            db.commit()

        bms_mod = db.query(Module).filter(Module.code == "BMS").first()
        bms_admin_role = db.query(ModuleRole).filter(ModuleRole.module_id == bms_mod.id, ModuleRole.code == "BMS_ADMIN").first()
        bms_bf_role = db.query(ModuleRole).filter(ModuleRole.module_id == bms_mod.id, ModuleRole.code == "BMS_BF_MANAGER").first()

        # BMS Admin
        bms_admin = db.query(User).filter(User.username == "test_sec_bms_admin").first()
        if not bms_admin:
            bms_admin = User(
                name="Security BMS Admin",
                username="test_sec_bms_admin",
                email="test_sec_bms_admin@company.com",
                password_hash=get_password_hash("BmsAdmin123!"),
                status="active"
            )
            db.add(bms_admin)
            db.commit()
            db.refresh(bms_admin)
            emp = Employee(
                user_id=bms_admin.id,
                employee_id="EMP-SEC-ADMIN",
                name="Security BMS Admin",
                email=bms_admin.email,
                department="Management",
                designation="BMS Admin",
                status="active"
            )
            db.add(emp)
            db.commit()
        bms_admin.roles = []
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == bms_admin.id).delete()
        db.add(UserModuleMembership(user_id=bms_admin.id, module_id=bms_mod.id, role_id=bms_admin_role.id, is_active=True))
        db.commit()

        # BMS BF Manager
        bf_mgr = db.query(User).filter(User.username == "test_sec_bf_mgr").first()
        if not bf_mgr:
            bf_mgr = User(
                name="Security BF Manager",
                username="test_sec_bf_mgr",
                email="test_sec_bf_mgr@company.com",
                password_hash=get_password_hash("BfMgr123!"),
                status="active"
            )
            db.add(bf_mgr)
            db.commit()
            db.refresh(bf_mgr)
            emp = Employee(
                user_id=bf_mgr.id,
                employee_id="EMP-SEC-BFMGR",
                name="Security BF Manager",
                email=bf_mgr.email,
                department="Kitchen Operations",
                designation="BF Manager",
                status="active"
            )
            db.add(emp)
            db.commit()
        bf_mgr.roles = []
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == bf_mgr.id).delete()
        db.add(UserModuleMembership(user_id=bf_mgr.id, module_id=bms_mod.id, role_id=bms_bf_role.id, is_active=True))
        db.commit()

        # Candidate Central Users
        for i in range(1, 6):
            c_user = db.query(User).filter(User.username == f"test_sec_candidate_{i}").first()
            if not c_user:
                c_user = User(
                    name=f"Candidate User {i}",
                    username=f"test_sec_candidate_{i}",
                    email=f"candidate_{i}@company.com",
                    password_hash=get_password_hash("Cand123!"),
                    status="active"
                )
                db.add(c_user)
                db.commit()
            # Ensure not in BMS yet
            db.query(UserModuleMembership).filter(UserModuleMembership.user_id == c_user.id, UserModuleMembership.module_id == bms_mod.id).delete()
            if c_user.employee:
                db.delete(c_user.employee)
            db.commit()

        return True
    finally:
        db.close()

def get_auth_headers(username, password, role_used=None):
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    if role_used:
        headers["X-Role-Used"] = role_used
    return headers

# =========================================================================
# 1. ASSIGNABLE ROLES ENDPOINTS
# =========================================================================

def test_assignable_roles_bf_manager(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bf_mgr", "BfMgr123!", "BMS_BF_MANAGER")
    res = client.get("/api/v1/employees/assignable-roles", headers=headers)
    assert res.status_code == 200
    roles = res.json().get("roles", [])
    codes = [r["code"] for r in roles]

    assert "BMS_EMPLOYEE" in codes
    assert "BMS_BF_MANAGER" in codes
    assert "BMS_ADMIN" not in codes
    assert "BMS_FINANCE_MANAGER" not in codes
    assert "BMS_DIRECTOR_ANALYTICS" not in codes
    assert "IT_ADMIN" not in codes
    assert "DIRECTOR" not in codes

def test_assignable_roles_bms_admin(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bms_admin", "BmsAdmin123!", "BMS_ADMIN")
    res = client.get("/api/v1/employees/assignable-roles", headers=headers)
    assert res.status_code == 200
    roles = res.json().get("roles", [])
    codes = [r["code"] for r in roles]

    assert "BMS_EMPLOYEE" in codes
    assert "BMS_BF_MANAGER" in codes
    assert "BMS_ADMIN" in codes
    assert "BMS_FINANCE_MANAGER" not in codes
    assert "BMS_DIRECTOR_ANALYTICS" not in codes
    assert "IT_ADMIN" not in codes
    assert "DIRECTOR" not in codes

def test_assignable_roles_global_admin(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_it_admin", "Admin123!", "IT_ADMIN")
    res = client.get("/api/v1/employees/assignable-roles", headers=headers)
    assert res.status_code == 200
    roles = res.json().get("roles", [])
    codes = [r["code"] for r in roles]

    assert "BMS_EMPLOYEE" in codes
    assert "BMS_BF_MANAGER" in codes
    assert "BMS_ADMIN" in codes
    assert "BMS_FINANCE_MANAGER" in codes
    assert "BMS_DIRECTOR_ANALYTICS" not in codes

# =========================================================================
# 2. BMS BF MANAGER ROLE ASSIGNMENT RESTRICTION TESTS
# =========================================================================

def test_bf_manager_can_assign_permitted_roles(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bf_mgr", "BfMgr123!", "BMS_BF_MANAGER")
    db = SessionLocal()
    cand1 = db.query(User).filter(User.username == "test_sec_candidate_1").first()
    cand_id = cand1.id
    db.close()

    # Can assign BMS_EMPLOYEE
    res = client.post("/api/v1/employees/assign-user", json={
        "userId": cand_id,
        "roleCode": "BMS_EMPLOYEE",
        "department": "Engineering",
        "designation": "Software Engineer"
    }, headers=headers)
    assert res.status_code == 200
    emp = res.json()["employee"]
    assert emp["bmsRoleCode"] == "BMS_EMPLOYEE"

    # Can update to BMS_BF_MANAGER
    res_update = client.put(f"/api/v1/employees/{emp['employeeId']}", json={
        "roleCode": "BMS_BF_MANAGER"
    }, headers=headers)
    assert res_update.status_code == 200
    assert res_update.json()["employee"]["bmsRoleCode"] == "BMS_BF_MANAGER"

def test_bf_manager_cannot_assign_bms_admin(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bf_mgr", "BfMgr123!", "BMS_BF_MANAGER")
    db = SessionLocal()
    cand2 = db.query(User).filter(User.username == "test_sec_candidate_2").first()
    cand_id = cand2.id
    db.close()

    res = client.post("/api/v1/employees/assign-user", json={
        "userId": cand_id,
        "roleCode": "BMS_ADMIN",
        "department": "Operations",
        "designation": "Admin"
    }, headers=headers)
    assert res.status_code == 403
    err_msg = res.json().get("message") or res.json().get("detail") or ""
    assert "not authorized to assign BMS Admin" in err_msg

def test_bf_manager_cannot_assign_bms_finance_manager(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bf_mgr", "BfMgr123!", "BMS_BF_MANAGER")
    db = SessionLocal()
    cand3 = db.query(User).filter(User.username == "test_sec_candidate_3").first()
    cand_id = cand3.id
    db.close()

    res = client.post("/api/v1/employees/assign-user", json={
        "userId": cand_id,
        "roleCode": "BMS_FINANCE_MANAGER",
        "department": "Finance",
        "designation": "Finance Head"
    }, headers=headers)
    assert res.status_code == 403
    err_msg = res.json().get("message") or res.json().get("detail") or ""
    assert "not authorized to assign BMS Finance Manager" in err_msg

def test_bf_manager_cannot_assign_global_roles(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bf_mgr", "BfMgr123!", "BMS_BF_MANAGER")
    db = SessionLocal()
    cand4 = db.query(User).filter(User.username == "test_sec_candidate_4").first()
    cand_id = cand4.id
    db.close()

    res = client.post("/api/v1/employees/assign-user", json={
        "userId": cand_id,
        "roleCode": "IT_ADMIN",
        "department": "IT",
        "designation": "IT Admin"
    }, headers=headers)
    assert res.status_code == 403

def test_bf_manager_cannot_escalate_self(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bf_mgr", "BfMgr123!", "BMS_BF_MANAGER")
    # Attempt to update own employee profile with BMS_ADMIN
    res = client.put("/api/v1/employees/EMP-SEC-BFMGR", json={
        "roleCode": "BMS_ADMIN"
    }, headers=headers)
    assert res.status_code == 403

# =========================================================================
# 3. BMS ADMIN ROLE ASSIGNMENT RESTRICTION TESTS
# =========================================================================

def test_bms_admin_can_assign_permitted_roles(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bms_admin", "BmsAdmin123!", "BMS_ADMIN")
    db = SessionLocal()
    cand5 = db.query(User).filter(User.username == "test_sec_candidate_5").first()
    cand_id = cand5.id
    db.close()

    # Can assign BMS_EMPLOYEE
    res = client.post("/api/v1/employees/assign-user", json={
        "userId": cand_id,
        "roleCode": "BMS_EMPLOYEE",
        "department": "Operations",
        "designation": "Assistant"
    }, headers=headers)
    assert res.status_code == 200
    emp = res.json()["employee"]

    # Can update to BMS_BF_MANAGER
    res = client.put(f"/api/v1/employees/{emp['employeeId']}", json={
        "roleCode": "BMS_BF_MANAGER"
    }, headers=headers)
    assert res.status_code == 200

    # Can update to BMS_ADMIN
    res = client.put(f"/api/v1/employees/{emp['employeeId']}", json={
        "roleCode": "BMS_ADMIN"
    }, headers=headers)
    assert res.status_code == 200

def test_bms_admin_cannot_assign_finance_manager(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bms_admin", "BmsAdmin123!", "BMS_ADMIN")
    db = SessionLocal()
    emp = db.query(Employee).join(User).filter(User.username == "test_sec_candidate_5").first()
    emp_id = emp.employee_id
    db.close()

    res = client.put(f"/api/v1/employees/{emp_id}", json={
        "roleCode": "BMS_FINANCE_MANAGER"
    }, headers=headers)
    assert res.status_code == 403
    err_msg = res.json().get("message") or res.json().get("detail") or ""
    assert "not authorized to assign BMS Finance Manager" in err_msg

def test_bms_admin_cannot_assign_global_roles(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bms_admin", "BmsAdmin123!", "BMS_ADMIN")
    db = SessionLocal()
    emp = db.query(Employee).join(User).filter(User.username == "test_sec_candidate_5").first()
    emp_id = emp.employee_id
    db.close()

    res = client.put(f"/api/v1/employees/{emp_id}", json={
        "roleCode": "DIRECTOR"
    }, headers=headers)
    assert res.status_code == 403

def test_bms_admin_cannot_escalate_self(setup_roles_and_test_users):
    headers = get_auth_headers("test_sec_bms_admin", "BmsAdmin123!", "BMS_ADMIN")
    res = client.put("/api/v1/employees/EMP-SEC-ADMIN", json={
        "roleCode": "BMS_FINANCE_MANAGER"
    }, headers=headers)
    assert res.status_code == 403

# =========================================================================
# 4. DIRECTOR ANALYTICS COMPLETE REMOVAL TESTS
# =========================================================================

def test_director_analytics_endpoint_removed():
    headers_dir = get_auth_headers("test_sec_director", "Director123!", "DIRECTOR")
    res = client.get("/api/v1/reports/director-analytics", headers=headers_dir)
    assert res.status_code == 404

def test_director_dashboard_ceo_endpoint_preserved():
    headers_dir = get_auth_headers("test_sec_director", "Director123!", "DIRECTOR")
    res = client.get("/api/v1/reports/ceo", headers=headers_dir)
    assert res.status_code == 200
    assert res.json().get("success") is True

def test_director_dashboard_restricted_from_bms_admin_and_bf_manager():
    headers_bms = get_auth_headers("test_sec_bms_admin", "BmsAdmin123!", "BMS_ADMIN")
    res = client.get("/api/v1/reports/ceo", headers=headers_bms)
    assert res.status_code == 403

    headers_bf = get_auth_headers("test_sec_bf_mgr", "BfMgr123!", "BMS_BF_MANAGER")
    res_bf = client.get("/api/v1/reports/ceo", headers=headers_bf)
    assert res_bf.status_code == 403

def test_retired_role_cannot_be_assigned():
    headers_it = get_auth_headers("test_sec_it_admin", "Admin123!", "IT_ADMIN")
    db = SessionLocal()
    emp = db.query(Employee).join(User).filter(User.username == "test_sec_candidate_5").first()
    emp_id = emp.employee_id
    db.close()

    res = client.put(f"/api/v1/employees/{emp_id}", json={
        "roleCode": "BMS_DIRECTOR_ANALYTICS"
    }, headers=headers_it)
    assert res.status_code in [400, 422]
    err_msg = (res.json().get("message") or res.json().get("detail") or "").lower()
    assert "retired" in err_msg
