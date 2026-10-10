import os
import sys
from datetime import datetime, date, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.employees.model import Employee
from app.breakfast.model import BreakfastRecord, BreakfastDailyEntry, BreakfastSetting
from app.audit.model import AuditLog
from app.audit.service import AuditService
from app.core.security import create_access_token
from app.breakfast.date_utils import (
    KOLKATA_TZ,
    get_request_window_for_date,
    is_request_window_open,
    get_applicable_breakfast_date,
    get_authoritative_breakfast_date,
    get_breakfast_window_details,
    serialize_utc_timestamp
)

client = TestClient(app)

def get_user_token(username: str):
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    emp_id = u.employee.employee_id if u and u.employee else ""
    user_id = str(u.id) if u else "test-id"
    db.close()
    return create_access_token(data={"sub": username, "username": username, "userId": user_id, "employeeId": emp_id})


# =========================================================================
# Scenario A: Overnight Breakfast Window & Authoritative Business Date
# =========================================================================

def test_overnight_breakfast_window_and_boundaries():
    """
    Validates Section 4 table explicitly:
    Window: opens Oct 8 at 16:30 IST, closes Oct 9 at 08:20 IST.
    """
    open_time = "16:30"
    close_time = "08:20"

    # 1. Oct 8, 4:29 PM IST -> Previous active cycle (Oct 8); next cycle (Oct 9) not yet open
    t_429 = datetime(2026, 10, 8, 16, 29, 0, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_429, open_time, close_time) == date(2026, 10, 8)
    assert is_request_window_open(date(2026, 10, 9), now=t_429, open_time=open_time, close_time=close_time) is False

    # 2. Oct 8, 4:30 PM IST -> Next cycle opens, active breakfast business date is Oct 9
    t_430 = datetime(2026, 10, 8, 16, 30, 0, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_430, open_time, close_time) == date(2026, 10, 9)
    assert is_request_window_open(date(2026, 10, 9), now=t_430, open_time=open_time, close_time=close_time) is True

    # 3. Oct 8, 9:40 PM IST -> Evening response window is active for Oct 9
    t_940 = datetime(2026, 10, 8, 21, 40, 0, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_940, open_time, close_time) == date(2026, 10, 9)
    assert is_request_window_open(date(2026, 10, 9), now=t_940, open_time=open_time, close_time=close_time) is True

    # 4. Oct 9, 12:00 AM IST (midnight) -> Active date is Oct 9, window is open
    t_midnight = datetime(2026, 10, 9, 0, 0, 0, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_midnight, open_time, close_time) == date(2026, 10, 9)
    assert is_request_window_open(date(2026, 10, 9), now=t_midnight, open_time=open_time, close_time=close_time) is True

    # 5. Oct 9, 8:19:59 AM IST -> Active date is Oct 9, window is still open
    t_819 = datetime(2026, 10, 9, 8, 19, 59, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_819, open_time, close_time) == date(2026, 10, 9)
    assert is_request_window_open(date(2026, 10, 9), now=t_819, open_time=open_time, close_time=close_time) is True

    # 6. Oct 9, 8:20:00 AM IST -> Closing boundary: window closes, active date remains Oct 9
    t_820 = datetime(2026, 10, 9, 8, 20, 0, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_820, open_time, close_time) == date(2026, 10, 9)
    assert is_request_window_open(date(2026, 10, 9), now=t_820, open_time=open_time, close_time=close_time) is False

    # 7. Oct 9, 12:00 PM IST (after closing, daytime operational cycle) -> Active date remains Oct 9
    t_noon = datetime(2026, 10, 9, 12, 0, 0, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_noon, open_time, close_time) == date(2026, 10, 9)
    assert is_request_window_open(date(2026, 10, 9), now=t_noon, open_time=open_time, close_time=close_time) is False

    # 8. Oct 9, 4:29:59 PM IST -> Still Oct 9
    t_next_429 = datetime(2026, 10, 9, 16, 29, 59, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_next_429, open_time, close_time) == date(2026, 10, 9)

    # 9. Oct 9, 4:30:00 PM IST -> Next cycle opens for Oct 10
    t_next_430 = datetime(2026, 10, 9, 16, 30, 0, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t_next_430, open_time, close_time) == date(2026, 10, 10)
    assert is_request_window_open(date(2026, 10, 10), now=t_next_430, open_time=open_time, close_time=close_time) is True


# =========================================================================
# Scenario B: Previous-Day Response Isolation (Issue 1 Root Cause Fix)
# =========================================================================

def test_previous_day_response_isolation():
    """
    Validates that:
    1. Employee submitted TAKING for Oct 8.
    2. Active window for Oct 9 opens.
    3. Employee has no response for Oct 9.
    4. /breakfast/today returns todayRecord: null and responseStatus: NO_RESPONSE.
    5. Oct 8 history is completely isolated and preserved.
    """
    db = SessionLocal()
    # Find active employee
    emp = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False).first()
    assert emp is not None
    user = emp.user
    assert user is not None
    token = get_user_token(user.username)
    headers = {"Authorization": f"Bearer {token}"}

    # Clean up any test records for 2026-10-08 and 2026-10-09
    db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == emp.employee_id,
        BreakfastRecord.business_date.in_(["2026-10-08", "2026-10-09"])
    ).delete()
    db.commit()

    # Step 1: Create an Oct 8 response record: TAKING
    rec_oct8 = BreakfastRecord(
        record_id=f"BRK-20261008-{emp.employee_id}",
        employee_id=emp.employee_id,
        employee_name=emp.name,
        business_date="2026-10-08",
        response="YES",
        employee_response="TAKING",
        actual_status="TAKEN",
        source="EMPLOYEE",
        submitted_at=datetime(2026, 10, 8, 7, 30, 0, tzinfo=timezone.utc),
        history=[]
    )
    db.add(rec_oct8)
    db.commit()

    # Step 2: Query /breakfast/today for 2026-10-09
    res = client.get("/api/v1/breakfast/today?date=2026-10-09", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["businessDate"] == "2026-10-09"

    # Step 3: MUST NOT fall back to Oct 8 record
    assert data["todayRecord"] is None, "todayRecord must be null when employee has not responded for active business date"
    assert data["responseStatus"] == "NO_RESPONSE", "responseStatus must be NO_RESPONSE"

    # Step 4: Verify Oct 8 history remains intact
    hist_res = client.get("/api/v1/breakfast/history", headers=headers)
    assert hist_res.status_code == 200
    hist_records = hist_res.json()["records"]
    oct8_match = [r for r in hist_records if r["businessDate"] == "2026-10-08"]
    assert len(oct8_match) == 1
    assert oct8_match[0]["response"] == "YES"
    assert oct8_match[0]["employeeResponse"] == "TAKING"

    # Step 5: Clean up
    db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == emp.employee_id,
        BreakfastRecord.business_date.in_(["2026-10-08", "2026-10-09"])
    ).delete()
    db.commit()
    db.close()


# =========================================================================
# Scenario C: Daily Entry Date Initialization and No Stale Pollution
# =========================================================================

def test_daily_entry_authoritative_initialization():
    admin_token = get_user_token("vasudev")
    headers = {"Authorization": f"Bearer {admin_token}", "X-Role-Used": "IT_ADMIN"}

    # 1. Calling without date returns the authoritative business date
    res = client.get("/api/v1/breakfast/daily-entry", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "businessDate" in data
    assert len(data["businessDate"]) == 10  # YYYY-MM-DD

    # 2. Calling with historical date loads historical records for that date only
    res_hist = client.get("/api/v1/breakfast/daily-entry?date=2026-10-05", headers=headers)
    assert res_hist.status_code == 200
    assert res_hist.json()["businessDate"] == "2026-10-05"


# =========================================================================
# Scenario D: Request vs Actual Status Lifecycle Semantics
# =========================================================================

def test_request_vs_actual_status_lifecycle():
    """
    Validates:
    - TAKING -> TAKEN
    - NOT_TAKING -> NOT_TAKEN
    - NO_RESPONSE -> NO_RESPONSE
    - Admin override on employee without prior response preserves NO_RESPONSE request status
    """
    db = SessionLocal()
    emp = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False).first()
    assert emp is not None
    admin_token = get_user_token("vasudev")
    admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Role-Used": "IT_ADMIN"}

    test_date = "2026-10-15"
    db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == emp.employee_id,
        BreakfastRecord.business_date == test_date
    ).delete()
    db.commit()

    # Admin marks actual status TAKEN for employee who has not submitted
    override_res = client.put(
        "/api/v1/breakfast/actual-status",
        json={
            "employeeId": emp.employee_id,
            "businessDate": test_date,
            "actualStatus": "TAKEN"
        },
        headers=admin_headers
    )
    assert override_res.status_code == 200
    rec_data = override_res.json()["record"]
    assert rec_data["actualStatus"] == "TAKEN"
    assert rec_data["actualStatusSource"] == "ADMIN_OVERRIDE"
    # Crucial: employee response must remain NO_RESPONSE, not falsely recorded as NO or NOT_TAKING
    assert rec_data["employeeResponse"] == "NO_RESPONSE"

    # Clean up
    db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == emp.employee_id,
        BreakfastRecord.business_date == test_date
    ).delete()
    db.commit()
    db.close()


# =========================================================================
# Scenario E: Timestamp Instant & IST Consistency
# =========================================================================

def test_timestamp_instant_and_ist_consistency():
    """
    Validates UTC instant serialization ends with 'Z' and matches IST offset exactly.
    """
    # 1. UTC instant serialization
    test_utc = datetime(2026, 10, 8, 11, 0, 0, tzinfo=timezone.utc)
    serialized = serialize_utc_timestamp(test_utc)
    assert serialized == "2026-10-08T11:00:00Z"

    # Naive assumed UTC
    test_naive = datetime(2026, 10, 8, 11, 0, 0)
    assert serialize_utc_timestamp(test_naive) == "2026-10-08T11:00:00Z"

    # In IST: 11:00 UTC = 16:30 IST
    dt_ist = test_utc.astimezone(KOLKATA_TZ)
    assert dt_ist.hour == 16
    assert dt_ist.minute == 30

    # 2. Audit log timestamp inspection
    db = SessionLocal()
    audit_svc = AuditService(db)
    test_log = audit_svc.log(
        action="TEST_TIMESTAMP_CONSISTENCY",
        target_info={"details": "Testing UTC instant Z and IST representation"}
    )
    audit_id = test_log.audit_id
    db.commit()
    db.close()

    admin_token = get_user_token("vasudev")
    headers = {"Authorization": f"Bearer {admin_token}", "X-Role-Used": "IT_ADMIN"}
    res = client.get(f"/api/v1/audit-logs?search={audit_id}", headers=headers)
    assert res.status_code == 200
    logs = res.json()["logs"]
    matched = [l for l in logs if l["auditId"] == audit_id][0]

    assert matched["timestamp"].endswith("Z")
    assert "+05:30" in matched["timestampIst"]

    # Clean up
    db = SessionLocal()
    db.query(AuditLog).filter(AuditLog.audit_id == audit_id).delete()
    db.commit()
    db.close()


# =========================================================================
# Scenario G: End-to-End Workflow Reproduction Test
# =========================================================================

def test_end_to_end_reported_scenario():
    """
    Full reproduction of the reported issue:
    1. Employee had TAKING for Oct 8.
    2. Oct 9 window opens. Employee has not responded for Oct 9.
    3. Employee page must show NO_RESPONSE for Oct 9.
    4. Daily Entry must show NO_RESPONSE for Oct 9.
    5. Historical Oct 8 response remains unchanged.
    6. Employee submits response for Oct 9 (TAKING).
    7. Employee page and Daily Entry show Oct 9 response.
    8. Audit record records business date Oct 9 and correct event timestamp.
    """
    db = SessionLocal()
    emp = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False).first()
    assert emp is not None
    user = emp.user
    token = get_user_token(user.username)
    emp_headers = {"Authorization": f"Bearer {token}"}
    admin_token = get_user_token("vasudev")
    admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Role-Used": "IT_ADMIN"}

    # Clean up test dates
    db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == emp.employee_id,
        BreakfastRecord.business_date.in_(["2026-10-08", "2026-10-09"])
    ).delete()
    db.commit()

    # Step 1: Oct 8 morning response: TAKING
    oct8_record = BreakfastRecord(
        record_id=f"BRK-20261008-{emp.employee_id}",
        employee_id=emp.employee_id,
        employee_name=emp.name,
        business_date="2026-10-08",
        response="YES",
        employee_response="TAKING",
        actual_status="TAKEN",
        source="EMPLOYEE",
        submitted_at=datetime(2026, 10, 8, 7, 45, 0, tzinfo=timezone.utc),
        history=[]
    )
    db.add(oct8_record)
    db.commit()

    # Step 2: Oct 9 request window opened, employee has not responded for Oct 9
    # Employee views status for Oct 9:
    today_res = client.get("/api/v1/breakfast/today?date=2026-10-09", headers=emp_headers)
    assert today_res.status_code == 200
    today_data = today_res.json()
    assert today_data["businessDate"] == "2026-10-09"
    assert today_data["todayRecord"] is None
    assert today_data["responseStatus"] == "NO_RESPONSE"

    # Daily entry views status for Oct 9:
    daily_res = client.get("/api/v1/breakfast/daily-entry?date=2026-10-09", headers=admin_headers)
    assert daily_res.status_code == 200
    emp_rows = [e for e in daily_res.json()["applicableEmployees"] if e["employeeId"] == emp.employee_id]
    assert len(emp_rows) == 1
    assert emp_rows[0]["response"] == "NO_RESPONSE"
    assert emp_rows[0]["actualStatus"] == "NO_RESPONSE"

    # Historical Oct 8 is still TAKING:
    hist_res = client.get("/api/v1/breakfast/history", headers=emp_headers)
    oct8_recs = [r for r in hist_res.json()["records"] if r["businessDate"] == "2026-10-08"]
    assert len(oct8_recs) == 1
    assert oct8_recs[0]["response"] == "YES"

    # Step 3: Employee submits response for Oct 9 (TAKING)
    # Set TESTING environment or mock window open
    os.environ["TESTING"] = "1"
    sub_res = client.post(
        "/api/v1/breakfast/submit",
        json={"businessDate": "2026-10-09", "response": "YES"},
        headers=emp_headers
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["success"] is True

    # Step 4: Employee views status again: now has Oct 9 record
    today_res_2 = client.get("/api/v1/breakfast/today?date=2026-10-09", headers=emp_headers)
    assert today_res_2.status_code == 200
    today_data_2 = today_res_2.json()
    assert today_data_2["todayRecord"] is not None
    assert today_data_2["todayRecord"]["businessDate"] == "2026-10-09"
    assert today_data_2["todayRecord"]["response"] == "YES"
    assert today_data_2["responseStatus"] == "TAKING"
    assert today_data_2["todayRecord"]["submittedAt"].endswith("Z")

    # Daily entry reflects Oct 9 response
    daily_res_2 = client.get("/api/v1/breakfast/daily-entry?date=2026-10-09", headers=admin_headers)
    emp_rows_2 = [e for e in daily_res_2.json()["applicableEmployees"] if e["employeeId"] == emp.employee_id]
    assert emp_rows_2[0]["response"] == "TAKING"
    assert emp_rows_2[0]["actualStatus"] == "TAKEN"

    # Oct 8 record still unchanged:
    hist_res_2 = client.get("/api/v1/breakfast/history", headers=emp_headers)
    oct8_recs_2 = [r for r in hist_res_2.json()["records"] if r["businessDate"] == "2026-10-08"]
    assert len(oct8_recs_2) == 1
    assert oct8_recs_2[0]["response"] == "YES"

    # Step 5: Clean up
    db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == emp.employee_id,
        BreakfastRecord.business_date.in_(["2026-10-08", "2026-10-09"])
    ).delete()
    db.commit()
    db.close()


# =========================================================================
# Scenario H: Submit Endpoint Configuration, NameError Prevention & Validation
# =========================================================================

def test_submit_endpoint_configuration_and_validation():
    """
    Validates:
    1. settings is properly imported and defined in breakfast/router.py.
    2. POST /api/breakfast/submit and POST /api/v1/breakfast/submit both work.
    3. When TESTING env var is NOT set, settings.ENVIRONMENT is evaluated without NameError.
    4. Invalid businessDate returns 400 validation error, not 500 NameError.
    5. Invalid response values return 400 validation error.
    6. When outside request window in production mode, returns 400 request window closed error.
    """
    from app.core.config import settings

    db = SessionLocal()
    emp = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False).first()
    assert emp is not None
    user = emp.user
    token = get_user_token(user.username)
    emp_headers = {"Authorization": f"Bearer {token}"}
    db.close()

    # 1. Test when TESTING is unset and settings.ENVIRONMENT is evaluated
    old_testing = os.environ.pop("TESTING", None)
    old_env = settings.ENVIRONMENT

    try:
        # A. Invalid date format must raise 400 ValidationError, NEVER 500 NameError
        settings.ENVIRONMENT = "development"
        res_invalid_date = client.post(
            "/api/breakfast/submit",
            json={"businessDate": "2026-99-99", "response": "YES"},
            headers=emp_headers
        )
        assert res_invalid_date.status_code == 400
        assert "Invalid businessDate format" in res_invalid_date.json()["message"]

        # B. In production/development mode: closed window raises 400 window closed, NEVER 500 NameError
        settings.ENVIRONMENT = "production"
        res_closed = client.post(
            "/api/breakfast/submit",
            json={"businessDate": "2020-01-01", "response": "YES"},
            headers=emp_headers
        )
        assert res_closed.status_code == 400
        assert "window is closed" in res_closed.json()["message"].lower()

        # C. Under test environment (is_testing=True via settings.ENVIRONMENT="test"):
        # Invalid response option must raise 400 ValidationError
        settings.ENVIRONMENT = "test"
        res_invalid_resp = client.post(
            "/api/breakfast/submit",
            json={"businessDate": "2026-10-09", "response": "MAYBE"},
            headers=emp_headers
        )
        assert res_invalid_resp.status_code == 400
        assert "Response must be YES or NO" in res_invalid_resp.json()["message"]

        # D. Response NO without reasonCode must raise 400 ValidationError
        res_no_reason = client.post(
            "/api/breakfast/submit",
            json={"businessDate": "2026-10-09", "response": "NO"},
            headers=emp_headers
        )
        assert res_no_reason.status_code == 400
        assert "reason" in res_no_reason.json()["message"].lower()

        # E. Successful submission via /api/breakfast/submit (test environment detection enabled)
        res_success_api = client.post(
            "/api/breakfast/submit",
            json={"businessDate": "2026-10-20", "response": "YES"},
            headers=emp_headers
        )
        assert res_success_api.status_code == 200
        assert res_success_api.json()["success"] is True
        assert res_success_api.json()["record"]["businessDate"] == "2026-10-20"
        assert res_success_api.json()["record"]["employeeResponse"] == "TAKING"

        # F. Also verify /api/v1/breakfast/submit works identically
        res_success_v1 = client.post(
            "/api/v1/breakfast/submit",
            json={"businessDate": "2026-10-20", "response": "YES"},
            headers=emp_headers
        )
        assert res_success_v1.status_code == 200
        assert res_success_v1.json()["success"] is True

        # Clean up test record
        db = SessionLocal()
        db.query(BreakfastRecord).filter(
            BreakfastRecord.employee_id == emp.employee_id,
            BreakfastRecord.business_date == "2026-10-20"
        ).delete()
        db.commit()
        db.close()

    finally:
        # Restore environment settings
        settings.ENVIRONMENT = old_env
        if old_testing is not None:
            os.environ["TESTING"] = old_testing

