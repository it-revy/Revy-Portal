from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, CurrentUser
from app.core.exceptions import ValidationError, NotFoundError
from app.breakfast.model import BreakfastSetting, BreakfastReason
from app.audit.service import AuditService

router = APIRouter(prefix="/settings", tags=["Breakfast Settings"])

class UpdateSettingsRequest(BaseModel):
    cutoffTime: Optional[str] = None
    timezone: Optional[str] = None
    autoLockEnabled: Optional[bool] = None

class AddReasonRequest(BaseModel):
    code: str
    label: str
    isCustomAllowed: Optional[bool] = False
    displayOrder: Optional[int] = 99

def serialize_setting(s: BreakfastSetting):
    return {
        "_id": s.id,
        "id": s.id,
        "cutoffTime": s.cutoff_time,
        "timezone": s.timezone,
        "autoLockEnabled": s.auto_lock_enabled,
        "breakfastFundLimit": s.breakfast_fund_limit,
        "createdAt": s.created_at.isoformat() if s.created_at else None,
        "updatedAt": s.updated_at.isoformat() if s.updated_at else None
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
        setting = BreakfastSetting(cutoff_time="12:00", timezone="Asia/Kolkata", auto_lock_enabled=True)
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
        setting = BreakfastSetting()
        db.add(setting)

    before_state = serialize_setting(setting)

    if payload.cutoffTime is not None:
        setting.cutoff_time = payload.cutoffTime
    if payload.timezone is not None:
        setting.timezone = payload.timezone
    if payload.autoLockEnabled is not None:
        setting.auto_lock_enabled = payload.autoLockEnabled

    db.commit()
    db.refresh(setting)

    after_state = serialize_setting(setting)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_SETTINGS_UPDATED",
        request=request,
        target_info={"details": f"Updated cutoff time to {setting.cutoff_time}"},
        before_state=before_state,
        after_state=after_state
    )

    return {
        "success": True,
        "message": "Settings updated successfully",
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
