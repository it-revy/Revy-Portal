from app.core.database import SessionLocal
from app.models import User, Role, Employee, BreakfastTemporaryRequest

def test_temporary_request_and_daily_calculation(client, auth_headers):
    # 1. Use an existing active employee and set them to PERMANENT_NOT_TAKING
    db = SessionLocal()
    perm_emp = db.query(Employee).filter(Employee.employee_id == "EMP-0006").first()
    assert perm_emp is not None, "EMP-0006 should exist from seed"
    perm_emp.breakfast_participation_type = "PERMANENT_NOT_TAKING"
    perm_emp_id = perm_emp.employee_id
    db.commit()

    target_date = "2026-10-15"

    # Clean up any existing temp requests for target_date
    db.query(BreakfastTemporaryRequest).filter(
        BreakfastTemporaryRequest.employee_id == perm_emp_id,
        BreakfastTemporaryRequest.requested_date == target_date
    ).delete()
    db.commit()
    db.close()

    # 2. Create a one-day request for target_date with decimal quantity 1.5
    create_payload = {
        "employeeId": perm_emp_id,
        "requestedDate": target_date,
        "quantity": 1.5,
        "notes": "Joining team celebration breakfast"
    }
    res = client.post("/api/v1/breakfast/temporary-request", json=create_payload, headers=auth_headers)
    assert res.status_code in [200, 201], res.text
    temp_data = res.json()["data"]
    assert temp_data["employeeId"] == perm_emp_id
    assert temp_data["requestedDate"] == target_date
    assert temp_data["quantity"] == 1.5
    assert temp_data["status"] == "CONFIRMED"
    request_id = temp_data["requestId"]

    # 3. Verify permanent status is UNCHANGED
    db = SessionLocal()
    re_emp = db.query(Employee).filter(Employee.employee_id == perm_emp_id).first()
    assert re_emp.breakfast_participation_type == "PERMANENT_NOT_TAKING"
    db.close()

    # 4. Prevent duplicate request for the same date
    dup_res = client.post("/api/v1/breakfast/temporary-request", json=create_payload, headers=auth_headers)
    assert dup_res.status_code == 400
    assert "already exists" in (dup_res.json().get("message") or str(dup_res.json()))

    # 5. Check daily breakfast calculation includes this request
    daily_res = client.get(f"/api/v1/breakfast/daily-entry?date={target_date}", headers=auth_headers)
    assert daily_res.status_code == 200
    daily_data = daily_res.json()
    
    # Check that perm_emp is in applicableEmployees and marked as isTemporaryRequest
    applicable_emps = daily_data["applicableEmployees"]
    found = next((e for e in applicable_emps if e["employeeId"] == perm_emp_id), None)
    assert found is not None
    assert found["isTemporaryRequest"] is True
    assert found["requestedQuantity"] == 1.5
    assert found["response"] == "TAKING"

    # 6. Edit request quantity
    update_res = client.put(f"/api/v1/breakfast/temporary-requests/{request_id}", json={"quantity": 2.0, "notes": "Updated to 2 portions"}, headers=auth_headers)
    assert update_res.status_code == 200
    assert update_res.json()["data"]["quantity"] == 2.0

    # 7. Cancel request
    cancel_res = client.delete(f"/api/v1/breakfast/temporary-requests/{request_id}", headers=auth_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # Check daily calculation again - should no longer include them
    daily_res_after = client.get(f"/api/v1/breakfast/daily-entry?date={target_date}", headers=auth_headers)
    assert daily_res_after.status_code == 200
    found_after = next((e for e in daily_res_after.json()["applicableEmployees"] if e["employeeId"] == perm_emp_id), None)
    assert found_after is None


def test_finance_manager_rbac(client):
    # Test RBAC using existing seeded users 'shahil' and 'himani'
    # Shahil: password Shahil123
    # Himani: password Himani123
    db = SessionLocal()
    user_shahil = db.query(User).filter(User.username == "shahil").first()
    user_himani = db.query(User).filter(User.username == "himani").first()
    fin_role = db.query(Role).filter(Role.code == "FINANCE_MANAGER").first()

    assert user_shahil is not None
    assert user_himani is not None
    assert fin_role is not None

    # Ensure neither initially has FINANCE_MANAGER
    user_shahil.roles = [r for r in user_shahil.roles if r.code != "FINANCE_MANAGER"]
    user_himani.roles = [r for r in user_himani.roles if r.code != "FINANCE_MANAGER"]
    db.commit()
    db.close()

    # 1. Shahil logs in - no finance role
    login_shahil = client.post("/api/v1/auth/login", json={"username": "shahil", "password": "Shahil123"})
    token_shahil = login_shahil.json()["token"]
    headers_shahil = {"Authorization": f"Bearer {token_shahil}", "X-Role-Used": "EMPLOYEE"}

    res_forbidden = client.get("/api/v1/breakfast/money/requests", headers=headers_shahil)
    assert res_forbidden.status_code == 403

    # 2. Admin assigns FINANCE_MANAGER to Shahil
    db = SessionLocal()
    user_shahil = db.query(User).filter(User.username == "shahil").first()
    fin_role = db.query(Role).filter(Role.code == "FINANCE_MANAGER").first()
    user_shahil.roles.append(fin_role)
    db.commit()
    db.close()

    # Shahil re-logs in with new role
    login_shahil2 = client.post("/api/v1/auth/login", json={"username": "shahil", "password": "Shahil123"})
    token_shahil2 = login_shahil2.json()["token"]
    headers_shahil2 = {"Authorization": f"Bearer {token_shahil2}", "X-Role-Used": "FINANCE_MANAGER"}

    res_allowed = client.get("/api/v1/breakfast/money/requests", headers=headers_shahil2)
    assert res_allowed.status_code == 200

    # 3. Admin removes FINANCE_MANAGER from Shahil and assigns it to Himani
    db = SessionLocal()
    user_shahil = db.query(User).filter(User.username == "shahil").first()
    user_himani = db.query(User).filter(User.username == "himani").first()
    fin_role = db.query(Role).filter(Role.code == "FINANCE_MANAGER").first()
    user_shahil.roles = [r for r in user_shahil.roles if r.code != "FINANCE_MANAGER"]
    user_himani.roles.append(fin_role)
    db.commit()
    db.close()

    # Shahil re-logs in -> forbidden
    login_shahil3 = client.post("/api/v1/auth/login", json={"username": "shahil", "password": "Shahil123"})
    token_shahil3 = login_shahil3.json()["token"]
    headers_shahil3 = {"Authorization": f"Bearer {token_shahil3}", "X-Role-Used": "EMPLOYEE"}
    res_forbidden_again = client.get("/api/v1/breakfast/money/requests", headers=headers_shahil3)
    assert res_forbidden_again.status_code == 403

    # Himani logs in -> allowed
    login_himani = client.post("/api/v1/auth/login", json={"username": "himani", "password": "Himani123"})
    token_himani = login_himani.json()["token"]
    headers_himani = {"Authorization": f"Bearer {token_himani}", "X-Role-Used": "FINANCE_MANAGER"}
    res_himani_allowed = client.get("/api/v1/breakfast/money/requests", headers=headers_himani)
    assert res_himani_allowed.status_code == 200


def test_ceo_report_metrics(client, auth_headers):
    res = client.get("/api/v1/reports/ceo", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    # Verify all expected CEO insights exist
    exec_summary = data["executiveSummary"]
    assert "totalEmployees" in exec_summary
    assert "totalBreakfastTakers" in exec_summary
    assert "totalNonTakers" in exec_summary
    assert "totalBreakfastRequestsMonth" in exec_summary
    assert "dailyRequestedQuantity" in exec_summary
    assert "dailyActualQuantity" in exec_summary
    assert "quantityDifference" in exec_summary
    assert "overallParticipationRate" in exec_summary
    assert "totalMonthlyCost" in exec_summary

    assert "summaries" in data
    assert "daily" in data["summaries"]
    assert "weekly" in data["summaries"]
    assert "monthly" in data["summaries"]

    assert "requestVsActualComparison" in data
    assert "consumptionTrends" in data
    assert "dailyTrend" in data
    assert "departmentBreakdown" in data
