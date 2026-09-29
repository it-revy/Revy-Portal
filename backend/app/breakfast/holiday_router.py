from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, CurrentUser
from app.core.exceptions import ValidationError, NotFoundError
from app.breakfast.model import PublicHoliday
from app.audit.service import AuditService

router = APIRouter(prefix="/holidays", tags=["Public Holidays"])

class CreateHolidayRequest(BaseModel):
    date: str
    name: str

def serialize_holiday(h: PublicHoliday):
    return {
        "_id": h.id,
        "id": h.id,
        "holidayId": h.holiday_id,
        "date": h.date,
        "name": h.name,
        "status": h.status,
        "createdBy": h.created_by,
        "createdAt": h.created_at.isoformat() if h.created_at else None
    }

@router.get("")
@router.get("/")
def get_holidays(
    current_user: CurrentUser = Depends(require_permission("breakfast.view")),
    db: Session = Depends(get_db)
):
    holidays = db.query(PublicHoliday).order_by(PublicHoliday.date.asc()).all()
    return {
        "success": True,
        "holidays": [serialize_holiday(h) for h in holidays]
    }

@router.post("")
@router.post("/")
def create_holiday(
    payload: CreateHolidayRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.holiday.manage")),
    db: Session = Depends(get_db)
):
    date_str = payload.date.strip()
    name_str = payload.name.strip()
    if not date_str or not name_str:
        raise ValidationError("Date and holiday name are required")

    existing = db.query(PublicHoliday).filter(PublicHoliday.date == date_str).first()
    if existing:
        raise ValidationError(f"Public holiday on {date_str} already exists ({existing.name})")

    holiday_id = f"HOL-{date_str.replace('-', '')}"
    holiday = PublicHoliday(
        holiday_id=holiday_id,
        date=date_str,
        name=name_str,
        status="active",
        created_by=current_user.name
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)

    serialized = serialize_holiday(holiday)

    audit_service = AuditService(db)
    audit_service.log(
        action="PUBLIC_HOLIDAY_CREATED",
        request=request,
        target_info={"target": holiday_id, "details": f"Created public holiday {name_str} on {date_str}"},
        after_state=serialized
    )

    return {
        "success": True,
        "message": "Public holiday created successfully",
        "holiday": serialized
    }

@router.delete("/{id}")
def delete_holiday(
    id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.holiday.manage")),
    db: Session = Depends(get_db)
):
    holiday = db.query(PublicHoliday).filter(
        (PublicHoliday.holiday_id == id) | (PublicHoliday.id == id)
    ).first()
    if not holiday:
        raise NotFoundError("Holiday not found")

    before_state = serialize_holiday(holiday)
    db.delete(holiday)
    db.commit()

    audit_service = AuditService(db)
    audit_service.log(
        action="PUBLIC_HOLIDAY_DELETED",
        request=request,
        target_info={"details": f"Deleted public holiday {holiday.name} ({holiday.date})"},
        before_state=before_state
    )

    return {
        "success": True,
        "message": "Public holiday deleted successfully"
    }
