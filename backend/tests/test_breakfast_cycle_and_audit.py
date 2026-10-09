import os
import sys
from datetime import datetime, date, timezone
import pytest
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.employees.model import Employee
from app.modules.model import UserModuleMembership
from app.users.model import User
from app.breakfast.model import BreakfastSetting, BreakfastReason, BreakfastRecord
from app.audit.model import AuditLog
from app.audit.service import AuditService
from app.core.security import create_access_token
from app.breakfast.date_utils import (
    KOLKATA_TZ,
    get_request_window_for_date,
    is_request_window_open,
    get_applicable_breakfast_date,
    get_breakfast_window_details,
    get_breakfast_cycle_settings
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
# A. Default Request-Window Boundaries for 7 October 2026
# =========================================================================

def test_default_request_window_boundaries():
    target_date = date(2026, 10, 7)
    open_time = "17:30"
    close_time = "08:20"

    w_start, w_end = get_request_window_for_date(target_date, open_time, close_time)
    assert w_start == datetime(2026, 10, 6, 17, 30, 0, tzinfo=KOLKATA_TZ)
    assert w_end == datetime(2026, 10, 7, 8, 20, 0, tzinfo=KOLKATA_TZ)

    # 1. 6 Oct, 17:29:59 IST — closed
    t1 = datetime(2026, 10, 6, 17, 29, 59, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, now=t1, open_time=open_time, close_time=close_time) is False
    assert get_applicable_breakfast_date(t1, open_time, close_time) == date(2026, 10, 7)
    d1 = get_breakfast_window_details(target_date, now=t1, open_time=open_time, close_time=close_time)
    assert d1["isOpen"] is False
    assert d1["statusCode"] == "UPCOMING"

    # 2. 6 Oct, 17:30:00 IST — open
    t2 = datetime(2026, 10, 6, 17, 30, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, now=t2, open_time=open_time, close_time=close_time) is True
    assert get_applicable_breakfast_date(t2, open_time, close_time) == date(2026, 10, 7)
    d2 = get_breakfast_window_details(target_date, now=t2, open_time=open_time, close_time=close_time)
    assert d2["isOpen"] is True
    assert d2["statusCode"] == "OPEN"

    # 3. 6 Oct, 20:00:00 IST — open
    t3 = datetime(2026, 10, 6, 20, 0, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, now=t3, open_time=open_time, close_time=close_time) is True
    assert get_applicable_breakfast_date(t3, open_time, close_time) == date(2026, 10, 7)

    # 4. 7 Oct, 07:30:00 IST — open
    t4 = datetime(2026, 10, 7, 7, 30, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, now=t4, open_time=open_time, close_time=close_time) is True
    assert get_applicable_breakfast_date(t4, open_time, close_time) == date(2026, 10, 7)

    # 5. 7 Oct, 08:19:59 IST — open
    t5 = datetime(2026, 10, 7, 8, 19, 59, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, now=t5, open_time=open_time, close_time=close_time) is True
    assert get_applicable_breakfast_date(t5, open_time, close_time) == date(2026, 10, 7)

    # 6. 7 Oct, 08:20:00 IST — closed
    t6 = datetime(2026, 10, 7, 8, 20, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, now=t6, open_time=open_time, close_time=close_time) is False
    assert get_applicable_breakfast_date(t6, open_time, close_time) == date(2026, 10, 8)
    d6 = get_breakfast_window_details(target_date, now=t6, open_time=open_time, close_time=close_time)
    assert d6["isOpen"] is False
    assert d6["statusCode"] == "CLOSED"

    # 7. 7 Oct, 08:21:00 IST — closed
    t7 = datetime(2026, 10, 7, 8, 21, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, now=t7, open_time=open_time, close_time=close_time) is False
    assert get_applicable_breakfast_date(t7, open_time, close_time) == date(2026, 10, 8)

    # 8. 7 Oct, 17:30:00 IST — opens the 8 October cycle
    t8 = datetime(2026, 10, 7, 17, 30, 0, tzinfo=KOLKATA_TZ)
    assert get_applicable_breakfast_date(t8, open_time, close_time) == date(2026, 10, 8)
    assert is_request_window_open(date(2026, 10, 8), now=t8, open_time=open_time, close_time=close_time) is True
    d8 = get_breakfast_window_details(date(2026, 10, 8), now=t8, open_time=open_time, close_time=close_time)
    assert d8["isOpen"] is True
    assert d8["statusCode"] == "OPEN"


# =========================================================================
# B. Configurable Settings Verification
# =========================================================================

def test_configurable_settings_api():
    admin_token = get_user_token("vasudev")
    headers = {"Authorization": f"Bearer {admin_token}", "X-Role-Used": "IT_ADMIN"}

    # 1. Fetch settings
    res = client.get("/api/v1/settings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "requestOpenTime" in data["settings"]
    assert "requestCloseTime" in data["settings"]
    assert data["settings"]["timezone"] == "Asia/Kolkata"

    # 2. Update to custom cycle: 18:00 to 09:00
    res_update = client.put(
        "/api/v1/settings",
        json={"requestOpenTime": "18:00", "requestCloseTime": "09:00"},
        headers=headers
    )
    assert res_update.status_code == 200
    updated = res_update.json()["settings"]
    assert updated["requestOpenTime"] == "18:00"
    assert updated["requestCloseTime"] == "09:00"
    assert updated["cutoffTime"] == "09:00"

    # 3. Verify custom cycle behavior with 18:00 / 09:00
    target_d = date(2026, 10, 10)
    w_start, w_end = get_request_window_for_date(target_d, "18:00", "09:00")
    assert w_start == datetime(2026, 10, 9, 18, 0, 0, tzinfo=KOLKATA_TZ)
    assert w_end == datetime(2026, 10, 10, 9, 0, 0, tzinfo=KOLKATA_TZ)

    # 4. Invalid times rejection
    res_invalid = client.put(
        "/api/v1/settings",
        json={"requestOpenTime": "25:00"},
        headers=headers
    )
    assert res_invalid.status_code == 400

    # 5. Equal open and close time rejection
    res_equal = client.put(
        "/api/v1/settings",
        json={"requestOpenTime": "09:00", "requestCloseTime": "09:00"},
        headers=headers
    )
    assert res_equal.status_code == 400

    # 6. Revert back to defaults: 17:30 and 08:20
    res_revert = client.put(
        "/api/v1/settings",
        json={"requestOpenTime": "17:30", "requestCloseTime": "08:20"},
        headers=headers
    )
    assert res_revert.status_code == 200
    assert res_revert.json()["settings"]["requestOpenTime"] == "17:30"
    assert res_revert.json()["settings"]["requestCloseTime"] == "08:20"


# =========================================================================
# C. Audit Timestamp IST Fix Verification
# =========================================================================

def test_audit_timestamp_ist_conversion():
    db = SessionLocal()
    audit_svc = AuditService(db)

    # Log a test action
    test_log = audit_svc.log(
        action="TEST_IST_TIMESTAMP_ACTION",
        target_info={"details": "Validating IST display accuracy"}
    )
    audit_id = test_log.audit_id
    db.commit()
    db.close()

    admin_token = get_user_token("vasudev")
    headers = {"Authorization": f"Bearer {admin_token}", "X-Role-Used": "IT_ADMIN"}

    res = client.get(f"/api/v1/audit-logs?search={audit_id}", headers=headers)
    assert res.status_code == 200
    logs = res.json()["logs"]
    assert len(logs) > 0
    matched = [l for l in logs if l["auditId"] == audit_id][0]

    # Check timestamp representation
    # 1. UTC ISO string must end with 'Z'
    assert matched["timestamp"].endswith("Z")
    assert matched["timestampUtc"].endswith("Z")

    # 2. timestampIst must contain +05:30 offset
    assert "+05:30" in matched["timestampIst"]

    # 3. timestampDisplay must contain IST
    assert matched["timestampDisplay"].endswith("IST")

    # 4. Verify exact 5:30 offset math
    dt_utc = datetime.fromisoformat(matched["timestampUtc"].replace("Z", "+00:00"))
    dt_ist = datetime.fromisoformat(matched["timestampIst"])
    assert round(dt_utc.timestamp(), 3) == round(dt_ist.timestamp(), 3)
    diff = dt_ist.utcoffset().total_seconds()
    assert diff == 19800  # 5 hours 30 mins = 19800 seconds

    # Clean up test audit log
    db = SessionLocal()
    db.query(AuditLog).filter(AuditLog.audit_id == audit_id).delete()
    db.commit()
    db.close()


# =========================================================================
# D. Daily Entry & Request Window Integration
# =========================================================================

def test_daily_entry_request_window_metadata():
    admin_token = get_user_token("vasudev")
    headers = {"Authorization": f"Bearer {admin_token}", "X-Role-Used": "IT_ADMIN"}

    res = client.get("/api/v1/breakfast/daily-entry?date=2026-10-07", headers=headers)
    assert res.status_code == 200
    d = res.json()
    assert d["success"] is True
    assert "requestWindow" in d
    rw = d["requestWindow"]
    assert "windowStartDisplay" in rw
    assert "windowEndDisplay" in rw
    assert "isOpen" in rw
    assert "06 Oct 2026" in rw["windowStartDisplay"]
    assert "07 Oct 2026" in rw["windowEndDisplay"]


# =========================================================================
# E. BMS BF Manager Role Restriction Verification
# =========================================================================

def test_bms_bf_manager_rbac_restrictions():
    # Login as test_bf_manager to get official token with role claims
    login_res = client.post("/api/v1/auth/login", json={"username": "test_bf_manager", "password": "BfManager123!"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}", "X-Role-Used": "BMS_BF_MANAGER"}

    # 1. Must be FORBIDDEN from Director Analytics
    res_dir = client.get("/api/v1/reports/director-analytics", headers=headers)
    assert res_dir.status_code in [401, 403]

    # 2. Must be FORBIDDEN from Finance Fund Management
    res_fin = client.get("/api/v1/breakfast/money/requests", headers=headers)
    assert res_fin.status_code in [401, 403]

    # 3. Must be FORBIDDEN from Audit Logs
    res_audit = client.get("/api/v1/audit-logs", headers=headers)
    assert res_audit.status_code in [401, 403]

    # 4. Allowed to view BMS Daily Entry and BMS today
    res_today = client.get("/api/v1/breakfast/today", headers=headers)
    assert res_today.status_code == 200
    assert "requestOpenTime" in res_today.json()
    assert "requestCloseTime" in res_today.json()
