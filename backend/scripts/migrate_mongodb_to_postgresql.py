import os
import sys
import argparse
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.roles.model import Role, Permission
from app.users.model import User
from app.employees.model import Employee, Department
from app.audit.model import AuditLog
from app.breakfast.model import (
    PublicHoliday,
    BreakfastSetting,
    BreakfastReason,
    BreakfastRecord,
    BreakfastNonParticipationPeriod,
    BreakfastDailyEntry,
    BreakfastAdditionalOrder,
    BreakfastOrder,
    BreakfastOrderItem,
    BreakfastMoneyTransaction,
    BreakfastFundRequest
)

def parse_date(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)

def run_migration(mongo_uri: str, db_name: str = None):
    try:
        from pymongo import MongoClient
    except ImportError:
        print("[Migration Error] pymongo is required. Please install pymongo.")
        sys.exit(1)

    print("=" * 60)
    print(" REVY BREAKFAST MANAGEMENT: MONGODB -> POSTGRESQL MIGRATION")
    print("=" * 60)

    print(f"[1/15] Connecting to MongoDB: {mongo_uri[:30]}...")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    
    # Verify MongoDB connection
    try:
        client.admin.command('ping')
        print("[1/15] Successfully connected to MongoDB.")
    except Exception as e:
        print(f"[Migration Error] Could not connect to MongoDB: {e}")
        return

    if not db_name:
        db_name = client.get_default_database().name if client.get_default_database() else "company_platform"
    mongo_db = client[db_name]
    print(f"[1/15] Using MongoDB database: {db_name}")

    print("[2/15] Initializing target relational schema...")
    init_db()
    db: Session = SessionLocal()

    summary = {
        "permissions": 0,
        "roles": 0,
        "users": 0,
        "employees": 0,
        "holidays": 0,
        "settings": 0,
        "reasons": 0,
        "records": 0,
        "non_participation_periods": 0,
        "daily_entries": 0,
        "additional_orders": 0,
        "orders": 0,
        "order_items": 0,
        "money_transactions": 0,
        "fund_requests": 0,
        "audit_logs": 0,
        "errors": []
    }

    try:
        # 1. Permissions
        print("[3/15] Migrating Permissions...")
        perm_map = {}
        for doc in mongo_db["permissions"].find():
            code = doc.get("code")
            p = db.query(Permission).filter(Permission.code == code).first()
            if not p:
                p = Permission(
                    code=code,
                    name=doc.get("name", code),
                    module=doc.get("module", "BREAKFAST"),
                    description=doc.get("description"),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(p)
                db.flush()
                summary["permissions"] += 1
            perm_map[code] = p

        # 2. Roles
        print("[4/15] Migrating Roles...")
        role_map = {}
        for doc in mongo_db["roles"].find():
            code = doc.get("code")
            r = db.query(Role).filter(Role.code == code).first()
            if not r:
                r = Role(
                    code=code,
                    name=doc.get("name", code),
                    description=doc.get("description"),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(r)
                db.flush()
                summary["roles"] += 1

            perms_in_doc = doc.get("permissions", [])
            r.permissions = [perm_map[c] for c in perms_in_doc if c in perm_map]
            role_map[code] = r

        # 3. Settings
        print("[5/15] Migrating Breakfast Settings...")
        for doc in mongo_db["breakfastsettings"].find():
            s = db.query(BreakfastSetting).first()
            if not s:
                s = BreakfastSetting(
                    cutoff_time=doc.get("cutoffTime", "12:00"),
                    timezone=doc.get("timezone", "Asia/Kolkata"),
                    auto_lock_enabled=doc.get("autoLockEnabled", True),
                    breakfast_fund_limit=float(doc.get("breakfastFundLimit", 2500.0)),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(s)
                summary["settings"] += 1

        # 4. Reasons
        print("[6/15] Migrating Breakfast Reasons...")
        for doc in mongo_db["breakfastreasons"].find():
            code = doc.get("code")
            br = db.query(BreakfastReason).filter(BreakfastReason.code == code).first()
            if not br:
                br = BreakfastReason(
                    code=code,
                    label=doc.get("label", code),
                    is_custom_allowed=doc.get("isCustomAllowed", False),
                    is_active=doc.get("isActive", True),
                    display_order=doc.get("displayOrder", 0),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(br)
                summary["reasons"] += 1

        # 5. Public Holidays
        print("[7/15] Migrating Public Holidays...")
        for doc in mongo_db["publicholidays"].find():
            date_str = doc.get("date")
            h = db.query(PublicHoliday).filter(PublicHoliday.date == date_str).first()
            if not h:
                h = PublicHoliday(
                    holiday_id=doc.get("holidayId") or f"HOL-{date_str.replace('-', '')}",
                    date=date_str,
                    name=doc.get("name", "Holiday"),
                    status=doc.get("status", "active"),
                    created_by=doc.get("createdBy", "System"),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(h)
                summary["holidays"] += 1

        # 6. Employees & Users
        print("[8/15] Migrating Users & Employees...")
        emp_id_map = {}
        for doc in mongo_db["employees"].find():
            emp_id = doc.get("employeeId", "").upper()
            username = (doc.get("username") or emp_id).lower()

            existing_user = db.query(User).filter(User.username == username).first()
            if not existing_user:
                existing_user = User(
                    username=username,
                    email=doc.get("email", f"{username}@company.com").lower(),
                    password_hash=doc.get("passwordHash", ""),
                    status=doc.get("status", "active"),
                    force_password_change=bool(doc.get("forcePasswordChange", False)),
                    is_hard_deleted=bool(doc.get("isHardDeleted", False)),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                doc_roles = doc.get("roles", ["EMPLOYEE"])
                existing_user.roles = [role_map[rc] for rc in doc_roles if rc in role_map]
                db.add(existing_user)
                db.flush()
                summary["users"] += 1

            existing_emp = db.query(Employee).filter(Employee.employee_id == emp_id).first()
            if not existing_emp:
                dept_name = doc.get("department", "General")
                # Ensure department exists
                d = db.query(Department).filter(Department.name == dept_name).first()
                if not d:
                    d = Department(name=dept_name)
                    db.add(d)

                existing_emp = Employee(
                    user_id=existing_user.id,
                    employee_id=emp_id,
                    name=doc.get("name", username),
                    email=doc.get("email", f"{username}@company.com").lower(),
                    phone=doc.get("phone", ""),
                    department=dept_name,
                    designation=doc.get("designation", "Staff"),
                    status=doc.get("status", "active"),
                    breakfast_participation_type=doc.get("breakfastParticipationType", "NORMAL"),
                    is_hard_deleted=bool(doc.get("isHardDeleted", False)),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(existing_emp)
                summary["employees"] += 1

            emp_id_map[emp_id] = existing_emp

        # 7. Breakfast Records
        print("[9/15] Migrating Breakfast Records (Responses)...")
        for doc in mongo_db["breakfastrecords"].find():
            rec_id = doc.get("recordId")
            emp_id = doc.get("employeeId", "").upper()
            b_date = doc.get("businessDate")

            existing_rec = db.query(BreakfastRecord).filter(
                BreakfastRecord.employee_id == emp_id,
                BreakfastRecord.business_date == b_date
            ).first()

            if not existing_rec:
                r = BreakfastRecord(
                    record_id=rec_id or f"BRK-{b_date.replace('-', '')}-{emp_id}",
                    employee_id=emp_id,
                    business_date=b_date,
                    response=doc.get("response", "YES"),
                    employee_response=doc.get("employeeResponse", "TAKING"),
                    actual_status=doc.get("actualStatus"),
                    actual_status_source=doc.get("actualStatusSource", "EMPLOYEE_RESPONSE"),
                    reason_code=doc.get("reasonCode"),
                    reason_text=doc.get("reasonText"),
                    source=doc.get("source", "EMPLOYEE"),
                    submitted_at=parse_date(doc.get("submittedAt")),
                    history=doc.get("history", []),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(r)
                summary["records"] += 1

        # 8. Non Participation Periods
        print("[10/15] Migrating Non-Participation Periods...")
        for doc in mongo_db["breakfastnonparticipationperiods"].find():
            p_id = doc.get("periodId")
            existing_p = db.query(BreakfastNonParticipationPeriod).filter(
                BreakfastNonParticipationPeriod.period_id == p_id
            ).first()
            if not existing_p:
                p = BreakfastNonParticipationPeriod(
                    period_id=p_id,
                    employee_id=doc.get("employeeId", "").upper(),
                    from_date=doc.get("fromDate"),
                    to_date=doc.get("toDate"),
                    reason_code=doc.get("reasonCode"),
                    reason_text=doc.get("reasonText"),
                    source=doc.get("source", "EMPLOYEE"),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(p)
                summary["non_participation_periods"] += 1

        # 9. Daily Entries
        print("[11/15] Migrating Breakfast Daily Entries...")
        for doc in mongo_db["breakfastdailyentries"].find():
            b_date = doc.get("businessDate")
            de = db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == b_date).first()
            if not de:
                de = BreakfastDailyEntry(
                    business_date=b_date,
                    employee_snapshot=doc.get("employeeSnapshot", []),
                    summary=doc.get("summary", {}),
                    breakfast_items=doc.get("breakfastItems", []),
                    common_items=doc.get("commonItems", []),
                    total_cost=float(doc.get("totalCost", 0.0)),
                    created_by=doc.get("createdBy", "Admin"),
                    updated_by=doc.get("updatedBy"),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(de)
                summary["daily_entries"] += 1

        # 10. Additional Orders
        print("[12/15] Migrating Additional Orders...")
        for doc in mongo_db["breakfastadditionalorders"].find():
            ord_id = doc.get("orderId")
            ao = db.query(BreakfastAdditionalOrder).filter(BreakfastAdditionalOrder.order_id == ord_id).first()
            if not ao:
                ao = BreakfastAdditionalOrder(
                    order_id=ord_id,
                    business_date=doc.get("businessDate"),
                    order_title=doc.get("orderTitle", "Additional Order"),
                    order_time=doc.get("orderTime"),
                    applicable_employee_snapshot=doc.get("applicableEmployeeSnapshot", []),
                    applicable_employee_count=int(doc.get("applicableEmployeeCount", 0)),
                    breakfast_items=doc.get("breakfastItems", []),
                    common_items=doc.get("commonItems", []),
                    total_cost=float(doc.get("totalCost", 0.0)),
                    created_by=doc.get("createdBy", "Admin"),
                    updated_by=doc.get("updatedBy"),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(ao)
                summary["additional_orders"] += 1

        # 11. Purchase Orders & Order Items
        print("[13/15] Migrating Orders & Order Items...")
        for doc in mongo_db["breakfastorders"].find():
            ord_id = doc.get("orderId")
            bo = db.query(BreakfastOrder).filter(BreakfastOrder.order_id == ord_id).first()
            if not bo:
                created_by = doc.get("createdBy", {})
                bo = BreakfastOrder(
                    order_id=ord_id,
                    business_date=doc.get("businessDate"),
                    vendor_name=doc.get("vendorName", "Internal Catering"),
                    notes=doc.get("notes", ""),
                    created_by_employee_id=created_by.get("employeeId", "ADMIN"),
                    created_by_employee_name=created_by.get("employeeName", "Admin"),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(bo)
                summary["orders"] += 1

        for doc in mongo_db["breakfastorderitems"].find():
            itm_id = doc.get("itemId")
            boi = db.query(BreakfastOrderItem).filter(BreakfastOrderItem.item_id == itm_id).first()
            if not boi:
                boi = BreakfastOrderItem(
                    item_id=itm_id,
                    order_id=doc.get("orderId"),
                    business_date=doc.get("businessDate"),
                    order_type=doc.get("orderType", "INDIVIDUAL"),
                    employee_id=doc.get("employeeId"),
                    employee_name=doc.get("employeeName"),
                    item_name=doc.get("itemName", ""),
                    price=float(doc.get("price", 0.0)),
                    quantity=int(doc.get("quantity", 1)),
                    total=float(doc.get("total", 0.0)),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(boi)
                summary["order_items"] += 1

        # 12. Money Transactions & Fund Requests
        print("[14/15] Migrating Financial Transactions & Fund Requests...")
        for doc in mongo_db["breakfastmoneytransactions"].find():
            txn_id = doc.get("transactionId")
            tx = db.query(BreakfastMoneyTransaction).filter(BreakfastMoneyTransaction.transaction_id == txn_id).first()
            if not tx:
                tx = BreakfastMoneyTransaction(
                    transaction_id=txn_id,
                    transaction_date=doc.get("transactionDate"),
                    transaction_time=doc.get("transactionTime", "12:00 PM"),
                    type=doc.get("type"),
                    amount=float(doc.get("amount", 0.0)),
                    balance_after_transaction=float(doc.get("balanceAfterTransaction", 0.0)),
                    source=doc.get("source", "Finance"),
                    reference_type=doc.get("referenceType", "MANUAL"),
                    reference_id=doc.get("referenceId"),
                    expense_category=doc.get("expenseCategory", "DAILY_BREAKFAST"),
                    expense_purpose=doc.get("expensePurpose", "EMPLOYEE"),
                    description=doc.get("description", ""),
                    note=doc.get("note", ""),
                    created_by=doc.get("createdBy", "Admin"),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(tx)
                summary["money_transactions"] += 1

        for doc in mongo_db["breakfastfundrequests"].find():
            req_id = doc.get("requestId")
            fr = db.query(BreakfastFundRequest).filter(BreakfastFundRequest.request_id == req_id).first()
            if not fr:
                fr = BreakfastFundRequest(
                    request_id=req_id,
                    requested_by=doc.get("requestedBy", "Admin"),
                    request_date=doc.get("requestDate"),
                    request_time=doc.get("requestTime", "12:00 PM"),
                    current_balance=float(doc.get("currentBalance", 0.0)),
                    fund_limit=float(doc.get("fundLimit", 2500.0)),
                    requested_amount=float(doc.get("requestedAmount", 0.0)),
                    expected_balance=float(doc.get("expectedBalance", 0.0)),
                    reason=doc.get("reason", ""),
                    status=doc.get("status", "PENDING_APPROVAL"),
                    approved_amount=float(doc.get("approvedAmount", 0.0)),
                    approved_by=doc.get("approvedBy"),
                    approved_at=parse_date(doc.get("approvedAt")),
                    provided_amount=float(doc.get("providedAmount", 0.0)),
                    provided_by=doc.get("providedBy"),
                    provided_at=parse_date(doc.get("providedAt")),
                    provided_date=doc.get("providedDate"),
                    provided_time=doc.get("providedTime"),
                    reference=doc.get("reference"),
                    provided_note=doc.get("providedNote"),
                    verified_amount=float(doc.get("verifiedAmount", 0.0)),
                    verified_by=doc.get("verifiedBy"),
                    verified_at=parse_date(doc.get("verifiedAt")),
                    rejection_reason=doc.get("rejectionReason"),
                    difference_reported=doc.get("differenceReported", {}),
                    created_at=parse_date(doc.get("createdAt")),
                    updated_at=parse_date(doc.get("updatedAt"))
                )
                db.add(fr)
                summary["fund_requests"] += 1

        # 13. Audit Logs
        print("[15/15] Migrating Audit Logs...")
        for doc in mongo_db["auditlogs"].find():
            aud_id = doc.get("auditId")
            al = db.query(AuditLog).filter(AuditLog.audit_id == aud_id).first()
            if not al:
                performed = doc.get("performedBy", {})
                target = doc.get("target", {})
                al = AuditLog(
                    audit_id=aud_id,
                    application=doc.get("application", "BREAKFAST"),
                    action=doc.get("action", "UNKNOWN"),
                    performed_by_employee_id=performed.get("employeeId"),
                    performed_by_name=performed.get("employeeName"),
                    role_used=performed.get("roleUsed"),
                    target_record_id=target.get("recordId"),
                    target_employee_id=target.get("targetEmployeeId"),
                    target_employee_name=target.get("targetEmployeeName"),
                    details=target.get("details"),
                    before_state=doc.get("beforeState"),
                    after_state=doc.get("afterState"),
                    timestamp=parse_date(doc.get("timestamp")),
                    created_at=parse_date(doc.get("createdAt"))
                )
                db.add(al)
                summary["audit_logs"] += 1

        db.commit()
        print("\n" + "=" * 60)
        print(" MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f" * Permissions Migrated:            {summary['permissions']}")
        print(f" * Roles Migrated:                  {summary['roles']}")
        print(f" * Users Migrated:                  {summary['users']}")
        print(f" * Employees Migrated:              {summary['employees']}")
        print(f" * Public Holidays Migrated:        {summary['holidays']}")
        print(f" * Breakfast Settings Migrated:     {summary['settings']}")
        print(f" * Breakfast Reasons Migrated:      {summary['reasons']}")
        print(f" * Breakfast Responses Migrated:    {summary['records']}")
        print(f" * Non-Participation Periods:       {summary['non_participation_periods']}")
        print(f" * Daily Entries Migrated:          {summary['daily_entries']}")
        print(f" * Additional Orders Migrated:      {summary['additional_orders']}")
        print(f" * Purchase Orders Migrated:        {summary['orders']}")
        print(f" * Purchase Order Items:            {summary['order_items']}")
        print(f" * Money Transactions Migrated:     {summary['money_transactions']}")
        print(f" * Fund Requests Migrated:          {summary['fund_requests']}")
        print(f" * Audit Logs Migrated:             {summary['audit_logs']}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n[Migration Error] Failed during execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate MongoDB Breakfast Management data to PostgreSQL")
    parser.add_argument("--mongo-uri", default=os.environ.get("MONGODB_URI"), help="MongoDB connection string")
    parser.add_argument("--db-name", default=os.environ.get("MONGODB_DB_NAME"), help="MongoDB database name")
    args = parser.parse_args()

    if not args.mongo_uri:
        print("[Notice] MONGODB_URI not provided. Migration script ready for execution when MongoDB credentials supplied.")
        print("Usage: python scripts/migrate_mongodb_to_postgresql.py --mongo-uri 'mongodb+srv://...'")
    else:
        run_migration(args.mongo_uri, args.db_name)
