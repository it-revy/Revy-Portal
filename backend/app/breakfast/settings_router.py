import re
from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, CurrentUser
from app.core.exceptions import ValidationError, NotFoundError
from app.breakfast.model import BreakfastSetting, BreakfastReason
from app.audit.service import AuditService
from app.breakfast.date_utils import serialize_utc_timestamp

router = APIRouter(prefix="/settings", tags=["Breakfast Settings"])

TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

def validate_time_str(time_str: str, field_name: str) -> str:
    s = time_str.strip()
    if not TIME_REGEX.match(s):
        raise ValidationError(f"Invalid {field_name} '{time_str}'. Expected 24-hour format HH:mm (00:00 to 23:59).")
    return s

class UpdateSettingsRequest(BaseModel):
    requestOpenTime: Optional[str] = None
    requestCloseTime: Optional[str] = None
    cutoffTime: Optional[str] = None
    timezone: Optional[str] = None
    autoLockEnabled: Optional[bool] = None

class AddReasonRequest(BaseModel):
    code: str
    label: str
    isCustomAllowed: Optional[bool] = False
    displayOrder: Optional[int] = 99

def serialize_setting(s: BreakfastSetting):
    open_time = s.request_open_time or "17:30"
    close_time = s.request_close_time or s.cutoff_time or "08:20"
    return {
        "_id": s.id,
        "id": s.id,
        "requestOpenTime": open_time,
        "requestCloseTime": close_time,
        "cutoffTime": close_time,
        "timezone": s.timezone or "Asia/Kolkata",
        "autoLockEnabled": s.auto_lock_enabled,
        "breakfastFundLimit": s.breakfast_fund_limit,
        "createdAt": serialize_utc_timestamp(s.created_at),
        "updatedAt": serialize_utc_timestamp(s.updated_at)
    }

def serialize_reason(r: BreakfastReason):
    return {
        "_id": r.id,
        "id": r.id,
        "code": r.code,
        "label": r.label,
        "isCustomAllowed": r.is_custom_allowed,
        "isActive": r.is_active,
        "displayOrder": r.display_order
    }

@router.get("")
@router.get("/")
def get_settings(
    current_user: CurrentUser = Depends(require_permission("breakfast.settings.manage")),
    db: Session = Depends(get_db)
):
    setting = db.query(BreakfastSetting).first()
    if not setting:
        setting = BreakfastSetting(
            request_open_time="17:30",
            request_close_time="08:20",
            cutoff_time="08:20",
            timezone="Asia/Kolkata",
            auto_lock_enabled=True
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)

    reasons = db.query(BreakfastReason).order_by(BreakfastReason.display_order.asc()).all()

    return {
        "success": True,
        "settings": serialize_setting(setting),
        "reasons": [serialize_reason(r) for r in reasons]
    }

@router.put("")
@router.put("/")
def update_settings(
    payload: UpdateSettingsRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.settings.manage")),
    db: Session = Depends(get_db)
):
    setting = db.query(BreakfastSetting).first()
    if not setting:
        setting = BreakfastSetting(
            request_open_time="17:30",
            request_close_time="08:20",
            cutoff_time="08:20",
            timezone="Asia/Kolkata",
            auto_lock_enabled=True
        )
        db.add(setting)

    before_state = serialize_setting(setting)

    # Determine proposed open and close times
    current_open = setting.request_open_time or "17:30"
    current_close = setting.request_close_time or setting.cutoff_time or "08:20"

    new_open = current_open
    if payload.requestOpenTime is not None:
        new_open = validate_time_str(payload.requestOpenTime, "requestOpenTime")

    new_close = current_close
    if payload.requestCloseTime is not None:
        new_close = validate_time_str(payload.requestCloseTime, "requestCloseTime")
    elif payload.cutoffTime is not None:
        new_close = validate_time_str(payload.cutoffTime, "cutoffTime")

    if new_open == new_close:
        raise ValidationError("Request opening time and closing time cannot be identical.")

    setting.request_open_time = new_open
    setting.request_close_time = new_close
    setting.cutoff_time = new_close

    if payload.timezone is not None:
        setting.timezone = payload.timezone.strip()
    if payload.autoLockEnabled is not None:
        setting.auto_lock_enabled = payload.autoLockEnabled

    db.commit()
    db.refresh(setting)

    after_state = serialize_setting(setting)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_SETTINGS_UPDATED",
        request=request,
        target_info={
            "details": f"Updated breakfast cycle: Opens at {setting.request_open_time}, Closes at {setting.request_close_time} IST"
        },
        before_state=before_state,
        after_state=after_state
    )

    return {
        "success": True,
        "message": "Breakfast settings updated successfully",
        "settings": after_state
    }

@router.post("/reasons")
def add_reason_type(
    payload: AddReasonRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.settings.manage")),
    db: Session = Depends(get_db)
):
    upper_code = payload.code.strip().upper()
    existing = db.query(BreakfastReason).filter(BreakfastReason.code == upper_code).first()
    if existing:
        raise ValidationError(f"Reason code {upper_code} already exists")

    reason = BreakfastReason(
        code=upper_code,
        label=payload.label.strip(),
        is_custom_allowed=bool(payload.isCustomAllowed),
        display_order=payload.displayOrder or 99
    )
    db.add(reason)
    db.commit()
    db.refresh(reason)

    serialized = serialize_reason(reason)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_REASON_ADDED",
        request=request,
        target_info={"details": f"Added new breakfast rejection reason: {reason.label}"},
        after_state=serialized
    )

    return {
        "success": True,
        "message": "Reason added successfully",
        "reason": serialized
    }
