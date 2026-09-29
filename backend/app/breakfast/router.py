import math
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, CurrentUser
from app.core.exceptions import ValidationError, NotFoundError
from app.employees.model import Employee
from app.breakfast.model import (
    BreakfastRecord,
    BreakfastSetting,
    BreakfastReason,
    BreakfastNonParticipationPeriod,
    BreakfastDailyEntry,
    BreakfastAdditionalOrder,
    PublicHoliday
)
from app.breakfast import service as bf_service
from app.breakfast import money_service
from app.breakfast import calendar_service
from app.breakfast.date_utils import (
    get_kolkata_date_string,
    get_kolkata_now,
    get_formatted_date_and_day,
    is_after_cutoff,
    getNextDayDate
)
from app.audit.service import AuditService

router = APIRouter(prefix="/breakfast", tags=["Breakfast"])

class SubmitBreakfastRequest(BaseModel):
    response: str
    reasonCode: Optional[str] = None
    reasonText: Optional[str] = None

class MultiDayAbsenceRequest(BaseModel):
    fromDate: str
    toDate: str
    reasonCode: str
    reasonText: Optional[str] = None

class UpdateActualStatusRequest(BaseModel):
    employeeId: str
    businessDate: str
    actualStatus: str

class ItemInput(BaseModel):
    name: str
    unitPrice: float
    quantity: Optional[float] = None
    total: Optional[float] = None

class SaveDailyEntryRequest(BaseModel):
    businessDate: str
    breakfastItems: Optional[List[ItemInput]] = []
    commonItems: Optional[List[ItemInput]] = []

class AdditionalOrderRequest(BaseModel):
    businessDate: str
    orderTitle: Optional[str] = "Additional Breakfast / Snack Order"
    orderTime: Optional[str] = None
    breakfastItems: Optional[List[ItemInput]] = []
    commonItems: Optional[List[ItemInput]] = []

def serialize_record(r: Optional[BreakfastRecord]):
    if not r:
        return None
    return {
        "_id": r.id,
        "id": r.id,
        "recordId": r.record_id,
        "employeeId": r.employee_id,
        "businessDate": r.business_date,
        "response": r.response,
        "employeeResponse": r.employee_response,
        "actualStatus": r.actual_status,
        "actualStatusSource": r.actual_status_source,
        "reasonCode": r.reason_code,
        "reasonText": r.reason_text,
        "source": r.source,
        "submittedAt": r.submitted_at.isoformat() if r.submitted_at else None,
        "history": r.history or []
    }

def serialize_period(p: BreakfastNonParticipationPeriod):
    return {
        "_id": p.id,
        "id": p.id,
        "periodId": p.period_id,
        "employeeId": p.employee_id,
        "fromDate": p.from_date,
        "toDate": p.to_date,
        "reasonCode": p.reason_code,
        "reasonText": p.reason_text,
        "source": p.source,
        "createdAt": p.created_at.isoformat() if p.created_at else None
    }

def serialize_daily_entry(e: Optional[BreakfastDailyEntry]):
    if not e:
        return None
    return {
        "_id": e.id,
        "id": e.id,
        "businessDate": e.business_date,
        "employeeSnapshot": e.employee_snapshot or [],
        "summary": e.summary or {},
        "breakfastItems": e.breakfast_items or [],
        "commonItems": e.common_items or [],
        "totalCost": e.total_cost,
        "createdBy": e.created_by,
        "updatedBy": e.updated_by,
        "createdAt": e.created_at.isoformat() if e.created_at else None,
        "updatedAt": e.updated_at.isoformat() if e.updated_at else None
    }

def serialize_additional_order(o: BreakfastAdditionalOrder):
    return {
        "_id": o.id,
        "id": o.id,
        "orderId": o.order_id,
        "businessDate": o.business_date,
        "orderTitle": o.order_title,
        "orderTime": o.order_time,
        "applicableEmployeeSnapshot": o.applicable_employee_snapshot or [],
        "applicableEmployeeCount": o.applicable_employee_count,
        "breakfastItems": o.breakfast_items or [],
        "commonItems": o.common_items or [],
        "totalCost": o.total_cost,
        "createdBy": o.created_by,
        "updatedBy": o.updated_by,
        "createdAt": o.created_at.isoformat() if o.created_at else None,
        "updatedAt": o.updated_at.isoformat() if o.updated_at else None
    }

# 1. Personal Breakfast Status (Today)
@router.get("/today")
def get_today_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today_dt = get_kolkata_now()
    today_info = get_formatted_date_and_day(today_dt)

    settings = db.query(BreakfastSetting).first()
    cutoff_time = settings.cutoff_time if settings else "12:00"
    is_cutoff_passed = is_after_cutoff(cutoff_time)

    next_day_dt = getNextDayDate(today_dt)
    next_day_info = get_formatted_date_and_day(next_day_dt)

    active_date_str = next_day_info["dateStr"] if is_cutoff_passed else today_info["dateStr"]
    active_formatted = next_day_info["displayString"] if is_cutoff_passed else today_info["displayString"]

    is_holiday = db.query(PublicHoliday).filter(
        PublicHoliday.date == active_date_str,
        PublicHoliday.status == "active"
    ).first()

    today_record = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == current_user.employee_id,
        BreakfastRecord.business_date == active_date_str
    ).first()

    reasons = db.query(BreakfastReason).filter(BreakfastReason.is_active == True).order_by(BreakfastReason.display_order.asc()).all()
    formatted_reasons = [
        {"_id": r.id, "id": r.id, "code": r.code, "label": r.label, "isCustomAllowed": r.is_custom_allowed}
        for r in reasons
    ]

    return {
        "success": True,
        "businessDate": active_date_str,
        "todayFormattedDisplay": today_info["displayString"],
        "activeFormattedDisplay": active_formatted,
        "isCutoffPassed": is_cutoff_passed,
        "cutoffTime": cutoff_time,
        "employeeId": current_user.employee_id,
        "name": current_user.name,
        "participationType": current_user.breakfast_participation_type,
        "isPublicHoliday": bool(is_holiday),
        "holidayName": is_holiday.name if is_holiday else None,
        "todayRecord": serialize_record(today_record),
        "reasons": formatted_reasons
    }

# 2. Submit Daily Breakfast Response
@router.post("/submit")
def submit_daily_breakfast(
    payload: SubmitBreakfastRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.breakfast_participation_type == "PERMANENT_NOT_TAKING":
        raise ValidationError("Your account is set to PERMANENT_NOT_TAKING. You do not submit daily responses.")

    today_dt = get_kolkata_now()
    settings = db.query(BreakfastSetting).first()
    cutoff_time = settings.cutoff_time if settings else "12:00"
    cutoff_passed = is_after_cutoff(cutoff_time)

    target_dt = getNextDayDate(today_dt) if cutoff_passed else today_dt
    target_info = get_formatted_date_and_day(target_dt)
    target_date_str = target_info["dateStr"]

    resp = payload.response.upper()
    if resp not in ["YES", "NO", "TAKING", "NOT_TAKING"]:
        raise ValidationError("Response must be YES or NO")

    normalized_resp = "YES" if resp in ["YES", "TAKING"] else "NO"
    emp_resp = "TAKING" if normalized_resp == "YES" else "NOT_TAKING"

    final_reason_code = None
    final_reason_text = None

    if normalized_resp == "NO":
        if not payload.reasonCode:
            raise ValidationError("Please select a reason for not taking breakfast")
        final_reason_code = payload.reasonCode
        if payload.reasonCode == "OTHER":
            if not payload.reasonText or not payload.reasonText.strip():
                raise ValidationError('Reason text is mandatory when "Other" is selected')
            final_reason_text = payload.reasonText.strip()
        else:
            r_doc = db.query(BreakfastReason).filter(BreakfastReason.code == payload.reasonCode).first()
            final_reason_text = r_doc.label if r_doc else payload.reasonCode

    existing_record = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == current_user.employee_id,
        BreakfastRecord.business_date == target_date_str
    ).first()

    action_name = "BREAKFAST_RESPONSE_SUBMITTED"
    before_state = None

    if existing_record:
        action_name = "BREAKFAST_RESPONSE_UPDATED"
        before_state = serialize_record(existing_record)

        hist = list(existing_record.history or [])
        hist.append({
            "response": existing_record.response,
            "actualStatus": existing_record.actual_status,
            "reasonCode": existing_record.reason_code,
            "reasonText": existing_record.reason_text,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "updatedBy": current_user.name
        })
        existing_record.history = hist
        existing_record.response = normalized_resp
        existing_record.employee_response = emp_resp
        existing_record.reason_code = final_reason_code
        existing_record.reason_text = final_reason_text
    else:
        record_id = f"BRK-{target_date_str.replace('-', '')}-{current_user.employee_id}"
        existing_record = BreakfastRecord(
            record_id=record_id,
            employee_id=current_user.employee_id,
            business_date=target_date_str,
            response=normalized_resp,
            employee_response=emp_resp,
            actual_status=None,
            reason_code=final_reason_code,
            reason_text=final_reason_text,
            source="EMPLOYEE",
            submitted_at=datetime.now(timezone.utc),
            history=[]
        )
        db.add(existing_record)

    db.commit()
    db.refresh(existing_record)

    after_state = serialize_record(existing_record)

    audit_service = AuditService(db)
    audit_service.log(
        action=action_name,
        request=request,
        target_info={
            "recordId": existing_record.record_id,
            "targetEmployeeId": current_user.employee_id,
            "targetEmployeeName": current_user.name,
            "details": f"Response for {target_info['displayString']}: {normalized_resp}"
        },
        before_state=before_state,
        after_state=after_state
    )

    return {
        "success": True,
        "message": f"Breakfast response for {target_info['displayString']} saved successfully",
        "record": after_state
    }

# 3. Multi-Day Absence Submission
@router.post("/multi-day-absence")
def submit_multi_day_absence(
    payload: MultiDayAbsenceRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from_date = payload.fromDate.strip()
    to_date = payload.toDate.strip()
    if not from_date or not to_date or not payload.reasonCode:
        raise ValidationError("From Date, To Date, and Reason are required")
    if from_date > to_date:
        raise ValidationError("From Date must be before or equal to To Date")

    if payload.reasonCode == "OTHER" and (not payload.reasonText or not payload.reasonText.strip()):
        raise ValidationError("Mandatory reason text required when Other is selected")

    final_reason_text = payload.reasonText.strip() if payload.reasonText else payload.reasonCode
    if payload.reasonCode != "OTHER":
        r = db.query(BreakfastReason).filter(BreakfastReason.code == payload.reasonCode).first()
        if r:
            final_reason_text = r.label

    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    period_id = f"PER-{now_ts}"
    period = BreakfastNonParticipationPeriod(
        period_id=period_id,
        employee_id=current_user.employee_id,
        from_date=from_date,
        to_date=to_date,
        reason_code=payload.reasonCode,
        reason_text=final_reason_text,
        source="EMPLOYEE"
    )
    db.add(period)

    # Upsert NO records for each date in range
    from datetime import date as dt_date, timedelta
    start_d = dt_date.fromisoformat(from_date)
    end_d = dt_date.fromisoformat(to_date)
    cur_d = start_d
    updated_dates = []

    while cur_d <= end_d:
        d_str = cur_d.isoformat()
        updated_dates.append(d_str)
        rec_id = f"BRK-{d_str.replace('-', '')}-{current_user.employee_id}"

        rec = db.query(BreakfastRecord).filter(
            BreakfastRecord.employee_id == current_user.employee_id,
            BreakfastRecord.business_date == d_str
        ).first()

        if rec:
            rec.response = "NO"
            rec.employee_response = "NOT_TAKING"
            rec.reason_code = payload.reasonCode
            rec.reason_text = final_reason_text
            rec.source = "EMPLOYEE"
        else:
            rec = BreakfastRecord(
                record_id=rec_id,
                employee_id=current_user.employee_id,
                business_date=d_str,
                response="NO",
                employee_response="NOT_TAKING",
                actual_status=None,
                reason_code=payload.reasonCode,
                reason_text=final_reason_text,
                source="EMPLOYEE",
                submitted_at=datetime.now(timezone.utc),
                history=[]
            )
            db.add(rec)
        cur_d += timedelta(days=1)

    db.commit()
    db.refresh(period)

    serialized_period = serialize_period(period)

    audit_service = AuditService(db)
    audit_service.log(
        action="MULTI_DAY_ABSENCE_SUBMITTED",
        request=request,
        target_info={"details": f"Submitted multi-day absence for {current_user.name} ({from_date} to {to_date})"},
        after_state={"period": serialized_period, "updatedDates": updated_dates}
    )

    return {
        "success": True,
        "message": f"Multi-day non-breakfast period recorded from {from_date} to {to_date}",
        "period": serialized_period,
        "datesCount": len(updated_dates)
    }

# 4. Own Submission History
@router.get("/history")
def get_own_history(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == current_user.employee_id
    ).order_by(BreakfastRecord.business_date.desc()).limit(60).all()

    periods = db.query(BreakfastNonParticipationPeriod).filter(
        BreakfastNonParticipationPeriod.employee_id == current_user.employee_id
    ).order_by(BreakfastNonParticipationPeriod.from_date.desc()).all()

    return {
        "success": True,
        "records": [serialize_record(r) for r in records],
        "periods": [serialize_period(p) for p in periods]
    }

# 5. Admin Summary
@router.get("/admin/summary")
def get_admin_summary(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.view")),
    db: Session = Depends(get_db)
):
    target_date = date or get_kolkata_date_string()

    is_holiday = db.query(PublicHoliday).filter(
        PublicHoliday.date == target_date,
        PublicHoliday.status == "active"
    ).first()

    active_emps = db.query(Employee).filter(
        Employee.status == "active",
        Employee.is_hard_deleted == False
    ).all()
    normal_emps = [e for e in active_emps if e.breakfast_participation_type == "NORMAL"]
    perm_emps = [e for e in active_emps if e.breakfast_participation_type == "PERMANENT_NOT_TAKING"]

    today_recs = db.query(BreakfastRecord).filter(BreakfastRecord.business_date == target_date).all()
    yes_count = sum(1 for r in today_recs if r.response in ["YES", "TAKING"] or r.employee_response == "TAKING")
    no_count = sum(1 for r in today_recs if r.response in ["NO", "NOT_TAKING"] or r.employee_response == "NOT_TAKING")
    taken_count = sum(1 for r in today_recs if r.actual_status == "TAKEN")
    not_taken_count = sum(1 for r in today_recs if r.actual_status == "NOT_TAKEN")

    responded_ids = {r.employee_id.upper() for r in today_recs}
    pending_count = sum(1 for e in normal_emps if e.employee_id.upper() not in responded_ids)

    settings = db.query(BreakfastSetting).first()
    cutoff_time = settings.cutoff_time if settings else "12:00"

    return {
        "success": True,
        "businessDate": target_date,
        "isPublicHoliday": bool(is_holiday),
        "holidayName": is_holiday.name if is_holiday else None,
        "cutoffTime": cutoff_time,
        "isCutoffPassed": is_after_cutoff(cutoff_time),
        "metrics": {
            "totalActive": len(active_emps),
            "normalEmployeesCount": len(normal_emps),
            "permanentNotTakingCount": len(perm_emps),
            "takingBreakfastCount": yes_count,
            "notTakingBreakfastCount": no_count,
            "pendingCount": pending_count,
            "expectedBreakfastCount": 0 if is_holiday else yes_count,
            "actuallyTakenCount": taken_count,
            "actuallyNotTakenCount": not_taken_count
        }
    }

# 6. Admin Daily Records
@router.get("/admin/records")
def get_admin_daily_records(
    date: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.view")),
    db: Session = Depends(get_db)
):
    target_date = date or get_kolkata_date_string()
    day_status = calendar_service.get_business_day_status(target_date, db)

    emp_q = db.query(Employee).filter(Employee.status == "active", Employee.is_hard_deleted == False)
    if department and department != "ALL":
        emp_q = emp_q.filter(Employee.department == department)
    employees = emp_q.all()

    if search and search.strip():
        s = search.strip().lower()
        employees = [
            e for e in employees
            if (e.user and s in e.user.username.lower())
            or s in e.name.lower()
            or s in e.employee_id.lower()
            or s in e.department.lower()
        ]

    records = db.query(BreakfastRecord).filter(BreakfastRecord.business_date == target_date).all()
    record_map = {r.employee_id.upper(): r for r in records}

    all_list = []
    for emp in employees:
        rec = record_map.get(emp.employee_id.upper())
        is_perm = (emp.breakfast_participation_type == "PERMANENT_NOT_TAKING")

        emp_response = "NO_RESPONSE"
        act_status = "NO_RESPONSE"
        act_source = rec.actual_status_source if rec else "EMPLOYEE_RESPONSE"

        if is_perm:
            emp_response = "NOT_TAKING"
            act_status = "NOT_TAKEN"
        elif rec:
            if rec.response in ["YES", "TAKING"] or rec.employee_response == "TAKING":
                emp_response = "TAKING"
                act_status = rec.actual_status or "TAKEN"
            elif rec.response in ["NO", "NOT_TAKING"] or rec.employee_response == "NOT_TAKING":
                emp_response = "NOT_TAKING"
                act_status = rec.actual_status or "NOT_TAKEN"
            else:
                emp_response = "NO_RESPONSE"
                act_status = rec.actual_status or "NO_RESPONSE"

        all_list.append({
            "employeeId": emp.employee_id,
            "username": emp.user.username if emp.user else "",
            "name": emp.name,
            "department": emp.department,
            "designation": emp.designation,
            "participationType": emp.breakfast_participation_type,
            "employeeResponse": emp_response,
            "actualStatus": act_status,
            "actualStatusSource": act_source,
            "reasonCode": rec.reason_code if rec else ("PERMANENT_NOT_TAKING" if is_perm else None),
            "reasonText": rec.reason_text if rec else ("Permanent Non-Participant" if is_perm else None),
            "source": rec.source if rec else "EMPLOYEE"
        })

    return {
        "success": True,
        "businessDate": target_date,
        "dayStatus": day_status,
        "allList": all_list
    }

# 7. Update Actual Status (Override)
@router.put("/actual-status")
def update_actual_status(
    payload: UpdateActualStatusRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    if payload.actualStatus not in ["TAKEN", "NOT_TAKEN", "NO_RESPONSE"]:
        raise ValidationError("actualStatus must be TAKEN, NOT_TAKEN, or NO_RESPONSE")

    emp = db.query(Employee).filter(Employee.employee_id == payload.employeeId.strip().upper()).first()
    if not emp:
        raise NotFoundError("Employee not found")

    rec = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == emp.employee_id,
        BreakfastRecord.business_date == payload.businessDate
    ).first()

    before_state = serialize_record(rec)
    prev_status = rec.actual_status if rec and rec.actual_status else "NO_RESPONSE"

    if not rec:
        rec_id = f"BRK-{payload.businessDate.replace('-', '')}-{emp.employee_id}"
        rec = BreakfastRecord(
            record_id=rec_id,
            employee_id=emp.employee_id,
            business_date=payload.businessDate,
            response="NO",
            employee_response="NO_RESPONSE",
            actual_status=payload.actualStatus,
            actual_status_source="ADMIN_OVERRIDE",
            source="ADMIN",
            history=[]
        )
        db.add(rec)
    else:
        hist = list(rec.history or [])
        hist.append({
            "response": rec.response,
            "actualStatus": rec.actual_status,
            "actualStatusSource": rec.actual_status_source,
            "reasonCode": rec.reason_code,
            "reasonText": rec.reason_text,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "updatedBy": current_user.name
        })
        rec.history = hist
        rec.actual_status = payload.actualStatus
        rec.actual_status_source = "ADMIN_OVERRIDE"

    # Also update snapshot in daily entry if exists
    daily_entry = db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == payload.businessDate).first()
    if daily_entry and daily_entry.employee_snapshot:
        snapshot = list(daily_entry.employee_snapshot)
        for item in snapshot:
            if item.get("employeeId", "").upper() == emp.employee_id.upper():
                item["actualStatus"] = payload.actualStatus
                item["actualStatusSource"] = "ADMIN_OVERRIDE"
        daily_entry.employee_snapshot = snapshot

    db.commit()
    db.refresh(rec)

    after_state = serialize_record(rec)

    audit_service = AuditService(db)
    audit_service.log(
        action="ACTUAL_STATUS_OVERRIDDEN",
        request=request,
        target_info={
            "targetEmployeeId": emp.employee_id,
            "targetEmployeeName": emp.name,
            "previousActualStatus": prev_status,
            "newActualStatus": payload.actualStatus,
            "details": f"Breakfast Admin ({current_user.name}) overridden actual status for {emp.name} ({emp.employee_id}) on {payload.businessDate} from {prev_status} to {payload.actualStatus}"
        },
        before_state=before_state,
        after_state=after_state
    )

    return {
        "success": True,
        "message": f"Actual consumption status for {emp.name} updated to {payload.actualStatus} (ADMIN_OVERRIDE)",
        "record": after_state
    }

# 8. Daily Entry GET
@router.get("/daily-entry")
def get_daily_entry(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.view")),
    db: Session = Depends(get_db)
):
    target_date = date or get_kolkata_date_string()
    emp_data = bf_service.get_daily_breakfast_employees(target_date, db)
    existing_entry = db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == target_date).first()
    fund_metrics = money_service.get_money_balance_metrics(db)

    return {
        "success": True,
        "businessDate": target_date,
        "existingEntry": serialize_daily_entry(existing_entry),
        "applicableEmployees": emp_data["applicableEmployees"],
        "permExcludedEmployees": emp_data["permExcludedEmployees"],
        "leaveExcludedEmployees": emp_data["leaveExcludedEmployees"],
        "summary": emp_data["summary"],
        "fundMetrics": fund_metrics
    }

# 9. Daily Entry POST (Save/Update)
@router.post("/daily-entry")
def save_daily_entry(
    payload: SaveDailyEntryRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    b_date = payload.businessDate.strip()
    if not b_date:
        raise ValidationError("businessDate is required")

    emp_data = bf_service.get_daily_breakfast_employees(b_date, db)
    taking_count = emp_data["summary"]["takingCount"]

    processed_bf = []
    items_total = 0.0
    for item in payload.breakfastItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty = float(item.quantity) if item.quantity is not None else float(taking_count)
            tot = price * qty
            items_total += tot
            processed_bf.append({
                "name": item.name.strip(),
                "unitPrice": price,
                "quantity": qty,
                "total": tot
            })

    processed_cm = []
    common_total = 0.0
    for item in payload.commonItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty = float(item.quantity) if item.quantity is not None else 1.0
            tot = price * qty
            common_total += tot
            processed_cm.append({
                "name": item.name.strip(),
                "unitPrice": price,
                "quantity": qty,
                "total": tot
            })

    total_cost = items_total + common_total

    # Process money ledger
    money_service.process_daily_entry_expense(
        business_date=b_date,
        new_total_cost=total_cost,
        created_by=current_user.name,
        db=db
    )

    entry = db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == b_date).first()
    action = "DAILY_ENTRY_UPDATED" if entry else "DAILY_ENTRY_CREATED"
    before_state = serialize_daily_entry(entry)

    if entry:
        entry.employee_snapshot = emp_data["applicableEmployees"]
        entry.summary = emp_data["summary"]
        entry.breakfast_items = processed_bf
        entry.common_items = processed_cm
        entry.total_cost = total_cost
        entry.updated_by = current_user.name
    else:
        entry = BreakfastDailyEntry(
            business_date=b_date,
            employee_snapshot=emp_data["applicableEmployees"],
            summary=emp_data["summary"],
            breakfast_items=processed_bf,
            common_items=processed_cm,
            total_cost=total_cost,
            created_by=current_user.name
        )
        db.add(entry)

    db.commit()
    db.refresh(entry)

    after_state = serialize_daily_entry(entry)
    updated_metrics = money_service.get_money_balance_metrics(db)

    audit_service = AuditService(db)
    audit_service.log(
        action=action,
        request=request,
        target_info={
            "businessDate": b_date,
            "totalCost": total_cost,
            "details": f"Daily entry for {b_date} saved with total cost ₹{total_cost:,.2f}"
        },
        before_state=before_state,
        after_state=after_state
    )

    return {
        "success": True,
        "message": f"Daily entry for {b_date} saved successfully",
        "entry": after_state,
        "fundMetrics": updated_metrics
    }

# 10. Additional Orders GET
@router.get("/additional-orders")
def get_additional_orders(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.view")),
    db: Session = Depends(get_db)
):
    target_date = date or get_kolkata_date_string()
    emp_data = bf_service.get_additional_breakfast_employees(target_date, db)
    orders = db.query(BreakfastAdditionalOrder).filter(
        BreakfastAdditionalOrder.business_date == target_date
    ).order_by(desc(BreakfastAdditionalOrder.created_at)).all()
    fund_metrics = money_service.get_money_balance_metrics(db)

    return {
        "success": True,
        "businessDate": target_date,
        "applicableEmployees": emp_data["applicableEmployees"],
        "leaveExcludedEmployees": emp_data["leaveExcludedEmployees"],
        "applicableCount": emp_data["applicableCount"],
        "orders": [serialize_additional_order(o) for o in orders],
        "fundMetrics": fund_metrics
    }

# 11. Additional Orders POST (Create)
@router.post("/additional-orders")
def save_additional_order(
    payload: AdditionalOrderRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    b_date = payload.businessDate.strip()
    if not b_date:
        raise ValidationError("businessDate is required")

    emp_data = bf_service.get_additional_breakfast_employees(b_date, db)
    applicable_count = emp_data["applicableCount"]

    processed_bf = []
    items_total = 0.0
    for item in payload.breakfastItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty = float(item.quantity) if item.quantity is not None else float(applicable_count)
            tot = price * qty
            items_total += tot
            processed_bf.append({
                "name": item.name.strip(),
                "unitPrice": price,
                "quantity": qty,
                "total": tot
            })

    processed_cm = []
    common_total = 0.0
    for item in payload.commonItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty = float(item.quantity) if item.quantity is not None else 1.0
            tot = price * qty
            common_total += tot
            processed_cm.append({
                "name": item.name.strip(),
                "unitPrice": price,
                "quantity": qty,
                "total": tot
            })

    total_cost = items_total + common_total
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    order_id = f"ADD-ORD-{b_date.replace('-', '')}-{str(now_ts)[-4:]}"

    # Charge expense
    money_service.process_additional_order_expense(
        order_id=order_id,
        business_date=b_date,
        order_title=payload.orderTitle or "Additional Breakfast / Snack Order",
        total_cost=total_cost,
        created_by=current_user.name,
        db=db
    )

    now_time = payload.orderTime or get_kolkata_now().strftime("%I:%M %p")

    order = BreakfastAdditionalOrder(
        order_id=order_id,
        business_date=b_date,
        order_title=payload.orderTitle or "Additional Breakfast / Snack Order",
        order_time=now_time,
        applicable_employee_snapshot=emp_data["applicableEmployees"],
        applicable_employee_count=applicable_count,
        breakfast_items=processed_bf,
        common_items=processed_cm,
        total_cost=total_cost,
        created_by=current_user.name
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    serialized = serialize_additional_order(order)
    updated_metrics = money_service.get_money_balance_metrics(db)

    audit_service = AuditService(db)
    audit_service.log(
        action="ADDITIONAL_ORDER_CREATED",
        request=request,
        target_info={
            "orderId": order_id,
            "businessDate": b_date,
            "orderTitle": order.order_title,
            "totalCost": total_cost,
            "details": f"Created additional order ({order.order_title}) on {b_date}. Total cost: ₹{total_cost:,.2f}"
        },
        after_state=serialized
    )

    return {
        "success": True,
        "message": "Additional order saved successfully",
        "order": serialized,
        "fundMetrics": updated_metrics
    }

# 12. Additional Orders PUT (Update)
@router.put("/additional-orders/{id}")
def update_additional_order(
    id: str,
    payload: AdditionalOrderRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    order = db.query(BreakfastAdditionalOrder).filter(
        (BreakfastAdditionalOrder.order_id == id) | (BreakfastAdditionalOrder.id == id)
    ).first()
    if not order:
        raise NotFoundError("Additional order not found")

    before_state = serialize_additional_order(order)
    emp_data = bf_service.get_additional_breakfast_employees(order.business_date, db)
    applicable_count = emp_data["applicableCount"]

    processed_bf = []
    items_total = 0.0
    for item in payload.breakfastItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty = float(item.quantity) if item.quantity is not None else float(applicable_count)
            tot = price * qty
            items_total += tot
            processed_bf.append({
                "name": item.name.strip(),
                "unitPrice": price,
                "quantity": qty,
                "total": tot
            })

    processed_cm = []
    common_total = 0.0
    for item in payload.commonItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty = float(item.quantity) if item.quantity is not None else 1.0
            tot = price * qty
            common_total += tot
            processed_cm.append({
                "name": item.name.strip(),
                "unitPrice": price,
                "quantity": qty,
                "total": tot
            })

    new_total_cost = items_total + common_total

    # Update ledger difference
    money_res = money_service.process_additional_order_update(
        order_id=order.order_id,
        business_date=order.business_date,
        order_title=payload.orderTitle or order.order_title,
        new_total_cost=new_total_cost,
        created_by=current_user.name,
        db=db
    )

    order.order_title = payload.orderTitle or order.order_title
    order.order_time = payload.orderTime or order.order_time
    order.breakfast_items = processed_bf
    order.common_items = processed_cm
    order.total_cost = new_total_cost
    order.updated_by = current_user.name
    db.commit()
    db.refresh(order)

    after_state = serialize_additional_order(order)
    updated_metrics = money_service.get_money_balance_metrics(db)

    audit_service = AuditService(db)
    audit_service.log(
        action="ADDITIONAL_ORDER_UPDATED",
        request=request,
        target_info={
            "orderId": order.order_id,
            "businessDate": order.business_date,
            "previousCost": before_state["totalCost"],
            "newTotalCost": new_total_cost,
            "details": f"Updated additional order ({order.order_title}). Cost changed from ₹{before_state['totalCost']} to ₹{new_total_cost}"
        },
        before_state=before_state,
        after_state=after_state
    )

    return {
        "success": True,
        "message": "Additional order updated successfully",
        "order": after_state,
        "fundMetrics": updated_metrics
    }

# 13. Additional Orders DELETE
@router.delete("/additional-orders/{id}")
def delete_additional_order(
    id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    order = db.query(BreakfastAdditionalOrder).filter(
        (BreakfastAdditionalOrder.order_id == id) | (BreakfastAdditionalOrder.id == id)
    ).first()
    if not order:
        raise NotFoundError("Additional order not found")

    before_state = serialize_additional_order(order)

    # Reverse expense
    money_service.reverse_additional_order_expense(
        order_id=order.order_id,
        business_date=order.business_date,
        order_title=order.order_title,
        created_by=current_user.name,
        db=db
    )

    db.delete(order)
    db.commit()

    updated_metrics = money_service.get_money_balance_metrics(db)

    audit_service = AuditService(db)
    audit_service.log(
        action="ADDITIONAL_ORDER_DELETED",
        request=request,
        target_info={
            "orderId": id,
            "businessDate": order.business_date,
            "totalCost": order.total_cost,
            "details": f"Deleted additional order ({order.order_title}) on {order.business_date}. Reversed ₹{order.total_cost:,.2f} into ledger."
        },
        before_state=before_state
    )

    return {
        "success": True,
        "message": "Additional order deleted successfully and expense reversed in money ledger",
        "fundMetrics": updated_metrics
    }

# 14. All Orders (Unified list of Daily Entries + Additional Orders)
@router.get("/orders")
def get_all_orders(
    page: int = Query(1),
    limit: str = Query("20"),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    type: str = Query("ALL"),
    search: Optional[str] = Query(None),
    createdBy: Optional[str] = Query(None),
    minAmount: Optional[float] = Query(None),
    maxAmount: Optional[float] = Query(None),
    sortBy: str = Query("businessDate"),
    sortOrder: str = Query("desc"),
    current_user: CurrentUser = Depends(require_permission("breakfast.view")),
    db: Session = Depends(get_db)
):
    daily_q = db.query(BreakfastDailyEntry)
    add_q = db.query(BreakfastAdditionalOrder)

    if startDate and endDate:
        daily_q = daily_q.filter(BreakfastDailyEntry.business_date >= startDate, BreakfastDailyEntry.business_date <= endDate)
        add_q = add_q.filter(BreakfastAdditionalOrder.business_date >= startDate, BreakfastAdditionalOrder.business_date <= endDate)
    elif startDate:
        daily_q = daily_q.filter(BreakfastDailyEntry.business_date >= startDate)
        add_q = add_q.filter(BreakfastAdditionalOrder.business_date >= startDate)
    elif endDate:
        daily_q = daily_q.filter(BreakfastDailyEntry.business_date <= endDate)
        add_q = add_q.filter(BreakfastAdditionalOrder.business_date <= endDate)

    daily_entries = []
    if type in ["ALL", "DAILY_ENTRY", "DAILY_BREAKFAST"]:
        daily_entries = daily_q.all()

    additional_orders = []
    if type in ["ALL", "ADDITIONAL_ORDER"]:
        additional_orders = add_q.all()

    mapped_daily = []
    for entry in daily_entries:
        mapped_daily.append({
            "_id": entry.id,
            "orderId": f"DE-{entry.business_date.replace('-', '')}",
            "rawId": str(entry.id),
            "businessDate": entry.business_date,
            "orderType": "DAILY_ENTRY",
            "orderTypeLabel": "DAILY BREAKFAST",
            "orderTitle": f"Daily Breakfast ({entry.business_date})",
            "orderTime": "12:00",
            "applicableEmployeeCount": (entry.summary or {}).get("applicableCount", len(entry.employee_snapshot or [])),
            "takingEmployeeCount": (entry.summary or {}).get("takingCount", 0),
            "notTakingEmployeeCount": (entry.summary or {}).get("notTakingCount", 0),
            "noResponseEmployeeCount": (entry.summary or {}).get("noResponseCount", 0),
            "employeeSnapshot": entry.employee_snapshot or [],
            "breakfastItems": entry.breakfast_items or [],
            "commonItems": entry.common_items or [],
            "totalCost": entry.total_cost or 0.0,
            "createdBy": entry.created_by or "Breakfast Admin",
            "updatedBy": entry.updated_by,
            "createdAt": entry.created_at.isoformat() if entry.created_at else entry.business_date,
            "updatedAt": entry.updated_at.isoformat() if entry.updated_at else None,
            "status": "COMPLETED",
            "financialReference": {
                "referenceType": "DAILY_ENTRY",
                "referenceId": entry.business_date
            }
        })

    mapped_add = []
    for order in additional_orders:
        mapped_add.append({
            "_id": order.id,
            "orderId": order.order_id,
            "rawId": str(order.id),
            "businessDate": order.business_date,
            "orderType": "ADDITIONAL_ORDER",
            "orderTypeLabel": "ADDITIONAL ORDER",
            "orderTitle": order.order_title or "Additional Breakfast Order",
            "orderTime": order.order_time or "15:30",
            "applicableEmployeeCount": order.applicable_employee_count or len(order.applicable_employee_snapshot or []),
            "takingEmployeeCount": order.applicable_employee_count or 0,
            "employeeSnapshot": order.applicable_employee_snapshot or [],
            "breakfastItems": order.breakfast_items or [],
            "commonItems": order.common_items or [],
            "totalCost": order.total_cost or 0.0,
            "createdBy": order.created_by or "Breakfast Admin",
            "updatedBy": order.updated_by,
            "createdAt": order.created_at.isoformat() if order.created_at else order.business_date,
            "updatedAt": order.updated_at.isoformat() if order.updated_at else None,
            "status": "COMPLETED",
            "financialReference": {
                "referenceType": "ADDITIONAL_ORDER",
                "referenceId": order.order_id
            }
        })

    combined = mapped_daily + mapped_add

    if search and search.strip():
        s = search.strip().lower()
        combined = [
            o for o in combined
            if s in o["orderId"].lower()
            or s in o["orderTitle"].lower()
            or s in o["businessDate"].lower()
            or s in o["createdBy"].lower()
            or any(item.get("name") and s in item["name"].lower() for item in o["breakfastItems"])
            or any(item.get("name") and s in item["name"].lower() for item in o["commonItems"])
        ]

    if createdBy and createdBy != "ALL":
        c = createdBy.strip().lower()
        combined = [o for o in combined if c in o["createdBy"].lower()]

    if minAmount is not None:
        combined = [o for o in combined if o["totalCost"] >= float(minAmount)]
    if maxAmount is not None:
        combined = [o for o in combined if o["totalCost"] <= float(maxAmount)]

    # Sorting
    def sort_key(item):
        if sortBy == "totalCost":
            return item["totalCost"]
        elif sortBy == "orderId":
            return item["orderId"]
        else:
            return (item["businessDate"], item.get("createdAt", ""))

    combined.sort(key=sort_key, reverse=(sortOrder.lower() == "desc"))

    tot_count = len(combined)
    tot_amt = sum(o["totalCost"] for o in combined)
    daily_count = sum(1 for o in combined if o["orderType"] == "DAILY_ENTRY")
    add_count = sum(1 for o in combined if o["orderType"] == "ADDITIONAL_ORDER")

    page_num = max(1, int(page))
    limit_num = tot_count if limit == "ALL" else max(1, int(limit))
    tot_pages = math.ceil(tot_count / limit_num) if limit_num > 0 else 1

    start_idx = (page_num - 1) * limit_num
    paginated = combined[start_idx: start_idx + limit_num]

    return {
        "success": True,
        "summary": {
            "totalOrders": tot_count,
            "totalAmount": tot_amt,
            "dailyCount": daily_count,
            "additionalCount": add_count
        },
        "pagination": {
            "total": tot_count,
            "page": page_num,
            "limit": limit_num,
            "totalPages": tot_pages
        },
        "orders": paginated
    }
