import os
import sys
from datetime import datetime, timezone
import pytest
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.roles.model import Role
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.employees.model import Employee
from app.breakfast.model import BreakfastAdditionalOrder, BreakfastDailyEntry, BreakfastRecord
from app.core.security import get_password_hash
from app.breakfast.date_utils import (
    KOLKATA_TZ,
    get_request_window_for_date,
    is_request_window_open,
    get_applicable_breakfast_date,
    get_breakfast_window_details,
    get_kolkata_now
)

client = TestClient(app)

@pytest.fixture
def bms_bf_manager_user():
    """Create or get a BMS BF Manager user with strictly BMS_BF_MANAGER module role."""
    db = SessionLocal()
    try:
        username = "test_bf_manager"
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                name="BMS BF Manager Test",
                username=username,
                email=f"{username}@company.com",
                password_hash=get_password_hash("BfManager123!"),
                status="active"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            emp = Employee(
                user_id=user.id,
                employee_id="EMP-BFMGR",
                name="BMS BF Manager Test",
                email=f"{username}@company.com",
                department="Operations",
                designation="BF Manager",
                status="active"
            )
            db.add(emp)
            db.commit()

        # Clear global roles so it's strictly a module role
        user.roles = []
        db.commit()

        # Assign BMS module role BMS_BF_MANAGER
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == user.id).delete()
        db.commit()

        bms_mod = db.query(Module).filter(Module.code == "BMS").first()
        assert bms_mod is not None, "BMS module must exist"

        mr_bf = db.query(ModuleRole).filter(
            ModuleRole.module_id == bms_mod.id,
            ModuleRole.code == "BMS_BF_MANAGER"
        ).first()
        assert mr_bf is not None, "BMS_BF_MANAGER module role must exist"

        membership = UserModuleMembership(
            user_id=user.id,
            module_id=bms_mod.id,
            role_id=mr_bf.id,
            is_active=True
        )
        db.add(membership)
        db.commit()

        return username, "BfManager123!"
    finally:
        db.close()


@pytest.fixture
def bf_manager_headers(bms_bf_manager_user):
    username, password = bms_bf_manager_user
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "BMS_BF_MANAGER"
    }


# ==============================================================================
# 1. BMS BF MANAGER ROLE PERMISSIONS AND RBAC ISOLATION TESTS
# ==============================================================================

def test_bf_manager_can_access_normal_bms_functionality(bf_manager_headers):
    """BMS BF Manager must have normal operational access (orders, daily entry, money summary, reports)."""
    # 1. Today status
    res = client.get("/api/v1/breakfast/today", headers=bf_manager_headers)
    assert res.status_code == 200

    # 2. Orders list
    res_orders = client.get("/api/v1/breakfast/orders", headers=bf_manager_headers)
    assert res_orders.status_code == 200

    # 3. Additional orders list
    res_add = client.get("/api/v1/breakfast/additional-orders", headers=bf_manager_headers)
    assert res_add.status_code == 200

    # 4. Breakfast money balance
    res_money = client.get("/api/v1/breakfast/money/balance", headers=bf_manager_headers)
    assert res_money.status_code == 200

    # 5. Monthly report & Excel export
    res_rep = client.get("/api/v1/reports/monthly", headers=bf_manager_headers)
    assert res_rep.status_code == 200

    res_excel = client.get("/api/v1/reports/export-excel", headers=bf_manager_headers)
    assert res_excel.status_code == 200


def test_bf_manager_cannot_access_restricted_endpoints(bf_manager_headers):
    """
    BMS BF Manager MUST NOT have access to:
    1. Director Dashboard (/reports/ceo) -> 403 Forbidden
    2. Director Analytics (/reports/director-analytics) -> 403 Forbidden
    3. Finance Fund Request (/breakfast/money/requests) -> 403 Forbidden
    4. Audit Log (/audit-logs) -> 403 Forbidden
    """
    # 1. Director Dashboard API
    res_ceo = client.get("/api/v1/reports/ceo", headers=bf_manager_headers)
    assert res_ceo.status_code == 403, f"Expected 403 on Director Dashboard API, got {res_ceo.status_code}"

    # 2. Director Analytics API
    res_dir = client.get("/api/v1/reports/director-analytics", headers=bf_manager_headers)
    assert res_dir.status_code == 403, f"Expected 403 on Director Analytics API, got {res_dir.status_code}"

    # 3. Finance Fund Request API
    res_fund = client.get("/api/v1/breakfast/money/requests", headers=bf_manager_headers)
    assert res_fund.status_code == 403, f"Expected 403 on Finance Fund Request API, got {res_fund.status_code}"

    # 4. Audit Log API
    res_audit = client.get("/api/v1/audit-logs", headers=bf_manager_headers)
    assert res_audit.status_code == 403, f"Expected 403 on Audit Log API, got {res_audit.status_code}"


# ==============================================================================
# 2. CLIENT ORDER HEAD COUNT TESTS
# ==============================================================================

def test_client_order_head_count_calculations_and_validation(bf_manager_headers):
    """
    Client Order Head Count tests:
    - Head Count is numeric > 0
    - Calculation uses Head Count instead of total employee count
    - Client A with Head Count 6, Client B with Head Count 3
    - Negative / 0 head count raises 400/422 ValidationError
    """
    target_date = "2026-10-15"

    # Ensure sufficient fund balance in the ledger
    db = SessionLocal()
    from app.breakfast.model import BreakfastMoneyTransaction
    import uuid
    txn = BreakfastMoneyTransaction(
        transaction_id=f"TXN-TEST-{uuid.uuid4().hex[:6]}",
        transaction_date=target_date,
        transaction_time="10:00 AM",
        type="MONEY_RECEIVED",
        amount=50000.0,
        balance_after_transaction=50000.0,
        source="Finance Test Deposit",
        reference_type="DIRECT_DEPOSIT",
        reference_id=f"DEP-{uuid.uuid4().hex[:4]}",
        expense_category="DAILY_BREAKFAST",
        expense_purpose="EMPLOYEE",
        description="Fund replenishment for client order tests",
        created_by="Test Admin"
    )
    db.add(txn)
    db.commit()
    db.close()

    # Test invalid head count <= 0
    invalid_payload = {
        "businessDate": target_date,
        "orderTitle": "Invalid Client Order",
        "clientName": "Test Client",
        "headCount": -3,
        "breakfastItems": [{"name": "Samosa", "unitPrice": 20, "quantity": None}]
    }
    res_invalid = client.post("/api/v1/breakfast/additional-orders", json=invalid_payload, headers=bf_manager_headers)
    assert res_invalid.status_code in [400, 422], f"Expected 400/422 for negative head count, got {res_invalid.status_code}"

    zero_payload = {
        "businessDate": target_date,
        "orderTitle": "Zero Headcount Order",
        "clientName": "Test Client",
        "headCount": 0,
        "breakfastItems": [{"name": "Samosa", "unitPrice": 20, "quantity": None}]
    }
    res_zero = client.post("/api/v1/breakfast/additional-orders", json=zero_payload, headers=bf_manager_headers)
    assert res_zero.status_code in [400, 422], f"Expected 400/422 for zero head count, got {res_zero.status_code}"

    # Client A: Head Count = 6, Unit Price = 25 -> Expected Total = 6 * 25 = 150
    client_a_payload = {
        "businessDate": target_date,
        "orderTitle": "Client A Breakfast Order",
        "clientName": "Client A",
        "headCount": 6,
        "breakfastItems": [{"name": "Poha Plate", "unitPrice": 25, "quantity": None}],
        "commonItems": []
    }
    res_a = client.post("/api/v1/breakfast/additional-orders", json=client_a_payload, headers=bf_manager_headers)
    assert res_a.status_code == 200, f"Create Client A order failed: {res_a.text}"
    order_a = res_a.json()["order"]
    assert order_a["headCount"] == 6
    assert order_a["clientName"] == "Client A"
    assert order_a["totalCost"] == 150.0  # 6 * 25
    assert order_a["breakfastItems"][0]["quantity"] == 6.0

    # Client B: Head Count = 3, Unit Price = 40 -> Expected Total = 3 * 40 = 120
    client_b_payload = {
        "businessDate": target_date,
        "orderTitle": "Client B Executive Snacks",
        "clientName": "Client B",
        "headCount": 3,
        "breakfastItems": [{"name": "Sandwich", "unitPrice": 40, "quantity": None}],
        "commonItems": []
    }
    res_b = client.post("/api/v1/breakfast/additional-orders", json=client_b_payload, headers=bf_manager_headers)
    assert res_b.status_code == 200, f"Create Client B order failed: {res_b.text}"
    order_b = res_b.json()["order"]
    assert order_b["headCount"] == 3
    assert order_b["clientName"] == "Client B"
    assert order_b["totalCost"] == 120.0  # 3 * 40
    assert order_b["breakfastItems"][0]["quantity"] == 3.0


# ==============================================================================
# 3. ORDER SORTING - ASCENDING TESTS
# ==============================================================================

def test_orders_sorting_ascending(bf_manager_headers):
    """
    Orders must be displayed and exported in ascending order:
    Oldest first, newest last.
    """
    # 1. Check /orders API default sort order is asc
    res = client.get("/api/v1/breakfast/orders", headers=bf_manager_headers)
    assert res.status_code == 200
    data = res.json()
    orders = data.get("orders", [])
    if len(orders) > 1:
        dates = [o["businessDate"] for o in orders]
        assert dates == sorted(dates), f"Orders list should be ascending: {dates}"

    # 2. Check report orderSummary is strictly ascending
    res_rep = client.get("/api/v1/reports/monthly", headers=bf_manager_headers)
    assert res_rep.status_code == 200
    rep_orders = res_rep.json().get("orderSummary", [])
    if len(rep_orders) > 1:
        rep_dates = [o["businessDate"] for o in rep_orders]
        assert rep_dates == sorted(rep_dates), f"Report orderSummary must be ascending: {rep_dates}"


# ==============================================================================
# 4. TIMEZONE & REQUEST WINDOW BOUNDARY TESTS (Asia/Kolkata)
# ==============================================================================

def test_timezone_is_strictly_kolkata():
    """Verify Asia/Kolkata timezone is used and current time is timezone-aware."""
    now_ist = get_kolkata_now()
    assert now_ist.tzinfo is not None
    assert str(now_ist.tzinfo) == "Asia/Kolkata"
    # UTC offset for IST must be +05:30 (19800 seconds)
    assert now_ist.utcoffset().total_seconds() == 19800


def test_breakfast_request_window_exact_boundaries():
    """
    Test exact requirement boundaries for breakfast date: 08-Oct-2026
    Window Start: 07-Oct-2026 17:30 IST
    Window End:   08-Oct-2026 08:20 IST
    Inclusive/Exclusive rule: window_start <= now < window_end
    """
    target_date = "2026-10-08"
    w_start, w_end = get_request_window_for_date(target_date)

    assert w_start == datetime(2026, 10, 7, 17, 30, 0, tzinfo=KOLKATA_TZ)
    assert w_end == datetime(2026, 10, 8, 8, 20, 0, tzinfo=KOLKATA_TZ)

    # 1. Before opening: 07-Oct-2026 17:29:59 IST -> CLOSED
    t_before = datetime(2026, 10, 7, 17, 29, 59, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, t_before) is False

    # 2. Opening boundary: 07-Oct-2026 17:30:00 IST -> OPEN
    t_open = datetime(2026, 10, 7, 17, 30, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, t_open) is True

    # 3. During window: 07-Oct-2026 20:00:00 IST -> OPEN
    t_evening = datetime(2026, 10, 7, 20, 0, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, t_evening) is True

    # 4. Next morning: 08-Oct-2026 07:30:00 IST -> OPEN
    t_morning = datetime(2026, 10, 8, 7, 30, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, t_morning) is True

    # 5. One second before closing: 08-Oct-2026 08:19:59 IST -> OPEN
    t_almost_closed = datetime(2026, 10, 8, 8, 19, 59, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, t_almost_closed) is True

    # 6. Closing boundary: 08-Oct-2026 08:20:00 IST -> CLOSED
    t_closed = datetime(2026, 10, 8, 8, 20, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, t_closed) is False

    # 7. After closing: 08-Oct-2026 08:21:00 IST -> CLOSED
    t_after = datetime(2026, 10, 8, 8, 21, 0, tzinfo=KOLKATA_TZ)
    assert is_request_window_open(target_date, t_after) is False


def test_automatic_breakfast_date_detection():
    """
    Intelligent date detection based on current IST time:
    - 7 Oct 16:00 IST -> upcoming date is 8 Oct (window not open yet)
    - 7 Oct 17:30 IST -> date is 8 Oct (window opens)
    - 8 Oct 07:00 IST -> date is 8 Oct (window still accepting)
    - 8 Oct 08:20 IST -> window closes
    - 8 Oct 18:00 IST -> next window is for 9 Oct
    """
    # 7 Oct 16:00 IST
    d1 = get_applicable_breakfast_date(datetime(2026, 10, 7, 16, 0, 0, tzinfo=KOLKATA_TZ))
    assert str(d1) == "2026-10-08"

    # 7 Oct 17:30 IST
    d2 = get_applicable_breakfast_date(datetime(2026, 10, 7, 17, 30, 0, tzinfo=KOLKATA_TZ))
    assert str(d2) == "2026-10-08"

    # 8 Oct 07:00 IST
    d3 = get_applicable_breakfast_date(datetime(2026, 10, 8, 7, 0, 0, tzinfo=KOLKATA_TZ))
    assert str(d3) == "2026-10-08"

    # 8 Oct 18:00 IST -> Next day: 9 Oct
    d4 = get_applicable_breakfast_date(datetime(2026, 10, 8, 18, 0, 0, tzinfo=KOLKATA_TZ))
    assert str(d4) == "2026-10-09"
