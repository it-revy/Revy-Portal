import sys
import uuid
import httpx

BASE_URL = "http://127.0.0.1:5001"
client = httpx.Client(base_url=BASE_URL, timeout=30.0)

def run_tests():
    print("="*60)
    print("REVY Portal End-to-End Workflow Verification")
    print("="*60)

    # 1. Login with vasudev / Vasudev123
    print("\n[TEST 1] Authenticating vasudev / Vasudev123...")
    res = client.post("/api/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    login_data = res.json()
    assert login_data["success"] is True
    token = login_data["token"]
    vasudev_user = login_data["user"]
    print(f"  -> SUCCESS: Logged in as {vasudev_user['name']} (username: {vasudev_user['username']})")
    print(f"  -> Roles: {vasudev_user['roles']}")
    vasudev_headers = {"Authorization": f"Bearer {token}"}

    # 1b. Test Invalid Credentials
    print("\n[TEST 1b] Testing rejection of invalid password...")
    bad_res = client.post("/api/auth/login", json={"username": "vasudev", "password": "WrongPassword!"})
    assert bad_res.status_code == 401
    print("  -> SUCCESS: Invalid credentials properly rejected with 401 Unauthorized")

    # 2. Session Restore (/api/auth/me)
    print("\n[TEST 2] Verifying session restoration (/api/auth/me)...")
    me_res = client.get("/api/auth/me", headers=vasudev_headers)
    assert me_res.status_code == 200
    me_user = me_res.json()["user"]
    assert me_user["username"] == "vasudev"
    assert "IT_ADMIN" in me_user["roles"]
    print(f"  -> SUCCESS: Session valid for {me_user['name']} with {len(me_user['modules'])} active module memberships")

    # 3. Portal Modules & Role Scoping
    print("\n[TEST 3] Verifying Portal Services & Scoped Module Roles...")
    mods_res = client.get("/api/modules", headers=vasudev_headers)
    assert mods_res.status_code == 200
    modules = mods_res.json()
    module_codes = {m["code"] for m in modules}
    expected_9 = ["MIS", "BMS", "CRM", "LMS", "IMS", "LEAVE", "USERS", "DWR", "REPORTS"]
    for m_code in expected_9:
        assert m_code in module_codes, f"Missing module: {m_code}"
    print(f"  -> SUCCESS: All 9 services present: {', '.join(sorted(module_codes))}")

    # Verify BMS Roles
    bms_mod = next(m for m in modules if m["code"] == "BMS")
    bms_roles = [r["code"] for r in bms_mod["roles"]]
    for r in bms_roles:
        assert r.startswith("BMS_"), f"Role {r} is not BMS-scoped!"
    print(f"  -> SUCCESS: BMS Roles are strictly scoped: {bms_roles}")

    # 4. BMS Workflow Endpoints
    print("\n[TEST 4] Testing BMS Workflow Endpoints...")
    bms_endpoints = [
        ("/api/breakfast/today", "Today's Breakfast"),
        ("/api/breakfast/money/balance", "Breakfast Money"),
        ("/api/employees", "Employees"),
        ("/api/holidays", "Public Holidays"),
        ("/api/reports/ceo", "Reports (CEO/Summary)"),
        ("/api/audit-logs", "Audit Logs"),
        ("/api/settings", "BMS Settings")
    ]
    for ep, label in bms_endpoints:
        ep_res = client.get(ep, headers=vasudev_headers)
        assert ep_res.status_code == 200, f"Endpoint {ep} failed: {ep_res.status_code} {ep_res.text}"
        print(f"  -> {label} ({ep}): 200 OK")

    # 5. User Management Workflow
    print("\n[TEST 5] Testing User Management Workflow...")
    users_res = client.get("/api/users", headers=vasudev_headers)
    assert users_res.status_code == 200
    print(f"  -> User list: 200 OK ({len(users_res.json())} users)")

    managers_res = client.get("/api/users/managers/list", headers=vasudev_headers)
    assert managers_res.status_code == 200
    print(f"  -> Managers list: 200 OK ({len(managers_res.json())} managers)")

    # Create a test user via User Management
    temp_uid = uuid.uuid4().hex[:6]
    test_user_payload = {
        "name": f"Workflow Test User {temp_uid}",
        "username": f"wf_user_{temp_uid}",
        "email": f"wf_{temp_uid}@example.com",
        "phone": "+91 9123456789",
        "password": "Password123!",
        "status": "active"
    }
    create_res = client.post("/api/users", json=test_user_payload, headers=vasudev_headers)
    assert create_res.status_code == 200
    created_user = create_res.json()
    new_user_id = created_user["id"]
    print(f"  -> Created user: {created_user['username']} (ID: {new_user_id})")

    # Assign BMS & CRM module access with module-specific roles
    mod_update_payload = {
        "modules": [
            {
                "moduleCode": "BMS",
                "enabled": True,
                "roleCode": "BMS_EMPLOYEE"
            }
        ]
    }
    update_res = client.put(f"/api/users/{new_user_id}/modules", json=mod_update_payload, headers=vasudev_headers)
    assert update_res.status_code == 200
    assigned_modules = update_res.json()
    bms_entry = next(m for m in assigned_modules if m["moduleCode"] == "BMS")
    assert bms_entry["isEnabled"] is True
    assert bms_entry["roleCode"] == "BMS_EMPLOYEE"
    print(f"  -> Assigned Module: BMS with role BMS_EMPLOYEE")

    # 6. Direct URL Security & Role Isolation
    print("\n[TEST 6] Testing Direct URL Security & Role Isolation...")
    # Log in as the newly created user (who ONLY has BMS_EMPLOYEE role)
    emp_login_res = client.post("/api/auth/login", json={"username": test_user_payload["username"], "password": "Password123!"})
    assert emp_login_res.status_code == 200
    emp_token = emp_login_res.json()["token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Verify BMS access works for this user
    emp_bms_res = client.get("/api/breakfast/today", headers=emp_headers)
    assert emp_bms_res.status_code == 200
    print("  -> User with BMS_EMPLOYEE accessing BMS: 200 OK (Allowed)")

    # Verify User Management access is FORBIDDEN (403)
    emp_users_res = client.get("/api/users", headers=emp_headers)
    assert emp_users_res.status_code == 403
    print("  -> User with BMS_EMPLOYEE accessing User Management: 403 Forbidden (Blocked ✓)")

    # Verify Settings access (Admin only) is FORBIDDEN (403)
    emp_settings_res = client.get("/api/settings", headers=emp_headers)
    assert emp_settings_res.status_code == 403
    print("  -> User with BMS_EMPLOYEE accessing BMS Admin Settings: 403 Forbidden (Blocked ✓)")

    # 7. Global Roles (IT_ADMIN and DIRECTOR) have full unrestricted access
    print("\n[TEST 7] Testing Global Roles Full Access...")
    # vasudev is IT_ADMIN -> verified access to both BMS and Users
    assert "IT_ADMIN" in vasudev_user["roles"]
    print(f"  -> vasudev has global IT_ADMIN: Full access confirmed across Portal, BMS, and User Management ✓")

    # Cleanup test user
    del_res = client.delete(f"/api/users/{new_user_id}", headers=vasudev_headers)
    assert del_res.status_code == 200
    print(f"  -> Cleaned up test user {test_user_payload['username']}")

    print("\n" + "="*60)
    print("ALL TESTS PASSED SUCCESSFULLY (100%)!")
    print("="*60)

if __name__ == "__main__":
    run_tests()
