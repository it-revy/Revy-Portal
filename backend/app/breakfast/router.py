import os
import math
import uuid
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_any_permission, require_module_access, CurrentUser
from app.core.exceptions import ValidationError, NotFoundError, PermissionDeniedError
from app.employees.model import Employee
from app.breakfast.model import (
    BreakfastRecord,
    BreakfastSetting,
    BreakfastReason,
    BreakfastNonParticipationPeriod,
    BreakfastDailyEntry,
    BreakfastAdditionalOrder,
    PublicHoliday,
    BreakfastTemporaryRequest,
    BreakfastOrder,
    BreakfastOrderItem
)
from app.breakfast import service as bf_service
from app.breakfast import money_service
from app.breakfast import calendar_service
from app.breakfast.date_utils import (
    get_kolkata_date_string,
    get_kolkata_now,
    get_kolkata_time_string,
    to_kolkata_datetime,
    get_formatted_date_and_day,
    is_after_cutoff,
    getNextDayDate,
    get_request_window_for_date,
    is_request_window_open,
    get_applicable_breakfast_date,
    get_authoritative_breakfast_date,
    get_breakfast_window_details,
    get_breakfast_cycle_settings,
    serialize_utc_timestamp
)
from app.audit.service import AuditService

router = APIRouter(prefix="/breakfast", tags=["Breakfast"], dependencies=[Depends(require_module_access("BMS"))])

class SubmitBreakfastRequest(BaseModel):
    response: str
    reasonCode: Optional[str] = None
    reasonText: Optional[str] = None
    businessDate: Optional[str] = None

class CreateTemporaryBreakfastRequest(BaseModel):
    employeeId: Optional[str] = None
    requestedDate: Optional[str] = None
    targetDate: Optional[str] = None
    date: Optional[str] = None
    quantity: Optional[Union[float, int, str]] = 1.0
    notes: Optional[str] = None
    reason: Optional[str] = None

class UpdateTemporaryBreakfastRequest(BaseModel):
    quantity: Optional[Union[float, int, str]] = None
    notes: Optional[str] = None
    status: Optional[str] = None

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
    quantity: Optional[Union[float, int, str]] = None
    total: Optional[float] = None

class SaveDailyEntryRequest(BaseModel):
    businessDate: Optional[str] = None
    date: Optional[str] = None
    recordType: Optional[str] = "CURRENT"
    record_type: Optional[str] = None
    paidBy: Optional[str] = None
    paid_by: Optional[str] = None
    paymentType: Optional[str] = None
    payment_type: Optional[str] = None
    source: Optional[str] = None
    sourceId: Optional[str] = None
    source_id: Optional[str] = None
    breakfastItems: Optional[List[ItemInput]] = []
    commonItems: Optional[List[ItemInput]] = []
    totalQuantity: Optional[Union[float, int, str]] = None
    total_quantity: Optional[Union[float, int, str]] = None
    actualResponseQuantity: Optional[Union[float, int, str]] = None
    actual_response_quantity: Optional[Union[float, int, str]] = None
    employeeRequestQuantity: Optional[Union[float, int, str]] = None
    employee_request_quantity: Optional[Union[float, int, str]] = None

class AdditionalOrderRequest(BaseModel):
    businessDate: str
    orderTitle: Optional[str] = "Additional Breakfast / Snack Order"
    orderTime: Optional[str] = None
    headCount: Optional[Union[int, str]] = None
    head_count: Optional[Union[int, str]] = None
    clientName: Optional[str] = None
    client_name: Optional[str] = None
    breakfastItems: Optional[List[ItemInput]] = []
    commonItems: Optional[List[ItemInput]] = []
    totalQuantity: Optional[Union[float, int, str]] = None
    total_quantity: Optional[Union[float, int, str]] = None

class CreateBreakfastRecordRequest(BaseModel):
    businessDate: Optional[str] = None
    date: Optional[str] = None
    employeeId: Optional[str] = None
    employee_id: Optional[str] = None
    employeeName: Optional[str] = None
    employee_name: Optional[str] = None
    recordType: Optional[str] = None
    record_type: Optional[str] = None
    snack: Optional[str] = None
    snackQuantity: Optional[Union[str, float, int]] = None
    snack_quantity: Optional[Union[str, float, int]] = None
    snackCost: Optional[float] = None
    snack_cost: Optional[float] = None
    fruit: Optional[str] = None
    fruitQuantity: Optional[Union[str, float, int]] = None
    fruit_quantity: Optional[Union[str, float, int]] = None
    fruitCost: Optional[float] = None
    fruit_cost: Optional[float] = None
    totalCost: Optional[float] = None
    total_cost: Optional[float] = None
    paidBy: Optional[str] = None
    paid_by: Optional[str] = None
    paymentType: Optional[str] = None
    payment_type: Optional[str] = None
    source: Optional[str] = None
    sourceId: Optional[str] = None
    source_id: Optional[str] = None
    externalReference: Optional[str] = None
    external_reference: Optional[str] = None
    response: Optional[str] = None
    employeeResponse: Optional[str] = None
    actualStatus: Optional[str] = None
    reasonCode: Optional[str] = None
    reasonText: Optional[str] = None

class BatchRecordsRequest(BaseModel):
    records: List[CreateBreakfastRecordRequest]

class UpdateBreakfastRecordRequest(BaseModel):
    businessDate: Optional[str] = None
    date: Optional[str] = None
    snack: Optional[str] = None
    snackQuantity: Optional[Union[str, float, int]] = None
    snack_quantity: Optional[Union[str, float, int]] = None
    snackCost: Optional[float] = None
    snack_cost: Optional[float] = None
    fruit: Optional[str] = None
    fruitQuantity: Optional[Union[str, float, int]] = None
    fruit_quantity: Optional[Union[str, float, int]] = None
    fruitCost: Optional[float] = None
    fruit_cost: Optional[float] = None
    totalCost: Optional[float] = None
    total_cost: Optional[float] = None
    paidBy: Optional[str] = None
    paid_by: Optional[str] = None
    paymentType: Optional[str] = None
    payment_type: Optional[str] = None
    response: Optional[str] = None
    actualStatus: Optional[str] = None
    reasonCode: Optional[str] = None
    reasonText: Optional[str] = None

def serialize_record(r: Optional[BreakfastRecord]):
    if not r:
        return None
    is_historical = (r.record_type or "CURRENT") == "HISTORICAL"
    return {
        "_id": r.id,
        "id": r.id,
        "recordId": r.record_id,
        "employeeId": None if is_historical else r.employee_id,
        "employeeName": ("Not Recorded" if not r.employee_name else r.employee_name) if is_historical else r.employee_name,
        "businessDate": r.business_date,
        "recordType": r.record_type or "CURRENT",
        "isHistorical": is_historical,
        "snack": r.snack,
        "snackQuantity": r.snack_quantity,
        "snackCost": float(r.snack_cost) if r.snack_cost is not None else 0.0,
        "fruit": r.fruit,
        "fruitQuantity": r.fruit_quantity,
        "fruitCost": float(r.fruit_cost) if r.fruit_cost is not None else 0.0,
        "totalCost": float(r.total_cost) if r.total_cost is not None else 0.0,
        "paidBy": r.paid_by,
        "paymentType": r.payment_type,
        "source": r.source,
        "sourceId": r.source_id,
        "externalReference": r.external_reference,
        "response": r.response,
        "employeeResponse": r.employee_response,
        "actualStatus": r.actual_status,
        "actualStatusSource": r.actual_status_source,
        "reasonCode": r.reason_code,
        "reasonText": r.reason_text,
        "submittedAt": serialize_utc_timestamp(r.submitted_at),
        "history": r.history or [],
        "createdAt": serialize_utc_timestamp(r.created_at),
        "updatedAt": serialize_utc_timestamp(r.updated_at)
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
        "createdAt": serialize_utc_timestamp(p.created_at)
    }

def serialize_daily_entry(e: Optional[BreakfastDailyEntry]):
    if not e:
        return None
    is_historical = getattr(e, "record_type", "CURRENT") == "HISTORICAL"
    summary = dict(e.summary or {})
    actual_qty = summary.get("actualResponseQuantity", summary.get("actualTakenCount", 0))
    taking_cnt = summary.get("employeeRequestQuantity", summary.get("takingCount", 0))
    if "actualResponseQuantity" not in summary:
        summary["actualResponseQuantity"] = float(actual_qty)
    if "employeeRequestQuantity" not in summary:
        summary["employeeRequestQuantity"] = float(taking_cnt)
    if "totalQuantity" not in summary:
        summary["totalQuantity"] = float(actual_qty)

    tot_qty = getattr(e, "total_quantity", None)
    if tot_qty is None:
        tot_qty = summary.get("totalQuantity", float(actual_qty))

    return {
        "_id": e.id,
        "id": e.id,
        "businessDate": e.business_date,
        "employeeSnapshot": [] if is_historical else (e.employee_snapshot or []),
        "summary": summary,
        "breakfastItems": e.breakfast_items or [],
        "commonItems": e.common_items or [],
        "totalCost": e.total_cost,
        "totalQuantity": tot_qty,
        "actualResponseQuantity": summary.get("actualResponseQuantity", float(actual_qty)),
        "employeeRequestQuantity": summary.get("employeeRequestQuantity", float(taking_cnt)),
        "recordType": getattr(e, "record_type", "CURRENT"),
        "isHistorical": is_historical,
        "paidBy": getattr(e, "paid_by", None),
        "paymentType": getattr(e, "payment_type", None),
        "source": getattr(e, "source", "OPERATIONAL"),
        "sourceId": getattr(e, "source_id", None),
        "createdBy": e.created_by,
        "updatedBy": e.updated_by,
        "createdAt": serialize_utc_timestamp(e.created_at),
        "updatedAt": serialize_utc_timestamp(e.updated_at)
    }

def serialize_additional_order(o: BreakfastAdditionalOrder):
    tot_qty = getattr(o, "total_quantity", None)
    if tot_qty is None:
        tot_qty = sum(float(i.get("quantity") or 0) for i in (o.breakfast_items or []))
    return {
        "_id": o.id,
        "id": o.id,
        "orderId": o.order_id,
        "businessDate": o.business_date,
        "orderTitle": o.order_title,
        "clientName": getattr(o, "client_name", None),
        "headCount": getattr(o, "head_count", None),
        "orderTime": o.order_time,
        "applicableEmployeeSnapshot": o.applicable_employee_snapshot or [],
        "applicableEmployeeCount": o.applicable_employee_count,
        "breakfastItems": o.breakfast_items or [],
        "commonItems": o.common_items or [],
        "totalCost": o.total_cost,
        "totalQuantity": tot_qty,
        "createdBy": o.created_by,
        "updatedBy": o.updated_by,
        "createdAt": serialize_utc_timestamp(o.created_at),
        "updatedAt": serialize_utc_timestamp(o.updated_at)
    }

def serialize_temporary_request(req: BreakfastTemporaryRequest):
    if not req:
        return None
    return {
        "_id": req.id,
        "id": req.id,
        "requestId": req.request_id,
        "employeeId": req.employee_id,
        "employeeName": req.employee_name,
        "requestedDate": req.requested_date,
        "targetDate": req.requested_date,
        "quantity": float(req.quantity) if req.quantity is not None else 1.0,
        "status": req.status,
        "notes": req.notes or "",
        "createdAt": serialize_utc_timestamp(req.created_at),
        "updatedAt": serialize_utc_timestamp(req.updated_at)
    }

# 1. Personal Breakfast Status (Today / Active Window)
@router.get("/today")
def get_today_status(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now_ist = get_kolkata_now()
    open_t, close_t, _ = get_breakfast_cycle_settings(db)

    if date and len(date.strip()) == 10:
        try:
            target_date_obj = datetime.strptime(date.strip(), "%Y-%m-%d").date()
        except ValueError:
            target_date_obj = get_applicable_breakfast_date(now_ist, open_t, close_t)
    else:
        target_date_obj = get_applicable_breakfast_date(now_ist, open_t, close_t)

    window_info = get_breakfast_window_details(target_date=target_date_obj, now=now_ist, open_time=open_t, close_time=close_t)
    active_date_str = window_info["targetDate"]
    active_formatted = window_info["targetDateFullFormatted"]
    today_info = get_formatted_date_and_day(now_ist)

    is_holiday = db.query(PublicHoliday).filter(
        PublicHoliday.date == active_date_str,
        PublicHoliday.status == "active"
    ).first()

    today_record = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == current_user.employee_id,
        BreakfastRecord.business_date == active_date_str
    ).first()

    temp_req = db.query(BreakfastTemporaryRequest).filter(
        BreakfastTemporaryRequest.employee_id == current_user.employee_id,
        BreakfastTemporaryRequest.requested_date == active_date_str,
        BreakfastTemporaryRequest.status != "CANCELLED"
    ).first()

    reasons = db.query(BreakfastReason).filter(BreakfastReason.is_active == True).order_by(BreakfastReason.display_order.asc()).all()
    formatted_reasons = [
        {"_id": r.id, "id": r.id, "code": r.code, "label": r.label, "isCustomAllowed": r.is_custom_allowed}
        for r in reasons
    ]

    is_perm = (current_user.breakfast_participation_type or "").upper() in ["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"]

    # Authoritatively determine response status for the active business date
    if today_record:
        if today_record.response in ["YES", "TAKING"] or today_record.employee_response == "TAKING":
            response_status = "TAKING"
        elif today_record.response in ["NO", "NOT_TAKING"] or today_record.employee_response == "NOT_TAKING":
            response_status = "NOT_TAKING"
        else:
            response_status = "NO_RESPONSE"
    elif temp_req:
        response_status = "TAKING"
    elif is_perm:
        response_status = "NOT_TAKING"
    else:
        response_status = "NO_RESPONSE"

    request_window = {
        "opensAt": window_info["windowStart"],
        "closesAt": window_info["windowEnd"],
        "status": window_info["statusCode"],
        "isOpen": window_info["isOpen"],
        "windowStartDisplay": window_info["windowStartDisplay"],
        "windowEndDisplay": window_info["windowEndDisplay"]
    }

    return {
        "success": True,
        "businessDate": active_date_str,
        "targetDate": active_date_str,
        "todayFormattedDisplay": today_info["displayString"],
        "activeFormattedDisplay": active_formatted,
        "targetDateFormatted": window_info["targetDateFormatted"],
        "isCutoffPassed": not window_info["isOpen"],
        "isOpen": window_info["isOpen"],
        "isWindowOpen": window_info["isOpen"],
        "windowStatus": window_info["statusCode"],
        "windowStatusLabel": window_info["statusLabel"],
        "windowStart": window_info["windowStart"],
        "windowEnd": window_info["windowEnd"],
        "windowStartDisplay": window_info["windowStartDisplay"],
        "windowEndDisplay": window_info["windowEndDisplay"],
        "requestWindow": request_window,
        "currentIstTime": window_info["currentIstTime"],
        "cutoffTime": close_t,
        "requestOpenTime": open_t,
        "requestCloseTime": close_t,
        "employeeId": current_user.employee_id,
        "name": current_user.name,
        "participationType": current_user.breakfast_participation_type,
        "isPermanentNotTaking": is_perm,
        "isPublicHoliday": bool(is_holiday),
        "holidayName": is_holiday.name if is_holiday else None,
        "todayRecord": serialize_record(today_record),
        "targetDateRecord": serialize_record(today_record),
        "calendarRecord": None,
        "responseStatus": response_status,
        "temporaryRequest": serialize_temporary_request(temp_req),
        "reasons": formatted_reasons
    }

# 1b. Authoritative Active Business Date Endpoint
@router.get("/active-date")
@router.get("/business-date")
def get_active_business_date_endpoint(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now_ist = get_kolkata_now()
    open_t, close_t, _ = get_breakfast_cycle_settings(db)
    target_date_obj = get_applicable_breakfast_date(now=now_ist, open_time=open_t, close_time=close_t)
    active_date_str = target_date_obj.strftime("%Y-%m-%d")
    window_info = get_breakfast_window_details(target_date=target_date_obj, now=now_ist, open_time=open_t, close_time=close_t)
    return {
        "success": True,
        "businessDate": active_date_str,
        "targetDateFormatted": window_info["targetDateFormatted"],
        "targetDateFullFormatted": window_info["targetDateFullFormatted"],
        "requestWindow": {
            "opensAt": window_info["windowStart"],
            "closesAt": window_info["windowEnd"],
            "status": window_info["statusCode"],
            "isOpen": window_info["isOpen"],
            "windowStartDisplay": window_info["windowStartDisplay"],
            "windowEndDisplay": window_info["windowEndDisplay"]
        },
        "currentTimeIst": now_ist.strftime("%d %b %Y, %I:%M:%S %p IST"),
        "timezone": "Asia/Kolkata"
    }

# 2. Submit Daily Breakfast Response
@router.post("/submit")
def submit_daily_breakfast(
    payload: SubmitBreakfastRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_perm = (current_user.breakfast_participation_type or "").upper() in ["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"]

    now_ist = get_kolkata_now()
    open_t, close_t, _ = get_breakfast_cycle_settings(db)

    if payload.businessDate and len(payload.businessDate.strip()) == 10:
        try:
            target_date_obj = datetime.strptime(payload.businessDate.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Invalid businessDate format. Expected YYYY-MM-DD")
    else:
        target_date_obj = get_applicable_breakfast_date(now_ist, open_t, close_t)

    target_date_str = target_date_obj.strftime("%Y-%m-%d")
    target_dt_full = datetime(target_date_obj.year, target_date_obj.month, target_date_obj.day, 10, 0, 0, tzinfo=now_ist.tzinfo)
    target_info = get_formatted_date_and_day(target_dt_full)

    # STRICT SERVER-SIDE VALIDATION: Request window is configured open_time to close_time IST
    is_testing = os.getenv("TESTING") == "1" or settings.ENVIRONMENT in ["test", "testing"]
    if not is_testing:
        w_start, w_end = get_request_window_for_date(target_date_obj, open_time=open_t, close_time=close_t)
        if not (w_start <= now_ist < w_end):
            w_start_str = w_start.strftime("%d %b %Y, %I:%M %p")
            w_end_str = w_end.strftime("%d %b %Y, %I:%M %p")
            target_disp = target_date_obj.strftime("%d %b %Y")
            raise ValidationError(
                f"Breakfast request window is closed for {target_disp}. "
                f"Requests are accepted from {w_start_str} to {w_end_str} IST."
            )

    resp = payload.response.upper()
    if resp not in ["YES", "NO", "TAKING", "NOT_TAKING"]:
        raise ValidationError("Response must be YES or NO")

    normalized_resp = "YES" if resp in ["YES", "TAKING"] else "NO"
    emp_resp = "TAKING" if normalized_resp == "YES" else "NOT_TAKING"

    # Handle Permanent Non-Taker Exception
    if is_perm:
        if normalized_resp == "YES":
            existing_temp = db.query(BreakfastTemporaryRequest).filter(
                BreakfastTemporaryRequest.employee_id == current_user.employee_id,
                BreakfastTemporaryRequest.requested_date == target_date_str,
                BreakfastTemporaryRequest.status != "CANCELLED"
            ).first()
            if not existing_temp:
                req_id = f"REQ-{target_date_str.replace('-', '')}-{uuid.uuid4().hex[:4].upper()}"
                existing_temp = BreakfastTemporaryRequest(
                    request_id=req_id,
                    employee_id=current_user.employee_id,
                    employee_name=current_user.name,
                    requested_date=target_date_str,
                    quantity=1.0,
                    status="CONFIRMED",
                    notes="Daily submit one-day request"
                )
                db.add(existing_temp)
                db.flush()
        else:
            existing_temp = db.query(BreakfastTemporaryRequest).filter(
                BreakfastTemporaryRequest.employee_id == current_user.employee_id,
                BreakfastTemporaryRequest.requested_date == target_date_str,
                BreakfastTemporaryRequest.status != "CANCELLED"
            ).first()
            if existing_temp:
                existing_temp.status = "CANCELLED"
                db.flush()

    final_reason_code = None
    final_reason_text = None

    if normalized_resp == "NO":
        if is_perm:
            final_reason_code = "PERMANENT_NOT_TAKING"
            final_reason_text = "Permanent Non-Participant"
        else:
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
    elif is_perm:
        final_reason_code = "ONE_DAY_REQUEST"
        final_reason_text = "One-day breakfast request"

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
            "updatedAt": serialize_utc_timestamp(datetime.now(timezone.utc)),
            "updatedBy": current_user.name
        })
        existing_record.history = hist
        existing_record.response = normalized_resp
        existing_record.employee_response = emp_resp
        existing_record.actual_status = "TAKEN" if normalized_resp == "YES" else "NOT_TAKEN"
        existing_record.source = "TEMPORARY_REQUEST" if is_perm else "EMPLOYEE"
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
            actual_status="TAKEN" if normalized_resp == "YES" else "NOT_TAKEN",
            reason_code=final_reason_code,
            reason_text=final_reason_text,
            source="TEMPORARY_REQUEST" if is_perm else "EMPLOYEE",
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
            "details": f"Response for {target_info['displayString']}: {normalized_resp}" + (" (Permanent Non-Taker one-day exception)" if is_perm else "")
        },
        before_state=before_state,
        after_state=after_state
    )

    msg = f"Breakfast response for {target_info['displayString']} saved successfully"
    if is_perm and normalized_resp == "YES":
        msg = f"One-day breakfast request confirmed for {target_info['displayString']}. Your permanent non-taker profile status remains unchanged."

    return {
        "success": True,
        "message": msg,
        "record": after_state
    }

# 2b. Specific-Date Breakfast Request for Permanent Non-Takers
@router.post("/temporary-request")
@router.post("/temporary-requests")
def create_temporary_breakfast_request(
    payload: CreateTemporaryBreakfastRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req_date = (payload.requestedDate or payload.targetDate or payload.date or "").strip()
    if not req_date or len(req_date) != 10:
        raise ValidationError("Valid requestedDate or targetDate (YYYY-MM-DD) is required")
    try:
        datetime.strptime(req_date, "%Y-%m-%d")
    except ValueError:
        raise ValidationError("Invalid date format. Expected YYYY-MM-DD")

    try:
        qty = float(payload.quantity) if payload.quantity is not None else 1.0
        if qty <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValidationError("Quantity must be a positive number")

    target_emp_id = current_user.employee_id
    target_emp_name = current_user.name
    is_admin = ("BREAKFAST_ADMIN" in current_user.roles or "IT_ADMIN" in current_user.roles or "BMS_ADMIN" in current_user.roles or "BMS_BF_MANAGER" in current_user.roles or "*" in current_user.permissions)
    if payload.employeeId and is_admin:
        target_emp = db.query(Employee).filter(Employee.employee_id == payload.employeeId.upper()).first()
        if target_emp:
            target_emp_id = target_emp.employee_id
            target_emp_name = target_emp.name

    # Validate window for non-admin requests if requesting for current/past date
    if not is_admin:
        open_t, close_t, _ = get_breakfast_cycle_settings(db)
        req_date_obj = datetime.strptime(req_date, "%Y-%m-%d").date()
        w_start, w_end = get_request_window_for_date(req_date_obj, open_time=open_t, close_time=close_t)
        now_ist = get_kolkata_now()
        if req_date_obj <= now_ist.date() and not (w_start <= now_ist < w_end):
            w_start_str = w_start.strftime("%d %b %Y, %I:%M %p")
            w_end_str = w_end.strftime("%d %b %Y, %I:%M %p")
            raise ValidationError(
                f"Breakfast request window is closed for {req_date_obj.strftime('%d %b %Y')}. "
                f"Requests were accepted from {w_start_str} to {w_end_str} IST."
            )

    # Prevent duplicate requests for the same date
    existing_req = db.query(BreakfastTemporaryRequest).filter(
        BreakfastTemporaryRequest.employee_id == target_emp_id,
        BreakfastTemporaryRequest.requested_date == req_date,
        BreakfastTemporaryRequest.status != "CANCELLED"
    ).first()

    if existing_req:
        raise ValidationError(f"A temporary request already exists for this date ({req_date}). Please update or cancel the existing request.")

    req_id = f"REQ-{req_date.replace('-', '')}-{uuid.uuid4().hex[:4].upper()}"
    req_obj = BreakfastTemporaryRequest(
        request_id=req_id,
        employee_id=target_emp_id,
        employee_name=target_emp_name,
        requested_date=req_date,
        quantity=qty,
        status="CONFIRMED",
        notes=(payload.notes or payload.reason or "").strip()
    )
    db.add(req_obj)

    # Sync corresponding BreakfastRecord for req_date
    rec = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == target_emp_id,
        BreakfastRecord.business_date == req_date
    ).first()

    if rec:
        rec.response = "YES"
        rec.employee_response = "TAKING"
        rec.actual_status = "TAKEN"
        rec.source = "TEMPORARY_REQUEST"
        rec.reason_code = "ONE_DAY_REQUEST"
        rec.reason_text = f"One-day request ({qty} portions)"
    else:
        rec_id = f"BRK-{req_date.replace('-', '')}-{target_emp_id}"
        rec = BreakfastRecord(
            record_id=rec_id,
            employee_id=target_emp_id,
            business_date=req_date,
            response="YES",
            employee_response="TAKING",
            actual_status="TAKEN",
            source="TEMPORARY_REQUEST",
            reason_code="ONE_DAY_REQUEST",
            reason_text=f"One-day request ({qty} portions)",
            submitted_at=datetime.now(timezone.utc),
            history=[]
        )
        db.add(rec)

    db.commit()
    db.refresh(req_obj)

    serialized = serialize_temporary_request(req_obj)

    audit_service = AuditService(db)
    audit_service.log(
        action="TEMPORARY_BREAKFAST_REQUEST_CREATED",
        request=request,
        target_info={
            "requestId": req_obj.request_id,
            "targetEmployeeId": target_emp_id,
            "targetEmployeeName": target_emp_name,
            "requestedDate": req_date,
            "quantity": qty,
            "details": f"One-day breakfast request for {req_date} with quantity {qty}"
        },
        after_state=serialized
    )

    return {
        "success": True,
        "message": f"One-day breakfast request for {req_date} ({qty} portion{'s' if qty != 1 else ''}) submitted successfully. Your permanent non-taker status remains unchanged.",
        "request": serialized,
        "data": serialized
    }

@router.get("/temporary-requests")
def get_temporary_breakfast_requests(
    employee_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(BreakfastTemporaryRequest)
    is_admin = ("*" in current_user.permissions or "breakfast.view" in current_user.permissions)
    if not is_admin:
        query = query.filter(BreakfastTemporaryRequest.employee_id == current_user.employee_id)
    elif employee_id:
        query = query.filter(BreakfastTemporaryRequest.employee_id == employee_id.upper())

    if date:
        query = query.filter(BreakfastTemporaryRequest.requested_date == date)
    if status and status != "ALL":
        query = query.filter(BreakfastTemporaryRequest.status == status)

    requests = query.order_by(desc(BreakfastTemporaryRequest.requested_date)).all()
    return {
        "success": True,
        "requests": [serialize_temporary_request(r) for r in requests]
    }

@router.put("/temporary-requests/{request_id}")
def update_temporary_breakfast_request(
    request_id: str,
    payload: UpdateTemporaryBreakfastRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    temp_req = db.query(BreakfastTemporaryRequest).filter(
        BreakfastTemporaryRequest.request_id == request_id
    ).first()
    if not temp_req:
        raise NotFoundError("Temporary breakfast request not found")

    is_admin = ("*" in current_user.permissions or "breakfast.manage" in current_user.permissions)
    if not is_admin and temp_req.employee_id != current_user.employee_id:
        raise PermissionDeniedError("Cannot modify another employee's request")

    if payload.quantity is not None:
        try:
            qty = float(payload.quantity)
            if qty <= 0:
                raise ValueError()
            temp_req.quantity = qty
        except (ValueError, TypeError):
            raise ValidationError("Quantity must be a positive number")

    if payload.notes is not None:
        temp_req.notes = payload.notes.strip()

    if payload.status is not None:
        temp_req.status = payload.status

    rec = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == temp_req.employee_id,
        BreakfastRecord.business_date == temp_req.requested_date
    ).first()

    if rec:
        if temp_req.status == "CANCELLED":
            rec.response = "NO"
            rec.employee_response = "NOT_TAKING"
            rec.actual_status = "NOT_TAKEN"
            rec.reason_code = "CANCELLED_REQUEST"
            rec.reason_text = "Temporary request cancelled"
        else:
            rec.response = "YES"
            rec.employee_response = "TAKING"
            rec.actual_status = "TAKEN"
            rec.reason_text = f"One-day request ({temp_req.quantity} portions)"

    db.commit()
    db.refresh(temp_req)

    serialized = serialize_temporary_request(temp_req)
    return {
        "success": True,
        "message": f"Temporary request {temp_req.request_id} updated successfully",
        "request": serialized,
        "data": serialized
    }

@router.delete("/temporary-requests/{request_id}")
def delete_temporary_breakfast_request(
    request_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    temp_req = db.query(BreakfastTemporaryRequest).filter(
        BreakfastTemporaryRequest.request_id == request_id
    ).first()
    if not temp_req:
        raise NotFoundError("Temporary breakfast request not found")

    is_admin = ("*" in current_user.permissions or "breakfast.manage" in current_user.permissions)
    if not is_admin and temp_req.employee_id != current_user.employee_id:
        raise PermissionDeniedError("Cannot cancel another employee's request")

    temp_req.status = "CANCELLED"

    rec = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == temp_req.employee_id,
        BreakfastRecord.business_date == temp_req.requested_date
    ).first()
    if rec:
        rec.response = "NO"
        rec.employee_response = "NOT_TAKING"
        rec.actual_status = "NOT_TAKEN"
        rec.reason_code = "CANCELLED_REQUEST"
        rec.reason_text = "Temporary request cancelled"

    db.commit()
    db.refresh(temp_req)
    serialized = serialize_temporary_request(temp_req)

    return {
        "success": True,
        "message": f"Temporary breakfast request for {temp_req.requested_date} cancelled successfully",
        "request": serialized,
        "data": serialized
    }

@router.put("/temporary-requests/{request_id}/cancel")
def cancel_temporary_breakfast_request(
    request_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return delete_temporary_breakfast_request(request_id, request, current_user, db)


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
    target_date = date or get_authoritative_breakfast_date(db)

    is_holiday = db.query(PublicHoliday).filter(
        PublicHoliday.date == target_date,
        PublicHoliday.status == "active"
    ).first()

    active_emps = db.query(Employee).filter(
        Employee.status == "active",
        Employee.is_hard_deleted == False
    ).all()
    normal_emps = [e for e in active_emps if (e.breakfast_participation_type or "").upper() in ["NORMAL", "REGULAR", "REGULAR_TAKER"]]
    perm_emps = [e for e in active_emps if (e.breakfast_participation_type or "").upper() in ["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"]]

    today_recs = db.query(BreakfastRecord).filter(
        BreakfastRecord.business_date == target_date,
        BreakfastRecord.record_type == "CURRENT"
    ).all()

    emp_data = bf_service.get_daily_breakfast_employees(target_date, db)
    summary = emp_data["summary"]

    open_t, close_t, _ = get_breakfast_cycle_settings(db)
    cutoff_time = close_t

    # Calculate actual breakfast cost for target_date from daily entry, additional orders, and individual orders
    daily_entry = db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == target_date).first()
    daily_entry_cost = float(daily_entry.total_cost or 0.0) if daily_entry else 0.0

    daily_add_orders = db.query(BreakfastAdditionalOrder).filter(BreakfastAdditionalOrder.business_date == target_date).all()
    additional_orders_cost = float(sum(o.total_cost or 0.0 for o in daily_add_orders))

    order_items = db.query(BreakfastOrderItem).filter(BreakfastOrderItem.business_date == target_date).all()
    order_items_cost = float(sum(i.total or 0.0 for i in order_items))

    hist_records = db.query(BreakfastRecord).filter(
        BreakfastRecord.business_date == target_date,
        BreakfastRecord.record_type == "HISTORICAL"
    ).all()
    historical_cost = float(sum(
        (r.total_cost or 0.0) if (r.total_cost and r.total_cost > 0) else ((r.snack_cost or 0.0) + (r.fruit_cost or 0.0))
        for r in hist_records
    )) if not daily_entry else 0.0

    today_breakfast_cost = round(daily_entry_cost + additional_orders_cost + order_items_cost + historical_cost, 2)

    return {
        "success": True,
        "businessDate": target_date,
        "isPublicHoliday": bool(is_holiday),
        "holidayName": is_holiday.name if is_holiday else None,
        "cutoffTime": cutoff_time,
        "requestOpenTime": open_t,
        "requestCloseTime": close_t,
        "isCutoffPassed": is_after_cutoff(cutoff_time),
        "metrics": {
            "totalActive": summary["totalActive"],
            "normalEmployeesCount": len(normal_emps),
            "permanentNotTakingCount": summary["permanentNotTaking"],
            "takingBreakfastCount": summary["takingCount"],
            "notTakingBreakfastCount": summary["notTakingCount"],
            "pendingCount": summary["noResponseCount"],
            "expectedBreakfastCount": 0 if is_holiday else summary["takingCount"],
            "actuallyTakenCount": summary["actualTakenCount"],
            "actuallyNotTakenCount": summary["actualNotTakenCount"],
            "employeeRequestQuantity": float(summary["employeeRequestQuantity"]),
            "actualResponseQuantity": float(summary["actualResponseQuantity"]),
            "totalQuantity": float(summary["totalQuantity"]),
            "temporaryRequestsCount": summary["temporaryRequestsCount"],
            "todayBreakfastCost": today_breakfast_cost,
            "dailyCost": today_breakfast_cost,
            "totalBreakfastCost": today_breakfast_cost
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
    target_date = date or get_authoritative_breakfast_date(db)
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
    record_map = {r.employee_id.upper(): r for r in records if r.employee_id and r.record_type == "CURRENT"}
    historical_records = [serialize_record(r) for r in records if r.record_type == "HISTORICAL"]

    temp_requests = db.query(BreakfastTemporaryRequest).filter(
        BreakfastTemporaryRequest.requested_date == target_date,
        BreakfastTemporaryRequest.status != "CANCELLED"
    ).all()
    temp_req_map = {tr.employee_id.upper(): tr for tr in temp_requests}

    all_list = []
    for emp in employees:
        rec = record_map.get(emp.employee_id.upper())
        is_perm = (emp.breakfast_participation_type or "").upper() in ["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"]
        temp_req = temp_req_map.get(emp.employee_id.upper())

        emp_response = "NO_RESPONSE"
        act_status = "NO_RESPONSE"
        act_source = rec.actual_status_source if rec else ("TEMPORARY_REQUEST" if temp_req else "EMPLOYEE_RESPONSE")

        if temp_req:
            emp_response = "TAKING"
            act_status = rec.actual_status if (rec and rec.actual_status) else "TAKEN"
            r_code = "ONE_DAY_REQUEST"
            r_text = f"One-Day Request ({temp_req.quantity} portions)"
        elif is_perm:
            emp_response = "NOT_TAKING"
            act_status = "NOT_TAKEN"
            r_code = "PERMANENT_NOT_TAKING"
            r_text = "Permanent Non-Participant"
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
            r_code = rec.reason_code
            r_text = rec.reason_text
        else:
            r_code = None
            r_text = None

        all_list.append({
            "employeeId": emp.employee_id,
            "username": emp.user.username if emp.user else "",
            "name": emp.name,
            "department": emp.department,
            "designation": emp.designation,
            "participationType": emp.breakfast_participation_type,
            "isTemporaryRequest": bool(temp_req),
            "temporaryRequestId": temp_req.request_id if temp_req else None,
            "requestedQuantity": float(temp_req.quantity) if temp_req else (1.0 if emp_response == "TAKING" else 0.0),
            "employeeResponse": emp_response,
            "actualStatus": act_status,
            "actualStatusSource": act_source,
            "reasonCode": r_code,
            "reasonText": r_text,
            "source": "TEMPORARY_REQUEST" if temp_req else (rec.source if rec else "EMPLOYEE")
        })

    return {
        "success": True,
        "businessDate": target_date,
        "dayStatus": day_status,
        "allList": all_list,
        "historicalRecords": historical_records,
        "hasHistorical": len(historical_records) > 0
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
            response="NO_RESPONSE",
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
            "updatedAt": serialize_utc_timestamp(datetime.now(timezone.utc)),
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
@router.get("/daily-entries")
def get_daily_entry(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.view")),
    db: Session = Depends(get_db)
):
    target_date = date or get_authoritative_breakfast_date(db)
    open_t, close_t, _ = get_breakfast_cycle_settings(db)
    try:
        target_d_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        target_d_obj = get_kolkata_now().date()
    window_info = get_breakfast_window_details(target_date=target_d_obj, now=get_kolkata_now(), open_time=open_t, close_time=close_t)

    emp_data = bf_service.get_daily_breakfast_employees(target_date, db)
    existing_entry = db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == target_date).first()
    historical_records = db.query(BreakfastRecord).filter(
        BreakfastRecord.business_date == target_date,
        BreakfastRecord.record_type == "HISTORICAL"
    ).all()
    fund_metrics = money_service.get_money_balance_metrics(db)

    is_entry_historical = bool(existing_entry and getattr(existing_entry, "record_type", "CURRENT") == "HISTORICAL")
    has_historical = len(historical_records) > 0 or is_entry_historical

    return {
        "success": True,
        "businessDate": target_date,
        "requestWindow": {
            "windowStartDisplay": window_info["windowStartDisplay"],
            "windowEndDisplay": window_info["windowEndDisplay"],
            "isOpen": window_info["isOpen"],
            "statusCode": window_info["statusCode"],
            "statusLabel": window_info["statusLabel"]
        },
        "existingEntry": serialize_daily_entry(existing_entry),
        "historicalRecords": [serialize_record(r) for r in historical_records],
        "hasHistorical": has_historical,
        "applicableEmployees": emp_data["applicableEmployees"] if not is_entry_historical else [],
        "permExcludedEmployees": emp_data["permExcludedEmployees"] if not is_entry_historical else [],
        "leaveExcludedEmployees": emp_data["leaveExcludedEmployees"] if not is_entry_historical else [],
        "summary": emp_data["summary"] if not is_entry_historical else {
            "applicableCount": 0,
            "takingCount": 0,
            "employeeRequestQuantity": 0.0,
            "actualTakenCount": 0,
            "actualResponseQuantity": 0.0,
            "totalQuantity": 0.0,
            "isHistorical": True
        },
        "fundMetrics": fund_metrics
    }

# 9. Daily Entry POST (Save/Update)
@router.post("/daily-entry")
@router.post("/daily-entries")
def save_daily_entry(
    payload: SaveDailyEntryRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    b_date = (payload.businessDate or payload.date or "").strip()
    if not b_date:
        raise ValidationError("businessDate or date is required")

    rec_type = (payload.recordType or payload.record_type or "CURRENT").upper()
    paid_by = payload.paidBy or payload.paid_by
    payment_type = payload.paymentType or payload.payment_type
    src = payload.source or ("HISTORICAL_IMPORT" if rec_type == "HISTORICAL" else "OPERATIONAL")
    src_id = payload.sourceId or payload.source_id

    emp_data = bf_service.get_daily_breakfast_employees(b_date, db)
    taking_count = emp_data["summary"]["takingCount"]
    actual_response_qty = emp_data["summary"].get("actualResponseQuantity", emp_data["summary"].get("actualTakenCount", 0))

    # Total quantity is based on Actual Response Quantity
    total_qty_input = payload.totalQuantity if payload.totalQuantity is not None else payload.total_quantity
    try:
        total_quantity = float(total_qty_input) if total_qty_input is not None and str(total_qty_input).strip() != "" else float(actual_response_qty)
    except (ValueError, TypeError):
        total_quantity = float(actual_response_qty)

    processed_bf = []
    items_total = 0.0
    for item in payload.breakfastItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty_raw = item.quantity
            try:
                qty_num = float(qty_raw) if qty_raw is not None and str(qty_raw).strip() != "" else float(actual_response_qty)
            except (ValueError, TypeError):
                qty_num = float(actual_response_qty) if actual_response_qty > 0 else 1.0
            tot = round(float(item.total) if item.total is not None and item.total > 0 else (price * qty_num), 2)
            items_total += tot
            processed_bf.append({
                "name": item.name.strip(),
                "unitPrice": price,
                "quantity": qty_num,
                "total": tot
            })

    processed_cm = []
    common_total = 0.0
    for item in payload.commonItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty_raw = item.quantity
            try:
                qty_num = float(qty_raw) if qty_raw is not None and str(qty_raw).strip() != "" else 1.0
            except (ValueError, TypeError):
                qty_num = 1.0
            tot = round(float(item.total) if item.total is not None and item.total > 0 else (price * qty_num), 2)
            common_total += tot
            processed_cm.append({
                "name": item.name.strip(),
                "unitPrice": price,
                "quantity": qty_num,
                "total": tot
            })

    total_cost = round(items_total + common_total, 2)

    # Process money ledger ONLY for current operational records, NOT historical
    if rec_type != "HISTORICAL":
        money_service.process_daily_entry_expense(
            business_date=b_date,
            new_total_cost=total_cost,
            created_by=current_user.name,
            db=db
        )

    entry = db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == b_date).first()
    action = "DAILY_ENTRY_UPDATED" if entry else "DAILY_ENTRY_CREATED"
    before_state = serialize_daily_entry(entry)

    entry_summary = dict(emp_data["summary"]) if rec_type != "HISTORICAL" else {
        "applicableCount": 0,
        "takingCount": 0,
        "employeeRequestQuantity": 0.0,
        "actualTakenCount": 0,
        "actualResponseQuantity": 0.0,
        "totalQuantity": 0.0,
        "isHistorical": True
    }
    entry_summary["totalQuantity"] = total_quantity
    entry_summary["actualResponseQuantity"] = float(actual_response_qty)
    req_qty_val = (
        payload.employeeRequestQuantity if payload.employeeRequestQuantity is not None
        else (payload.employee_request_quantity if payload.employee_request_quantity is not None
        else emp_data["summary"].get("employeeRequestQuantity", float(taking_count)))
    )
    entry_summary["employeeRequestQuantity"] = float(req_qty_val)

    if entry:
        if rec_type != "HISTORICAL":
            entry.employee_snapshot = emp_data["applicableEmployees"]
            entry.summary = entry_summary
        else:
            entry.employee_snapshot = []
            entry.summary = entry_summary
        entry.total_quantity = total_quantity
        entry.record_type = rec_type
        entry.paid_by = paid_by
        entry.payment_type = payment_type
        entry.source = src
        entry.source_id = src_id
        entry.breakfast_items = processed_bf
        entry.common_items = processed_cm
        entry.total_cost = total_cost
        entry.updated_by = current_user.name
    else:
        entry = BreakfastDailyEntry(
            business_date=b_date,
            employee_snapshot=[] if rec_type == "HISTORICAL" else emp_data["applicableEmployees"],
            summary=entry_summary,
            breakfast_items=processed_bf,
            common_items=processed_cm,
            total_cost=total_cost,
            total_quantity=total_quantity,
            record_type=rec_type,
            paid_by=paid_by,
            payment_type=payment_type,
            source=src,
            source_id=src_id,
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
            "recordType": rec_type,
            "totalCost": total_cost,
            "details": f"Daily entry ({rec_type}) for {b_date} saved with total cost ₹{total_cost:,.2f}"
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
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.view", "breakfast.orders.view"])),
    db: Session = Depends(get_db)
):
    target_date = date or get_authoritative_breakfast_date(db)
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

    raw_hc = payload.headCount if payload.headCount is not None else payload.head_count
    head_count = None
    if raw_hc is not None:
        try:
            head_count = int(raw_hc)
            if head_count <= 0:
                raise ValidationError("Head count must be a positive number greater than 0")
        except (ValueError, TypeError):
            raise ValidationError("Head count must be a valid positive number")

    calc_count = float(head_count) if head_count is not None else float(applicable_count)

    processed_bf = []
    items_total = 0.0
    for item in payload.breakfastItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty = float(item.quantity) if item.quantity is not None else calc_count
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
        client_name=payload.clientName.strip() if payload.clientName else None,
        head_count=head_count,
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

    raw_hc = payload.headCount if payload.headCount is not None else payload.head_count
    head_count = order.head_count
    if raw_hc is not None:
        try:
            head_count = int(raw_hc)
            if head_count <= 0:
                raise ValidationError("Head count must be a positive number greater than 0")
        except (ValueError, TypeError):
            raise ValidationError("Head count must be a valid positive number")

    calc_count = float(head_count) if head_count is not None else float(applicable_count)

    processed_bf = []
    items_total = 0.0
    for item in payload.breakfastItems or []:
        if item and item.name and item.name.strip():
            price = float(item.unitPrice or 0)
            qty = float(item.quantity) if item.quantity is not None else calc_count
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
    order.head_count = head_count
    if payload.clientName is not None:
        order.client_name = payload.clientName.strip() if payload.clientName else None
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

# 14. All Orders (Unified list of Daily Entries + Additional Orders + Historical Entries)
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
    sortOrder: str = Query("asc"),
    current_user: CurrentUser = Depends(require_permission("breakfast.orders.view")),
    db: Session = Depends(get_db)
):
    daily_q = db.query(BreakfastDailyEntry)
    add_q = db.query(BreakfastAdditionalOrder)
    hist_q = db.query(BreakfastRecord).filter(BreakfastRecord.record_type == "HISTORICAL")

    if startDate and endDate:
        daily_q = daily_q.filter(BreakfastDailyEntry.business_date >= startDate, BreakfastDailyEntry.business_date <= endDate)
        add_q = add_q.filter(BreakfastAdditionalOrder.business_date >= startDate, BreakfastAdditionalOrder.business_date <= endDate)
        hist_q = hist_q.filter(BreakfastRecord.business_date >= startDate, BreakfastRecord.business_date <= endDate)
    elif startDate:
        daily_q = daily_q.filter(BreakfastDailyEntry.business_date >= startDate)
        add_q = add_q.filter(BreakfastAdditionalOrder.business_date >= startDate)
        hist_q = hist_q.filter(BreakfastRecord.business_date >= startDate)
    elif endDate:
        daily_q = daily_q.filter(BreakfastDailyEntry.business_date <= endDate)
        add_q = add_q.filter(BreakfastAdditionalOrder.business_date <= endDate)
        hist_q = hist_q.filter(BreakfastRecord.business_date <= endDate)

    daily_entries = []
    if type in ["ALL", "DAILY_ENTRY", "DAILY_BREAKFAST"]:
        daily_entries = daily_q.all()

    additional_orders = []
    if type in ["ALL", "ADDITIONAL_ORDER"]:
        additional_orders = add_q.all()

    historical_records = []
    if type in ["ALL", "HISTORICAL", "HISTORICAL_RECORD", "HISTORICAL_BREAKFAST"]:
        historical_records = hist_q.all()

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
            "recordType": getattr(entry, "record_type", "CURRENT"),
            "isHistorical": getattr(entry, "record_type", "CURRENT") == "HISTORICAL",
            "employeeId": None if getattr(entry, "record_type", "CURRENT") == "HISTORICAL" else None,
            "employeeName": "Not Recorded" if getattr(entry, "record_type", "CURRENT") == "HISTORICAL" else None,
            "applicableEmployeeCount": (entry.summary or {}).get("applicableCount", len(entry.employee_snapshot or [])),
            "systemEmployeeCount": (entry.summary or {}).get("applicableCount", len(entry.employee_snapshot or [])),
            "takingEmployeeCount": (entry.summary or {}).get("takingCount", 0),
            "notTakingEmployeeCount": (entry.summary or {}).get("notTakingCount", 0),
            "noResponseEmployeeCount": (entry.summary or {}).get("noResponseCount", 0),
            "employeeRequestQuantity": (entry.summary or {}).get("employeeRequestQuantity", (entry.summary or {}).get("takingCount", 0)),
            "actualResponseQuantity": (entry.summary or {}).get("actualResponseQuantity", (entry.summary or {}).get("actualTakenCount", 0)),
            "totalQuantity": getattr(entry, "total_quantity", None) or (entry.summary or {}).get("totalQuantity", (entry.summary or {}).get("actualResponseQuantity", 0)),
            "employeeSnapshot": entry.employee_snapshot or [],
            "breakfastItems": entry.breakfast_items or [],
            "commonItems": entry.common_items or [],
            "totalCost": entry.total_cost or 0.0,
            "paidBy": getattr(entry, "paid_by", None),
            "paymentType": getattr(entry, "payment_type", None),
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
            "clientName": order.client_name,
            "headCount": order.head_count,
            "recordType": "CURRENT",
            "isHistorical": False,
            "applicableEmployeeCount": order.head_count if order.head_count is not None else (order.applicable_employee_count or len(order.applicable_employee_snapshot or [])),
            "systemEmployeeCount": order.applicable_employee_count or len(order.applicable_employee_snapshot or []),
            "takingEmployeeCount": order.head_count if order.head_count is not None else (order.applicable_employee_count or 0),
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

    mapped_hist = []
    for hr in historical_records:
        items = []
        if hr.snack:
            items.append({
                "name": hr.snack,
                "quantity": hr.snack_quantity or "1",
                "unitPrice": hr.snack_cost or 0.0,
                "total": hr.snack_cost or 0.0
            })
        if hr.fruit:
            items.append({
                "name": hr.fruit,
                "quantity": hr.fruit_quantity or "1",
                "unitPrice": hr.fruit_cost or 0.0,
                "total": hr.fruit_cost or 0.0
            })

        order_id = hr.source_id or hr.record_id
        mapped_hist.append({
            "_id": hr.id,
            "orderId": order_id,
            "rawId": str(hr.id),
            "recordId": hr.record_id,
            "businessDate": hr.business_date,
            "orderType": "HISTORICAL",
            "orderTypeLabel": "HISTORICAL BREAKFAST",
            "orderTitle": f"Historical Breakfast ({hr.business_date})",
            "orderTime": "12:00",
            "recordType": "HISTORICAL",
            "isHistorical": True,
            "employeeId": None,
            "employeeName": "Not Recorded",
            "applicableEmployeeCount": 0,
            "takingEmployeeCount": 0,
            "notTakingEmployeeCount": 0,
            "noResponseEmployeeCount": 0,
            "employeeSnapshot": [],
            "breakfastItems": items,
            "commonItems": [],
            "snack": hr.snack,
            "snackQuantity": hr.snack_quantity,
            "snackCost": hr.snack_cost or 0.0,
            "fruit": hr.fruit,
            "fruitQuantity": hr.fruit_quantity,
            "fruitCost": hr.fruit_cost or 0.0,
            "totalCost": hr.total_cost or 0.0,
            "paidBy": hr.paid_by,
            "paymentType": hr.payment_type,
            "source": hr.source,
            "sourceId": hr.source_id,
            "externalReference": hr.external_reference,
            "createdBy": hr.paid_by or "Historical Import",
            "updatedBy": None,
            "createdAt": hr.created_at.isoformat() if hr.created_at else hr.business_date,
            "updatedAt": hr.updated_at.isoformat() if hr.updated_at else None,
            "status": "COMPLETED",
            "financialReference": {
                "referenceType": "HISTORICAL_RECORD",
                "referenceId": hr.record_id
            }
        })

    combined = mapped_daily + mapped_add + mapped_hist

    if search and search.strip():
        s = search.strip().lower()
        combined = [
            o for o in combined
            if s in o["orderId"].lower()
            or s in o["orderTitle"].lower()
            or s in o["businessDate"].lower()
            or s in (o.get("createdBy") or "").lower()
            or s in (o.get("paidBy") or "").lower()
            or s in (o.get("paymentType") or "").lower()
            or s in (o.get("snack") or "").lower()
            or s in (o.get("fruit") or "").lower()
            or any(item.get("name") and s in item["name"].lower() for item in o.get("breakfastItems", []))
            or any(item.get("name") and s in item["name"].lower() for item in o.get("commonItems", []))
        ]

    if createdBy and createdBy != "ALL":
        c = createdBy.strip().lower()
        combined = [o for o in combined if c in (o.get("createdBy") or "").lower() or c in (o.get("paidBy") or "").lower()]

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
    hist_count = sum(1 for o in combined if o["orderType"] == "HISTORICAL")

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
            "grandTotal": tot_amt,
            "dailyCount": daily_count,
            "additionalCount": add_count,
            "historicalCount": hist_count
        },
        "pagination": {
            "total": tot_count,
            "page": page_num,
            "limit": limit_num,
            "totalPages": tot_pages
        },
        "orders": paginated
    }

# 15. Breakfast Records GET (List)
@router.get("/records")
def get_breakfast_records(
    date: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    recordType: Optional[str] = Query("ALL"),
    employeeId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1),
    limit: str = Query("50"),
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.view", "breakfast.orders.view"])),
    db: Session = Depends(get_db)
):
    q = db.query(BreakfastRecord)
    if date:
        q = q.filter(BreakfastRecord.business_date == date)
    if startDate and endDate:
        q = q.filter(BreakfastRecord.business_date >= startDate, BreakfastRecord.business_date <= endDate)
    elif startDate:
        q = q.filter(BreakfastRecord.business_date >= startDate)
    elif endDate:
        q = q.filter(BreakfastRecord.business_date <= endDate)

    if recordType and recordType.upper() != "ALL":
        q = q.filter(BreakfastRecord.record_type == recordType.upper())

    if employeeId:
        q = q.filter(BreakfastRecord.employee_id == employeeId.upper())

    records = q.order_by(BreakfastRecord.business_date.desc(), BreakfastRecord.created_at.desc()).all()

    if search and search.strip():
        s = search.strip().lower()
        records = [
            r for r in records
            if (r.employee_name and s in r.employee_name.lower())
            or (r.employee_id and s in r.employee_id.lower())
            or (r.snack and s in r.snack.lower())
            or (r.fruit and s in r.fruit.lower())
            or (r.paid_by and s in r.paid_by.lower())
            or (r.source_id and s in r.source_id.lower())
            or (r.business_date and s in r.business_date.lower())
        ]

    tot_count = len(records)
    page_num = max(1, int(page))
    limit_num = tot_count if limit == "ALL" else max(1, int(limit))
    tot_pages = math.ceil(tot_count / limit_num) if limit_num > 0 else 1
    start_idx = (page_num - 1) * limit_num
    paginated = records[start_idx: start_idx + limit_num]

    return {
        "success": True,
        "total": tot_count,
        "page": page_num,
        "limit": limit_num,
        "totalPages": tot_pages,
        "records": [serialize_record(r) for r in paginated]
    }

# 16. Breakfast Record GET by ID
@router.get("/records/{id}")
def get_breakfast_record_by_id(
    id: str,
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.view", "breakfast.orders.view"])),
    db: Session = Depends(get_db)
):
    rec = db.query(BreakfastRecord).filter(
        (BreakfastRecord.id == id) | (BreakfastRecord.record_id == id) | (BreakfastRecord.source_id == id)
    ).first()
    if not rec:
        raise NotFoundError("Breakfast record not found")
    return {
        "success": True,
        "record": serialize_record(rec)
    }

# 17. Breakfast Record POST (Create single record)
@router.post("/records", status_code=201)
def create_breakfast_record(
    payload: CreateBreakfastRecordRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    b_date = payload.businessDate or payload.date
    if not b_date or not b_date.strip():
        raise ValidationError("businessDate (or date) is required")
    b_date = b_date.strip()

    rec_type = (payload.recordType or payload.record_type or "CURRENT").upper()
    if rec_type not in ["CURRENT", "HISTORICAL"]:
        raise ValidationError("recordType must be CURRENT or HISTORICAL")

    emp_id = payload.employeeId or payload.employee_id
    if emp_id:
        emp_id = emp_id.strip()

    # Rule: CURRENT requires employee; HISTORICAL employee is null/optional
    if rec_type == "CURRENT":
        if not emp_id:
            raise ValidationError("employeeId is required for CURRENT breakfast records")
    else:
        # HISTORICAL: employee stays None unless explicitly linked
        emp_id = None

    src_id = payload.sourceId or payload.source_id
    # Idempotency / duplicate check if source_id provided
    if src_id:
        existing = db.query(BreakfastRecord).filter(BreakfastRecord.source_id == src_id).first()
        if existing:
            return {
                "success": True,
                "skipped": True,
                "message": f"Historical record with sourceId '{src_id}' already exists",
                "record": serialize_record(existing)
            }

    s_qty = str(payload.snackQuantity or payload.snack_quantity or "") if (payload.snackQuantity or payload.snack_quantity) is not None else None
    f_qty = str(payload.fruitQuantity or payload.fruit_quantity or "") if (payload.fruitQuantity or payload.fruit_quantity) is not None else None
    s_cost = float(payload.snackCost if payload.snackCost is not None else (payload.snack_cost or 0.0))
    f_cost = float(payload.fruitCost if payload.fruitCost is not None else (payload.fruit_cost or 0.0))
    t_cost = payload.totalCost if payload.totalCost is not None else payload.total_cost
    if t_cost is None:
        t_cost = s_cost + f_cost
    else:
        t_cost = float(t_cost)

    paid_by = payload.paidBy or payload.paid_by
    payment_type = payload.paymentType or payload.payment_type
    src = payload.source or ("HISTORICAL_IMPORT" if rec_type == "HISTORICAL" else "EMPLOYEE")
    ext_ref = payload.externalReference or payload.external_reference
    record_id = src_id or f"{'HIST' if rec_type == 'HISTORICAL' else 'BRK'}-{b_date.replace('-', '')}-{uuid.uuid4().hex[:8]}"

    rec = BreakfastRecord(
        record_id=record_id,
        employee_id=emp_id,
        employee_name=None if rec_type == "HISTORICAL" else (payload.employeeName or payload.employee_name),
        business_date=b_date,
        record_type=rec_type,
        snack=payload.snack,
        snack_quantity=s_qty,
        snack_cost=s_cost,
        fruit=payload.fruit,
        fruit_quantity=f_qty,
        fruit_cost=f_cost,
        total_cost=t_cost,
        paid_by=paid_by,
        payment_type=payment_type,
        source=src,
        source_id=src_id,
        external_reference=ext_ref,
        response=payload.response or ("HISTORICAL" if rec_type == "HISTORICAL" else "TAKING"),
        employee_response=payload.employeeResponse or ("HISTORICAL" if rec_type == "HISTORICAL" else "TAKING"),
        actual_status=payload.actualStatus or ("HISTORICAL" if rec_type == "HISTORICAL" else None),
        actual_status_source="HISTORICAL_IMPORT" if rec_type == "HISTORICAL" else "EMPLOYEE_RESPONSE",
        reason_code=payload.reasonCode,
        reason_text=payload.reasonText,
        submitted_at=datetime.now(timezone.utc),
        history=[]
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    serialized = serialize_record(rec)

    audit_service = AuditService(db)
    audit_service.log(
        action="HISTORICAL_BREAKFAST_IMPORT" if rec_type == "HISTORICAL" else "BREAKFAST_RECORD_CREATED",
        request=request,
        target_info={
            "recordId": rec.record_id,
            "businessDate": b_date,
            "recordType": rec_type,
            "sourceId": src_id,
            "totalCost": t_cost,
            "details": f"Created {'historical' if rec_type == 'HISTORICAL' else 'current'} breakfast record for {b_date}"
        },
        after_state=serialized
    )

    return {
        "success": True,
        "message": f"{'Historical' if rec_type == 'HISTORICAL' else 'Current'} record saved successfully",
        "record": serialized
    }

# 18. Breakfast Records Batch Insert (Seed / Import endpoint)
@router.post("/records/batch")
def batch_create_breakfast_records(
    records: Union[List[CreateBreakfastRecordRequest], BatchRecordsRequest],
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    items = records.records if isinstance(records, BatchRecordsRequest) else records
    inserted = 0
    skipped = 0
    errors = 0
    processed_records = []
    error_details = []

    for idx, item in enumerate(items):
        try:
            b_date = item.businessDate or item.date
            if not b_date or not b_date.strip():
                errors += 1
                error_details.append(f"Row {idx+1}: Missing date")
                continue
            b_date = b_date.strip()

            rec_type = (item.recordType or item.record_type or "HISTORICAL").upper()
            src_id = item.sourceId or item.source_id

            if src_id:
                existing = db.query(BreakfastRecord).filter(BreakfastRecord.source_id == src_id).first()
                if existing:
                    skipped += 1
                    processed_records.append(serialize_record(existing))
                    continue

            emp_id = None if rec_type == "HISTORICAL" else (item.employeeId or item.employee_id)
            s_qty = str(item.snackQuantity or item.snack_quantity or "") if (item.snackQuantity or item.snack_quantity) is not None else None
            f_qty = str(item.fruitQuantity or item.fruit_quantity or "") if (item.fruitQuantity or item.fruit_quantity) is not None else None
            s_cost = float(item.snackCost if item.snackCost is not None else (item.snack_cost or 0.0))
            f_cost = float(item.fruitCost if item.fruitCost is not None else (item.fruit_cost or 0.0))
            t_cost = item.totalCost if item.totalCost is not None else item.total_cost
            if t_cost is None:
                t_cost = s_cost + f_cost
            else:
                t_cost = float(t_cost)

            record_id = src_id or f"{'HIST' if rec_type == 'HISTORICAL' else 'BRK'}-{b_date.replace('-', '')}-{uuid.uuid4().hex[:8]}"

            rec = BreakfastRecord(
                record_id=record_id,
                employee_id=emp_id,
                employee_name=None if rec_type == "HISTORICAL" else (item.employeeName or item.employee_name),
                business_date=b_date,
                record_type=rec_type,
                snack=item.snack,
                snack_quantity=s_qty,
                snack_cost=s_cost,
                fruit=item.fruit,
                fruit_quantity=f_qty,
                fruit_cost=f_cost,
                total_cost=t_cost,
                paid_by=item.paidBy or item.paid_by,
                payment_type=item.paymentType or item.payment_type,
                source=item.source or ("HISTORICAL_IMPORT" if rec_type == "HISTORICAL" else "EMPLOYEE"),
                source_id=src_id,
                external_reference=item.externalReference or item.external_reference,
                response=item.response or ("HISTORICAL" if rec_type == "HISTORICAL" else "TAKING"),
                employee_response=item.employeeResponse or ("HISTORICAL" if rec_type == "HISTORICAL" else "TAKING"),
                actual_status=item.actualStatus or ("HISTORICAL" if rec_type == "HISTORICAL" else None),
                actual_status_source="HISTORICAL_IMPORT" if rec_type == "HISTORICAL" else "EMPLOYEE_RESPONSE",
                reason_code=item.reasonCode,
                reason_text=item.reasonText,
                submitted_at=datetime.now(timezone.utc),
                history=[]
            )
            db.add(rec)
            inserted += 1
            processed_records.append(serialize_record(rec))
        except Exception as e:
            errors += 1
            error_details.append(f"Row {idx+1}: {str(e)}")

    db.commit()

    audit_service = AuditService(db)
    audit_service.log(
        action="HISTORICAL_BREAKFAST_IMPORT",
        request=request,
        target_info={
            "totalRows": len(items),
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors,
            "details": f"Batch imported {inserted} records, skipped {skipped} duplicates, errors: {errors}"
        }
    )

    return {
        "success": True,
        "summary": {
            "total": len(items),
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors,
            "errorDetails": error_details
        },
        "records": processed_records
    }

# 19. Breakfast Record PUT (Update)
@router.put("/records/{id}")
def update_breakfast_record(
    id: str,
    payload: UpdateBreakfastRecordRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    rec = db.query(BreakfastRecord).filter(
        (BreakfastRecord.id == id) | (BreakfastRecord.record_id == id) | (BreakfastRecord.source_id == id)
    ).first()
    if not rec:
        raise NotFoundError("Breakfast record not found")

    before_state = serialize_record(rec)
    is_historical = (rec.record_type or "CURRENT") == "HISTORICAL"

    # Business Date
    if payload.businessDate or payload.date:
        rec.business_date = (payload.businessDate or payload.date).strip()

    # Editable historical/item fields
    if payload.snack is not None:
        rec.snack = payload.snack
    if payload.snackQuantity is not None or payload.snack_quantity is not None:
        rec.snack_quantity = str(payload.snackQuantity if payload.snackQuantity is not None else payload.snack_quantity)
    if payload.snackCost is not None or payload.snack_cost is not None:
        rec.snack_cost = float(payload.snackCost if payload.snackCost is not None else payload.snack_cost)

    if payload.fruit is not None:
        rec.fruit = payload.fruit
    if payload.fruitQuantity is not None or payload.fruit_quantity is not None:
        rec.fruit_quantity = str(payload.fruitQuantity if payload.fruitQuantity is not None else payload.fruit_quantity)
    if payload.fruitCost is not None or payload.fruit_cost is not None:
        rec.fruit_cost = float(payload.fruitCost if payload.fruitCost is not None else payload.fruit_cost)

    if payload.totalCost is not None or payload.total_cost is not None:
        rec.total_cost = float(payload.totalCost if payload.totalCost is not None else payload.total_cost)
    elif payload.snackCost is not None or payload.snack_cost is not None or payload.fruitCost is not None or payload.fruit_cost is not None:
        rec.total_cost = (rec.snack_cost or 0.0) + (rec.fruit_cost or 0.0)

    if payload.paidBy is not None or payload.paid_by is not None:
        rec.paid_by = payload.paidBy if payload.paidBy is not None else payload.paid_by
    if payload.paymentType is not None or payload.payment_type is not None:
        rec.payment_type = payload.paymentType if payload.paymentType is not None else payload.payment_type

    if not is_historical:
        if payload.response is not None:
            rec.response = payload.response
        if payload.actualStatus is not None:
            rec.actual_status = payload.actualStatus
        if payload.reasonCode is not None:
            rec.reason_code = payload.reasonCode
        if payload.reasonText is not None:
            rec.reason_text = payload.reasonText
    else:
        # Crucial Requirement: Do NOT allow setting employee for historical records!
        rec.employee_id = None
        rec.employee_name = None

    db.commit()
    db.refresh(rec)

    after_state = serialize_record(rec)

    audit_service = AuditService(db)
    audit_service.log(
        action="HISTORICAL_RECORD_UPDATED" if is_historical else "BREAKFAST_RECORD_UPDATED",
        request=request,
        target_info={
            "recordId": rec.record_id,
            "businessDate": rec.business_date,
            "recordType": rec.record_type,
            "details": f"Updated {'historical' if is_historical else 'current'} breakfast record ({rec.record_id})"
        },
        before_state=before_state,
        after_state=after_state
    )

    return {
        "success": True,
        "message": f"{'Historical' if is_historical else 'Current'} record updated successfully",
        "record": after_state
    }

# 20. Breakfast Record DELETE
@router.delete("/records/{id}")
def delete_breakfast_record(
    id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    rec = db.query(BreakfastRecord).filter(
        (BreakfastRecord.id == id) | (BreakfastRecord.record_id == id) | (BreakfastRecord.source_id == id)
    ).first()
    if not rec:
        raise NotFoundError("Breakfast record not found")

    before_state = serialize_record(rec)
    rec_type = rec.record_type or "CURRENT"
    rec_id = rec.record_id

    db.delete(rec)
    db.commit()

    audit_service = AuditService(db)
    audit_service.log(
        action="HISTORICAL_RECORD_DELETED" if rec_type == "HISTORICAL" else "BREAKFAST_RECORD_DELETED",
        request=request,
        target_info={
            "recordId": rec_id,
            "recordType": rec_type,
            "details": f"Deleted {'historical' if rec_type == 'HISTORICAL' else 'current'} record ({rec_id})"
        },
        before_state=before_state
    )

    return {
        "success": True,
        "message": f"{'Historical' if rec_type == 'HISTORICAL' else 'Current'} record deleted successfully"
    }
