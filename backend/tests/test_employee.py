import pytest

def test_list_employees(client, auth_headers):
    res = client.get("/api/v1/employees", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["count"] >= 1
    assert any(e["username"] == "vasudev" for e in data["employees"])

def test_create_and_update_employee(client, auth_headers):
    import uuid
    uid = uuid.uuid4().hex[:6]
    
    # 1. BMS must NEVER create users with raw password - verify strict rejection
    invalid_bms_create = {
        "username": f"legacy_bms_{uid}",
        "name": "Legacy BMS Employee",
        "email": f"legacy_bms_{uid}@company.com",
        "password": "Password123!",
        "department": "Engineering",
        "designation": "Junior Engineer",
    }
    res_invalid = client.post("/api/v1/employees", json=invalid_bms_create, headers=auth_headers)
    assert res_invalid.status_code == 400
    msg = res_invalid.json().get("message") or res_invalid.json().get("detail", "")
    assert "User Management" in msg

    # 2. Correct architecture: Create user via Central User Management
    user_payload = {
        "username": f"central_user_{uid}",
        "name": f"Central User {uid}",
        "email": f"central_user_{uid}@company.com",
        "password": "ValidPassword123!",
        "department": "Engineering",
        "designation": "Software Engineer",
        "status": "active"
    }
    res_user = client.post("/api/v1/users", json=user_payload, headers=auth_headers)
    assert res_user.status_code == 200, f"User creation failed: {res_user.text}"
    user_data = res_user.json()
    user_id = user_data.get("id") or user_data.get("user", {}).get("id")

    # 3. Add existing user to BMS
    assign_payload = {
        "userId": user_id,
        "department": "Engineering",
        "designation": "Software Engineer",
        "breakfastParticipationType": "ALL_DAYS",
        "bmsRole": "BMS_EMPLOYEE"
    }
    res_assign = client.post("/api/v1/employees/assign-user", json=assign_payload, headers=auth_headers)
    assert res_assign.status_code == 200, f"Assign to BMS failed: {res_assign.text}"
    emp = res_assign.json()["employee"]
    emp_id = emp["employeeId"]
    assert emp["userId"] == user_id

    # 4. Duplicate prevention test
    res_dup = client.post("/api/v1/employees/assign-user", json=assign_payload, headers=auth_headers)
    assert res_dup.status_code == 400
    msg_dup = res_dup.json().get("message") or res_dup.json().get("detail", "")
    assert "already" in msg_dup.lower()

    # 5. Get BMS employee details
    res_get = client.get(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["employee"]["name"] == f"Central User {uid}"

    # 6. Update BMS employee profile
    res_upd = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"designation": "Lead Engineer", "phone": "9876543210"},
        headers=auth_headers
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["employee"]["designation"] == "Lead Engineer"

    # 7. BMS cannot reset passwords
    res_reset = client.post(
        f"/api/v1/employees/{emp_id}/reset-password",
        json={"newPassword": "NewPassword123!", "confirmPassword": "NewPassword123!"},
        headers=auth_headers
    )
    assert res_reset.status_code == 400
    msg_reset = res_reset.json().get("detail") or res_reset.json().get("message", "")
    assert "User Management" in msg_reset

    # 8. Remove/deactivate from BMS
    res_deact = client.delete(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert res_deact.status_code == 200
    assert res_deact.json()["employee"]["status"] == "inactive"

    # 9. Verify central user still exists and remains active
    res_user_check = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert res_user_check.status_code == 200
    user_check_data = res_user_check.json()
    status_val = user_check_data.get("status") or user_check_data.get("user", {}).get("status")
    assert status_val == "active"

