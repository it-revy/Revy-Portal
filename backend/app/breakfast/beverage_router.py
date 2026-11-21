from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    require_permission,
    require_any_permission,
    require_module_access,
    CurrentUser
)
from app.breakfast.beverage_service import BeverageService
from app.breakfast.beverage_schema import (
    BeverageCreateRequest,
    BeverageUpdateRequest,
    BeverageStatusUpdateRequest,
    BeverageItemResponse,
    BeverageEntrySubmitRequest,
    BeverageAdminEntryCreateRequest,
    BeverageAdminEntryUpdateRequest,
    BeverageAdminEntryDeleteRequest,
    BeverageEntryResponse
)

router = APIRouter(
    prefix="/breakfast/beverages",
    tags=["BMS Beverages"],
    dependencies=[Depends(require_module_access("BMS"))]
)


# =============================================================================
# 1. CATALOGUE ENDPOINTS
# =============================================================================

@router.get(
    "/catalogue",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_any_permission(["bms.beverages.view", "bms.beverages.submit", "bms.beverages.manage"]))]
)
def get_beverage_catalogue(
    active_only: bool = Query(False, description="Whether to filter active beverages only"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    # If user lacks bms.beverages.manage, strictly return active beverages only
    has_manage = (
        current_user.is_global_admin or
        "*" in (current_user.all_permissions or []) or
        "bms.beverages.manage" in (current_user.permissions or []) or
        "bms.beverages.manage" in (current_user.all_permissions or [])
    )
    should_filter_active = active_only or not has_manage
    items = service.get_catalogue(active_only=should_filter_active)
    return {
        "success": True,
        "total": len(items),
        "beverages": [i.model_dump() for i in items]
    }


@router.post(
    "/catalogue",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("bms.beverages.manage"))]
)
def create_catalogue_beverage(
    payload: BeverageCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    created = service.create_beverage(actor=current_user, payload=payload)
    return {
        "success": True,
        "message": f"Beverage '{created.name}' created successfully.",
        "beverage": created.model_dump()
    }


@router.put(
    "/catalogue/{beverage_id}",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission("bms.beverages.manage"))]
)
def update_catalogue_beverage(
    beverage_id: str,
    payload: BeverageUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    updated = service.update_beverage(actor=current_user, beverage_id=beverage_id, payload=payload)
    return {
        "success": True,
        "message": f"Beverage '{updated.name}' updated successfully.",
        "beverage": updated.model_dump()
    }


@router.patch(
    "/catalogue/{beverage_id}/status",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission("bms.beverages.manage"))]
)
def toggle_catalogue_beverage_status(
    beverage_id: str,
    payload: BeverageStatusUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    updated = service.toggle_beverage_status(actor=current_user, beverage_id=beverage_id, is_active=payload.isActive)
    return {
        "success": True,
        "message": f"Beverage '{updated.name}' status set to {'ACTIVE' if updated.isActive else 'INACTIVE'}.",
        "beverage": updated.model_dump()
    }


# =============================================================================
# 2. EMPLOYEE CONSUMPTION ENDPOINTS
# =============================================================================

@router.post(
    "/entries",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("bms.beverages.submit"))]
)
def submit_employee_beverage_entry(
    payload: BeverageEntrySubmitRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    entry = service.submit_employee_entry(actor=current_user, payload=payload)
    return {
        "success": True,
        "message": f"Beverage entry for {entry.session} recorded successfully ({entry.quantity} {entry.unit} of {entry.beverageNameSnapshot}).",
        "entry": entry.model_dump()
    }


@router.get(
    "/my-entries",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission("bms.beverages.view"))]
)
def get_my_beverage_entries(
    fromDate: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    toDate: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    entries = service.get_my_entries(actor=current_user, from_date=fromDate, to_date=toDate)
    return {
        "success": True,
        "total": len(entries),
        "entries": [e.model_dump() for e in entries]
    }


@router.get(
    "/today-summary",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission("bms.beverages.view"))]
)
def get_today_beverage_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    summary = service.get_employee_today_status(actor=current_user)
    return {
        "success": True,
        **summary
    }


# =============================================================================
# 3. ADMIN CONSUMPTION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get(
    "/admin/entries",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission("bms.beverages.manage"))]
)
def admin_get_beverage_entries(
    date: Optional[str] = Query(None, description="Single target date YYYY-MM-DD"),
    fromDate: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    toDate: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    employeeId: Optional[str] = Query(None, description="Filter by employee code"),
    beverageId: Optional[str] = Query(None, description="Filter by beverage id"),
    session: Optional[str] = Query(None, description="Filter by MORNING or EVENING"),
    includeDeleted: bool = Query(False, description="Include soft-deleted records"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    result = service.admin_get_entries(
        from_date=fromDate,
        to_date=toDate,
        date=date,
        employee_id=employeeId,
        beverage_id=beverageId,
        session=session,
        include_deleted=includeDeleted,
        limit=limit,
        offset=offset
    )
    return {
        "success": True,
        **result
    }


@router.post(
    "/admin/entries",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("bms.beverages.manage"))]
)
def admin_create_beverage_entry(
    payload: BeverageAdminEntryCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    entry = service.admin_create_entry(actor=current_user, payload=payload)
    return {
        "success": True,
        "message": f"Recorded beverage entry for {entry.employeeNameSnapshot} on {entry.businessDate} ({entry.session}).",
        "entry": entry.model_dump()
    }


@router.put(
    "/admin/entries/{entry_id}",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission("bms.beverages.manage"))]
)
def admin_update_beverage_entry(
    entry_id: str,
    payload: BeverageAdminEntryUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    updated = service.admin_update_entry(actor=current_user, entry_id=entry_id, payload=payload)
    return {
        "success": True,
        "message": "Beverage record updated successfully.",
        "entry": updated.model_dump()
    }


@router.delete(
    "/admin/entries/{entry_id}",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission("bms.beverages.manage"))]
)
def admin_delete_beverage_entry(
    entry_id: str,
    payload: Optional[BeverageAdminEntryDeleteRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BeverageService(db)
    reason = payload.reason if payload else None
    deleted = service.admin_delete_entry(actor=current_user, entry_id=entry_id, reason=reason)
    return {
        "success": True,
        "message": f"Beverage entry for {deleted.employeeNameSnapshot} soft-deleted successfully.",
        "entry": deleted.model_dump()
    }
