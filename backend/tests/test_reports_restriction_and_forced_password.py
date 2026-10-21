from app.models import User, Employee
from app.core.database import SessionLocal
from app.core.security import verify_password, get_password_hash
from seed.seed_development import seed_database

def test_normal_employee_reports_access_forbidden(client, employee_headers):
    """
    Normal users (EMPLOYEE) must not have access to Reports endpoints.
    Should return 403 Forbidden.
    """
    # 1. /reports/years
    res_years = client.get("/api/v1/reports/years", headers=employee_headers)
    assert res_years.status_code == 403, f"Expected 403 for employee on /reports/years, got {res_years.status_code}: {res_years.text}"

    # 2. /reports/monthly
    res_monthly = client.get("/api/v1/reports/monthly?year=2026&month=10", headers=employee_headers)
    assert res_monthly.status_code == 403, f"Expected 403 for employee on /reports/monthly, got {res_monthly.status_code}: {res_monthly.text}"

    # 3. /reports/export-excel
    res_excel = client.get("/api/v1/reports/export-excel?year=2026&month=10", headers=employee_headers)
    assert res_excel.status_code == 403, f"Expected 403 for employee on /reports/export-excel, got {res_excel.status_code}: {res_excel.text}"

    # 4. /reports/ceo
    res_ceo = client.get("/api/v1/reports/ceo", headers=employee_headers)
    assert res_ceo.status_code == 403, f"Expected 403 for employee on /reports/ceo, got {res_ceo.status_code}: {res_ceo.text}"

def test_authorized_roles_can_access_reports(client, breakfast_admin_headers, finance_headers):
    """
    Explicitly authorized roles (Breakfast Admin, Finance Manager) retain reports access.
    """
    # Breakfast Admin can access years and monthly
    res_ba = client.get("/api/v1/reports/years", headers=breakfast_admin_headers)
    assert res_ba.status_code == 200, f"Expected 200 for breakfast admin, got {res_ba.status_code}"

    # Finance Manager can access years and monthly
    res_fin = client.get("/api/v1/reports/years", headers=finance_headers)
    assert res_fin.status_code == 200, f"Expected 200 for finance manager, got {res_fin.status_code}"

def test_seed_centralized_user_creation_and_idempotency():
    """
    Verifies that:
    1. Users are centrally created in User entity and linked to Employee via user_id.
    2. Repeated seeding does NOT overwrite modified user passwords.
    """
    db = SessionLocal()
    try:
        # Check that user exists centrally
        user = db.query(User).filter(User.username == "vasudev").first()
        assert user is not None
        emp = db.query(Employee).filter(Employee.user_id == user.id).first()
        assert emp is not None
        assert emp.employee_id == "EMP-0001"

        # Change user password directly in DB to test idempotency preservation
        custom_hash = get_password_hash("CustomPreservedPassword999")
        user.password_hash = custom_hash
        db.commit()

        # Re-run seed_database()
        seed_database()

        # Verify password hash was preserved and NOT reverted to default
        db.refresh(user)
        assert user.password_hash == custom_hash
        assert verify_password("CustomPreservedPassword999", user.password_hash)

        # Revert back to original password for subsequent test consistency
        user.password_hash = get_password_hash("Vasudev123")
        db.commit()
    finally:
        db.close()

def test_forced_password_change_blocks_apis_until_changed(client):
    """
    A user with force_password_change=True:
    1. Can log in successfully and receives forcePasswordChange=True in user profile.
    2. Any standard API endpoint returns 403 with error_code='PASSWORD_CHANGE_REQUIRED'.
    3. /auth/me and /auth/change-password remain accessible.
    4. Changing password with wrong current password fails (400).
    5. Changing password with identical new password fails (400).
    6. Changing password successfully clears force_password_change flag.
    7. After password change, standard API endpoints become accessible.
    """
    db = SessionLocal()
    try:
        # Create or fetch test user with force_password_change=True
        test_user = db.query(User).filter(User.username == "test.forcechange").first()
        if not test_user:
            test_user = User(
                username="test.forcechange",
                email="test.forcechange@company.com",
                password_hash=get_password_hash("InitPass123"),
                status="active",
                force_password_change=True,
                is_hard_deleted=False
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        else:
            test_user.password_hash = get_password_hash("InitPass123")
            test_user.force_password_change = True
            db.commit()

        # 1. Login
        login_res = client.post("/api/v1/auth/login", json={
            "username": "test.forcechange",
            "password": "InitPass123"
        })
        assert login_res.status_code == 200
        token = login_res.json()["token"]
        assert login_res.json()["user"]["forcePasswordChange"] is True

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Blocked on regular APIs
        res_blocked = client.get("/api/v1/breakfast/daily-entries", headers=headers)
        assert res_blocked.status_code == 403
        data_blocked = res_blocked.json()
        assert data_blocked.get("error_code") == "PASSWORD_CHANGE_REQUIRED" or "password change" in data_blocked.get("message", "").lower()

        # 3. Allowed on /auth/me
        res_me = client.get("/api/v1/auth/me", headers=headers)
        assert res_me.status_code == 200

        # 4. Wrong current password fails
        res_fail_cur = client.post("/api/v1/auth/change-password", json={
            "currentPassword": "WrongPassword999",
            "newPassword": "BrandNewPassword123",
            "confirmPassword": "BrandNewPassword123"
        }, headers=headers)
        assert res_fail_cur.status_code == 400

        # 5. Same as current password fails
        res_fail_same = client.post("/api/v1/auth/change-password", json={
            "currentPassword": "InitPass123",
            "newPassword": "InitPass123",
            "confirmPassword": "InitPass123"
        }, headers=headers)
        assert res_fail_same.status_code == 400

        # 6. Valid password change succeeds
        res_success = client.post("/api/v1/auth/change-password", json={
            "currentPassword": "InitPass123",
            "newPassword": "BrandNewPassword123",
            "confirmPassword": "BrandNewPassword123"
        }, headers=headers)
        assert res_success.status_code == 200
        assert res_success.json()["success"] is True

        # Flag cleared in DB
        db.refresh(test_user)
        assert test_user.force_password_change is False

        # 7. Standard API is no longer blocked with PASSWORD_CHANGE_REQUIRED
        res_unblocked = client.get("/api/v1/breakfast/daily-entries", headers=headers)
        # Should not be 403 PASSWORD_CHANGE_REQUIRED
        if res_unblocked.status_code == 403:
            assert res_unblocked.json().get("error_code") != "PASSWORD_CHANGE_REQUIRED"
        else:
            assert res_unblocked.status_code in [200, 404]

    finally:
        db.close()
