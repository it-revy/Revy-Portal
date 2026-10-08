import os
import sys
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.employees.model import Employee
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.core.security import get_password_hash

client = TestClient(app)

def get_admin_token():
    db = SessionLocal()
    try:
        from app.roles.model import Role
        it_role = db.query(Role).filter(Role.code == "IT_ADMIN").first()
        admin_user = db.query(User).filter(User.username == "test_admin_runner").first()
        if not admin_user:
            admin_user = User(
                name="Test Admin Runner",
                username="test_admin_runner",
                email="test_admin_runner@company.com",
                password_hash=get_password_hash("TestAdminPass123!"),
                status="active"
            )
            if it_role:
                admin_user.roles = [it_role]
            db.add(admin_user)
            db.commit()
        else:
            admin_user.password_hash = get_password_hash("TestAdminPass123!")
            if it_role and it_role not in admin_user.roles:
                admin_user.roles.append(it_role)
            db.commit()
    finally:
        db.close()

    res = client.post("/api/auth/login", json={"username": "test_admin_runner", "password": "TestAdminPass123!"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["token"]

def test_user_centric_architecture_complete():
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}

    uid = uuid.uuid4().hex[:6]
    mgr_username = f"manager_{uid}"
    emp_username = f"user_{uid}"

    # 1. Create Manager User
    mgr_res = client.post("/api/users", headers=headers, json={
        "name": f"Manager {uid.upper()}",
        "username": mgr_username,
        "email": f"{mgr_username}@example.com",
        "phone": "+91 9999988888",
        "password": "Password123!",
        "status": "active"
    })
    assert mgr_res.status_code == 200, f"Create manager failed: {mgr_res.text}"
    mgr_data = mgr_res.json()
    mgr_id = mgr_data["id"]
    assert mgr_data["name"] == f"Manager {uid.upper()}"
    assert mgr_data["hasBmsEmployee"] is False, "New User must NOT automatically be BMS employee"

    # 2. Create Subordinate User with Manager relationship
    user_res = client.post("/api/users", headers=headers, json={
        "name": f"Employee {uid.upper()}",
        "username": emp_username,
        "email": f"{emp_username}@example.com",
        "phone": "+91 8888877777",
        "password": "Password123!",
        "managerId": mgr_id,
        "status": "active"
    })
    assert user_res.status_code == 200, f"Create user failed: {user_res.text}"
    user_data = user_res.json()
    user_id = user_data["id"]
    assert user_data["managerId"] == mgr_id
    assert user_data["managerName"] == f"Manager {uid.upper()}"
    assert user_data["hasBmsEmployee"] is False, "New user must NOT automatically be BMS employee"

    # 3. Test Self-Manager validation error
    self_mgr_res = client.put(f"/api/users/{user_id}", headers=headers, json={
        "managerId": user_id
    })
    assert self_mgr_res.status_code == 400
    assert "cannot be their own manager" in self_mgr_res.text

    # 4. Test Login for User WITHOUT BMS membership
    user_login_res = client.post("/api/auth/login", json={
        "username": emp_username,
        "password": "Password123!"
    })
    assert user_login_res.status_code == 200, f"Login for non-BMS user should succeed: {user_login_res.text}"
    user_token = user_login_res.json()["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 5. Non-BMS user attempting to access BMS API directly must be DENIED (403)
    bms_denied_res = client.get("/api/breakfast/today", headers=user_headers)
    assert bms_denied_res.status_code == 403, f"Expected 403 for non-BMS member, got: {bms_denied_res.status_code}"
    assert "membership in module" in bms_denied_res.text

    # 6. Assign User to CRM and BMS with module-scoped roles
    modules_res = client.get("/api/modules", headers=headers)
    assert modules_res.status_code == 200
    all_mods = modules_res.json()
    bms_mod = next(m for m in all_mods if m["code"] == "BMS")
    crm_mod = next(m for m in all_mods if m["code"] == "CRM")

    update_mods_res = client.put(f"/api/users/{user_id}/modules", headers=headers, json={
        "modules": [
            {
                "moduleCode": "BMS",
                "enabled": True,
                "roleCode": "BMS_EMPLOYEE"
            },
            {
                "moduleCode": "CRM",
                "enabled": True,
                "roleCode": "CRM_SALES_EXECUTIVE"
            }
        ]
    })
    assert update_mods_res.status_code == 200, f"Module update failed: {update_mods_res.text}"
    user_memberships = update_mods_res.json()
    bms_assigned = next(m for m in user_memberships if m["moduleCode"] == "BMS")
    crm_assigned = next(m for m in user_memberships if m["moduleCode"] == "CRM")
    assert bms_assigned["isEnabled"] is True
    assert bms_assigned["roleCode"] == "BMS_EMPLOYEE"
    assert crm_assigned["isEnabled"] is True
    assert crm_assigned["roleCode"] == "CRM_SALES_EXECUTIVE"

    # 7. Check that adding to BMS automatically created/synchronized the BMS Employee record
    check_user_res = client.get(f"/api/users/{user_id}", headers=headers)
    assert check_user_res.status_code == 200
    assert check_user_res.json()["hasBmsEmployee"] is True
    assert check_user_res.json()["employeeId"] is not None

    # 8. User can now access BMS API!
    bms_allowed_res = client.get("/api/breakfast/today", headers=user_headers)
    assert bms_allowed_res.status_code == 200, f"Expected 200 after BMS membership assigned, got: {bms_allowed_res.text}"

    # 9. Test User Deactivation
    deact_res = client.delete(f"/api/users/{user_id}", headers=headers)
    assert deact_res.status_code == 200

    # Inactive user cannot log in
    deact_login_res = client.post("/api/auth/login", json={
        "username": emp_username,
        "password": "Password123!"
    })
    assert deact_login_res.status_code == 403
    assert "Account is deactivated" in deact_login_res.text

    print("\nAll User-Centric Module Architecture tests PASSED successfully!")

if __name__ == "__main__":
    test_user_centric_architecture_complete()
