import os
import sys
from datetime import datetime, timezone
import pytest

# Ensure TESTING=1
os.environ["TESTING"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.models  # Register all SQLAlchemy models
from app.core.database import SessionLocal, init_db
from app.core.init_roles import ensure_roles_and_permissions
from app.core.init_modules import ensure_modules_and_memberships
from app.employees.model import Employee
from app.users.model import User
from app.breakfast.beverage_model import BmsBeverage, BmsBeverageEntry
from app.breakfast.beverage_service import BeverageService
from app.breakfast.beverage_schema import (
    BeverageCreateRequest,
    BeverageUpdateRequest,
    BeverageEntrySubmitRequest,
    BeverageAdminEntryCreateRequest,
    BeverageAdminEntryUpdateRequest
)
from app.reports.service import ReportService
from app.core.exceptions import ValidationError, NotFoundError, PermissionDeniedError
from app.breakfast.date_utils import get_kolkata_date_string
from app.audit.model import AuditLog


class DummyActor:
    def __init__(self, username: str, employee_id: str, name: str, active_role: str, permissions=None, is_global_admin=False):
        self.username = username
        self.employee_id = employee_id
        self.name = name
        self.active_role = active_role
        self.permissions = permissions or []
        self.all_permissions = self.permissions
        self.is_global_admin = is_global_admin
        self.roles = [active_role]


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    ensure_roles_and_permissions()
    ensure_modules_and_memberships()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def employee_actor(db):
    emp = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False).first()
    assert emp is not None, "At least one active employee must exist in seed"
    return DummyActor(
        username=emp.user.username if emp.user else "emp_test",
        employee_id=emp.employee_id,
        name=emp.name,
        active_role="BMS_EMPLOYEE",
        permissions=["breakfast.submit", "breakfast.view_own", "breakfast.history_own", "bms.beverages.view", "bms.beverages.submit"]
    )


@pytest.fixture
def admin_actor():
    return DummyActor(
        username="vasudev",
        employee_id="DIR001",
        name="Vasudev Kava",
        active_role="IT_ADMIN",
        permissions=["*"],
        is_global_admin=True
    )


# =============================================================================
# 1. CATALOGUE TESTS
# =============================================================================

def test_initial_beverage_catalogue(db):
    service = BeverageService(db)
    items = service.get_catalogue(active_only=False)
    item_names = [i.name for i in items]

    assert "Tea" in item_names, "Tea must be in initial catalogue"
    assert "Green Tea" in item_names, "Green Tea must be in initial catalogue"
    assert "Coffee" in item_names, "Coffee must be in initial catalogue"

    for i in items:
        assert i.unit == "Cups", f"Beverage {i.name} unit must strictly be 'Cups'"
        assert i.isActive is True


def test_admin_catalogue_management(db, admin_actor):
    service = BeverageService(db)

    # Clean up test beverages from prior test runs
    db.query(BmsBeverage).filter(
        BmsBeverage.name.in_(["Masala Chai", "Special Masala Chai"])
    ).delete(synchronize_session=False)
    db.commit()

    # 1. Add new beverage
    created = service.create_beverage(
        actor=admin_actor,
        payload=BeverageCreateRequest(
            name="Masala Chai",
            description="Spiced Indian milk tea",
            displayOrder=4,
            isActive=True,
            unit="Cups"
        )
    )
    assert created.name == "Masala Chai"
    assert created.unit == "Cups"
    assert created.displayOrder == 4

    # Verify audit log
    audit = db.query(AuditLog).filter(
        AuditLog.action == "BMS_BEVERAGE_CATALOGUE_CREATE",
        AuditLog.target_record_id == created.id
    ).first()
    assert audit is not None
    assert audit.performed_by_name == admin_actor.name

    # 2. Reject non-Cups unit in schema validation
    with pytest.raises(Exception):
        BeverageCreateRequest(name="Soda", unit="Bottles")

    # 3. Edit beverage
    updated = service.update_beverage(
        actor=admin_actor,
        beverage_id=created.id,
        payload=BeverageUpdateRequest(
            name="Special Masala Chai",
            description="Premium spiced milk tea",
            displayOrder=5
        )
    )
    assert updated.name == "Special Masala Chai"
    assert updated.displayOrder == 5

    # 4. Toggle active/inactive status
    deactivated = service.toggle_beverage_status(actor=admin_actor, beverage_id=created.id, is_active=False)
    assert deactivated.isActive is False

    # Check active_only filter
    active_items = service.get_catalogue(active_only=True)
    assert not any(b.id == created.id for b in active_items)

    # Reactivate
    reactivated = service.toggle_beverage_status(actor=admin_actor, beverage_id=created.id, is_active=True)
    assert reactivated.isActive is True


# =============================================================================
# 2. EMPLOYEE SUBMISSION TESTS
# =============================================================================

def test_employee_morning_and_evening_submission(db, employee_actor):
    service = BeverageService(db)
    tea = db.query(BmsBeverage).filter(BmsBeverage.name == "Tea").first()
    coffee = db.query(BmsBeverage).filter(BmsBeverage.name == "Coffee").first()
    today_str = get_kolkata_date_string()

    # Clean up any existing entries for today for this test employee
    db.query(BmsBeverageEntry).filter(
        BmsBeverageEntry.employee_id == employee_actor.employee_id,
        BmsBeverageEntry.business_date == today_str
    ).delete()
    db.commit()

    # 1. Submit Morning entry
    morning_entry = service.submit_employee_entry(
        actor=employee_actor,
        payload=BeverageEntrySubmitRequest(
            beverageId=tea.id,
            session="MORNING",
            quantity=1,
            notes="Morning ginger tea"
        )
    )
    assert morning_entry.session == "MORNING"
    assert morning_entry.quantity == 1
    assert morning_entry.unit == "Cups"
    assert morning_entry.beverageNameSnapshot == "Tea"
    assert morning_entry.employeeNameSnapshot == employee_actor.name
    assert morning_entry.source == "EMPLOYEE"
    assert morning_entry.businessDate == today_str

    # 2. Submit Evening entry
    evening_entry = service.submit_employee_entry(
        actor=employee_actor,
        payload=BeverageEntrySubmitRequest(
            beverageId=coffee.id,
            session="EVENING",
            quantity=2,
            notes="Evening coffee"
        )
    )
    assert evening_entry.session == "EVENING"
    assert evening_entry.quantity == 2
    assert evening_entry.unit == "Cups"
    assert evening_entry.beverageNameSnapshot == "Coffee"

    # 3. Employee view own entries
    my_entries = service.get_my_entries(actor=employee_actor)
    sessions_found = [e.session for e in my_entries if e.businessDate == today_str]
    assert "MORNING" in sessions_found
    assert "EVENING" in sessions_found


def test_duplicate_submission_prevention(db, employee_actor):
    service = BeverageService(db)
    tea = db.query(BmsBeverage).filter(BmsBeverage.name == "Tea").first()

    # Attempt second morning submission on same day
    with pytest.raises(ValidationError) as exc:
        service.submit_employee_entry(
            actor=employee_actor,
            payload=BeverageEntrySubmitRequest(
                beverageId=tea.id,
                session="MORNING",
                quantity=1
            )
        )
    assert "already been submitted" in str(exc.value)


def test_employee_today_date_only_validation(db, employee_actor):
    service = BeverageService(db)
    tea = db.query(BmsBeverage).filter(BmsBeverage.name == "Tea").first()

    # Attempt submission for past date
    with pytest.raises(ValidationError) as exc_past:
        service.submit_employee_entry(
            actor=employee_actor,
            payload=BeverageEntrySubmitRequest(
                beverageId=tea.id,
                session="MORNING",
                quantity=1,
                businessDate="2026-10-01"
            )
        )
    assert "today's date only" in str(exc_past.value)


def test_positive_integer_quantity_validation():
    # Quantity <= 0
    with pytest.raises(Exception):
        BeverageEntrySubmitRequest(beverageId="bev-1", session="MORNING", quantity=0)

    with pytest.raises(Exception):
        BeverageEntrySubmitRequest(beverageId="bev-1", session="MORNING", quantity=-2)


def test_inactive_beverage_submission_prevention(db, employee_actor, admin_actor):
    service = BeverageService(db)
    green_tea = db.query(BmsBeverage).filter(BmsBeverage.name == "Green Tea").first()

    # Deactivate green tea
    service.toggle_beverage_status(actor=admin_actor, beverage_id=green_tea.id, is_active=False)

    try:
        # Submission for inactive beverage must fail
        with pytest.raises(ValidationError) as exc:
            service.submit_employee_entry(
                actor=employee_actor,
                payload=BeverageEntrySubmitRequest(
                    beverageId=green_tea.id,
                    session="MORNING",
                    quantity=1
                )
            )
        assert "deactivated" in str(exc.value) or "inactive" in str(exc.value)
    finally:
        # Re-activate
        service.toggle_beverage_status(actor=admin_actor, beverage_id=green_tea.id, is_active=True)


# =============================================================================
# 3. ADMIN MANAGEMENT & AUDIT LOGGING TESTS
# =============================================================================

def test_admin_create_entry_on_behalf(db, admin_actor):
    service = BeverageService(db)
    emps = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False).all()
    target_emp = emps[-1]
    coffee = db.query(BmsBeverage).filter(BmsBeverage.name == "Coffee").first()
    test_date = "2026-11-01"

    # Clean existing
    db.query(BmsBeverageEntry).filter(
        BmsBeverageEntry.employee_id == target_emp.employee_id,
        BmsBeverageEntry.business_date == test_date,
        BmsBeverageEntry.session == "MORNING"
    ).delete()
    db.commit()

    entry = service.admin_create_entry(
        actor=admin_actor,
        payload=BeverageAdminEntryCreateRequest(
            employeeId=target_emp.employee_id,
            beverageId=coffee.id,
            businessDate=test_date,
            session="MORNING",
            quantity=3,
            notes="Client meeting cups"
        )
    )
    assert entry.employeeId == target_emp.employee_id
    assert entry.quantity == 3
    assert entry.source == "ADMIN"
    assert entry.unit == "Cups"

    # Verify audit log
    audit = db.query(AuditLog).filter(
        AuditLog.action == "BMS_BEVERAGE_ADMIN_CREATE",
        AuditLog.target_record_id == entry.id
    ).first()
    assert audit is not None
    assert audit.target_employee_id == target_emp.employee_id


def test_admin_edit_with_audit_trail(db, admin_actor):
    service = BeverageService(db)
    tea = db.query(BmsBeverage).filter(BmsBeverage.name == "Tea").first()
    coffee = db.query(BmsBeverage).filter(BmsBeverage.name == "Coffee").first()
    emp = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False).first()
    test_date = "2026-11-02"

    # Clean existing
    db.query(BmsBeverageEntry).filter(
        BmsBeverageEntry.employee_id == emp.employee_id,
        BmsBeverageEntry.business_date == test_date,
        BmsBeverageEntry.session == "EVENING"
    ).delete()
    db.commit()

    # Create record
    created = service.admin_create_entry(
        actor=admin_actor,
        payload=BeverageAdminEntryCreateRequest(
            employeeId=emp.employee_id,
            beverageId=tea.id,
            businessDate=test_date,
            session="EVENING",
            quantity=1
        )
    )

    # Admin edits quantity to 2 and beverage to Coffee
    updated = service.admin_update_entry(
        actor=admin_actor,
        entry_id=created.id,
        payload=BeverageAdminEntryUpdateRequest(
            beverageId=coffee.id,
            quantity=2,
            notes="Updated to coffee"
        )
    )
    assert updated.quantity == 2
    assert updated.beverageNameSnapshot == "Coffee"

    # Verify audit trail
    audit = db.query(AuditLog).filter(
        AuditLog.action == "BMS_BEVERAGE_ADMIN_UPDATE",
        AuditLog.target_record_id == created.id
    ).order_by(AuditLog.timestamp.desc()).first()
    assert audit is not None
    assert audit.before_state["quantity"] == 1
    assert audit.after_state["quantity"] == 2


def test_admin_soft_delete_and_exclusion(db, admin_actor):
    service = BeverageService(db)
    tea = db.query(BmsBeverage).filter(BmsBeverage.name == "Tea").first()
    emp = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False).first()
    test_date = "2026-11-03"

    # Clean existing
    db.query(BmsBeverageEntry).filter(
        BmsBeverageEntry.employee_id == emp.employee_id,
        BmsBeverageEntry.business_date == test_date
    ).delete()
    db.commit()

    # Create entry
    entry = service.admin_create_entry(
        actor=admin_actor,
        payload=BeverageAdminEntryCreateRequest(
            employeeId=emp.employee_id,
            beverageId=tea.id,
            businessDate=test_date,
            session="MORNING",
            quantity=5
        )
    )

    # Confirm entry counted before deletion
    active_res = service.admin_get_entries(date=test_date, include_deleted=False)
    assert any(e.id == entry.id for e in active_res["records"])
    assert active_res["metrics"]["totalCups"] >= 5

    # Soft delete entry
    deleted = service.admin_delete_entry(actor=admin_actor, entry_id=entry.id, reason="Entered by mistake")
    assert deleted.isDeleted is True
    assert deleted.deletedBy == admin_actor.name
    assert deleted.deletionReason == "Entered by mistake"

    # Confirm soft-deleted entry is EXCLUDED from standard active queries
    active_after = service.admin_get_entries(date=test_date, include_deleted=False)
    assert not any(e.id == entry.id for e in active_after["records"])

    # Confirm soft-deleted entry is returned only when includeDeleted=True
    all_res = service.admin_get_entries(date=test_date, include_deleted=True)
    deleted_row = next((e for e in all_res["records"] if e.id == entry.id), None)
    assert deleted_row is not None
    assert deleted_row.isDeleted is True


# =============================================================================
# 4. DIRECTOR DASHBOARD INTEGRATION TESTS
# =============================================================================

def test_director_dashboard_beverage_overview(db, admin_actor):
    rs = ReportService(db)
    today_str = get_kolkata_date_string()
    report = rs.get_ceo_report(target_date=today_str)

    assert report["success"] is True
    # Verify breakfast integrity
    assert "executiveSummary" in report
    assert "dailySummary" in report
    assert "weeklySummary" in report
    assert "monthlySummary" in report
    assert "requestVsActualComparison" in report

    # Verify separate Beverage Overview
    assert "beverageOverview" in report
    bev_ov = report["beverageOverview"]
    assert bev_ov["unit"] == "Cups"
    assert "daySummary" in bev_ov
    assert "monthSummary" in bev_ov
    assert "dailyTrend" in bev_ov
    assert "employeeConsumption" in bev_ov

    day_sum = bev_ov["daySummary"]
    assert "totalCups" in day_sum
    assert "morningCups" in day_sum
    assert "eveningCups" in day_sum
    assert "beverages" in day_sum
    assert "participationRate" in day_sum

    # Verify Morning + Evening = Total
    assert day_sum["morningCups"] + day_sum["eveningCups"] == day_sum["totalCups"]

    # Verify beverages breakdown covers Tea, Green Tea, Coffee
    bev_names = [b["name"] for b in day_sum["beverages"]]
    assert "Tea" in bev_names
    assert "Coffee" in bev_names
    assert "Green Tea" in bev_names


def test_existing_bms_breakfast_regression(db):
    from app.breakfast import service as bf_service
    today_str = get_kolkata_date_string()

    # Verify breakfast employee list query works smoothly
    daily_bf = bf_service.get_daily_breakfast_employees(today_str, db)
    assert "summary" in daily_bf
    assert "applicableEmployees" in daily_bf
    assert isinstance(daily_bf["applicableEmployees"], list)
