from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_any_permission, CurrentUser
from app.employees.schema import (
    AddUserToBmsRequest,
    AvailableUserResponse
)
from app.employees.service import EmployeeService

router = APIRouter(prefix="/bms", tags=["BMS Memberships"])

@router.get("/users/available", response_model=List[AvailableUserResponse])
def get_available_bms_users(
    search: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.employee.create", "breakfast.employee.read", "users.view", "*"])),
    db: Session = Depends(get_db)
):
    """
    Returns central users eligible to be added to BMS.
    """
    service = EmployeeService(db)
    return service.list_available_users_for_bms(search=search)

@router.post("/memberships")
def create_bms_membership(
    payload: AddUserToBmsRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.employee.create", "users.edit", "*"])),
    db: Session = Depends(get_db)
):
    """
    Adds an existing central User to BMS.
    Does NOT accept username/password.
    """
    service = EmployeeService(db)
    created = service.add_user_to_bms(payload.model_dump(), request=request)
    return {
        "success": True,
        "message": f"User {created.get('name') or created.get('username')} successfully added to BMS.",
        "membership": created
    }

@router.delete("/memberships/{membership_id}")
def remove_bms_membership(
    membership_id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.employee.deactivate", "users.edit", "*"])),
    db: Session = Depends(get_db)
):
    """
    Removes user from BMS without deleting the central User.
    """
    service = EmployeeService(db)
    deactivated = service.deactivate_employee(membership_id, request=request)
    return {
        "success": True,
        "message": f"User {deactivated['name']} removed from BMS. Central user account and historical breakfast records preserved.",
        "membership": deactivated
    }
