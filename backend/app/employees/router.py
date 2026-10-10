from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, require_any_permission, require_role, CurrentUser
from app.employees.schema import (
    CreateEmployeeRequest,
    AddUserToBmsRequest,
    AvailableUserResponse,
    UpdateEmployeeRequest,
    ResetPasswordRequest,
    HardDeleteRequest
)
from app.employees.service import EmployeeService
from app.breakfast.model import BreakfastRecord
from app.breakfast.date_utils import serialize_utc_timestamp

router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("/available-users", response_model=List[AvailableUserResponse])
def get_available_users_for_bms(
    search: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.employee.create", "breakfast.employee.read", "users.view", "*"])),
    db: Session = Depends(get_db)
):
    """
    Returns active Central Users who are not currently active members of BMS.
    Used by BMS Admin to select and assign existing users to the Breakfast Management System.
    """
    service = EmployeeService(db)
    return service.list_available_users_for_bms(search=search)

@router.get("/assignable-roles")
def get_bms_assignable_roles(
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.employee.create", "breakfast.employee.update", "breakfast.employee.read", "users.view", "*"])),
    db: Session = Depends(get_db)
):
    """
    Returns active BMS roles that the current acting user is authorized to assign.
    """
    from app.roles.assignment_service import RoleAssignmentService
    roles = RoleAssignmentService.get_assignable_roles_for_module(current_user, "BMS", db)
    return {"success": True, "roles": roles}

@router.post("/assign-user")
@router.post("/add-to-bms")
def assign_user_to_bms(
    payload: AddUserToBmsRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.employee.create", "users.edit", "*"])),
    db: Session = Depends(get_db)
):
    """
    Assigns an existing Central User to BMS.
    Does NOT create a new system user. Strictly prevents duplicate assignments.
    """
    service = EmployeeService(db)
    created = service.add_user_to_bms(payload.model_dump(), request=request, current_user=current_user)
    return {
        "success": True,
        "message": f"User {created.get('name') or created.get('username')} successfully added to BMS.",
        "employee": created
    }

@router.get("")
@router.get("/")
def get_employees(
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    participationType: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.employee.read")),
    db: Session = Depends(get_db)
):
    service = EmployeeService(db)
    employees = service.repo.list_employees(
        search=search,
        department=department,
        status=status,
        participation_type=participationType
    )
    serialized = [service.serialize_employee(e) for e in employees]
    return {
        "success": True,
        "count": len(serialized),
        "employees": serialized
    }

@router.post("")
@router.post("/")
def create_employee(
    payload: CreateEmployeeRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.employee.create")),
    db: Session = Depends(get_db)
):
    service = EmployeeService(db)
    created = service.create_employee(payload.model_dump(), request=request, current_user=current_user)
    return {
        "success": True,
        "message": "User added to BMS successfully",
        "employee": created
    }

@router.get("/{id}")
def get_employee_by_id(
    id: str,
    current_user: CurrentUser = Depends(require_permission("breakfast.employee.read")),
    db: Session = Depends(get_db)
):
    service = EmployeeService(db)
    emp = service.repo.get_by_employee_id(id)
    if not emp:
        return {"success": False, "message": "Employee not found"}

    recent_records = db.query(BreakfastRecord).filter(
        BreakfastRecord.employee_id == emp.employee_id
    ).order_by(BreakfastRecord.business_date.desc()).limit(30).all()

    formatted_records = [
        {
            "_id": r.id,
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
            "submittedAt": serialize_utc_timestamp(r.submitted_at)
        }
        for r in recent_records
    ]

    return {
        "success": True,
        "employee": service.serialize_employee(emp),
        "recentRecords": formatted_records
    }

@router.put("/{id}")
def update_employee(
    id: str,
    payload: UpdateEmployeeRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.employee.update")),
    db: Session = Depends(get_db)
):
    service = EmployeeService(db)
    updated = service.update_employee(id, payload.model_dump(exclude_unset=True), request=request, current_user=current_user)
    return {
        "success": True,
        "message": "BMS Employee updated successfully",
        "employee": updated
    }

@router.delete("/{id}")
def deactivate_employee(
    id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.employee.deactivate")),
    db: Session = Depends(get_db)
):
    service = EmployeeService(db)
    deactivated = service.deactivate_employee(id, request=request)
    return {
        "success": True,
        "message": f"User {deactivated['name']} ({deactivated['employeeId']}) removed from BMS. Historical records and central user account remain preserved.",
        "employee": deactivated
    }

@router.post("/{id}/reset-password")
def reset_password(
    id: str,
    payload: Optional[Dict[str, Any]] = None,
    request: Request = None,
    current_user: CurrentUser = Depends(require_permission("user.password.reset")),
    db: Session = Depends(get_db)
):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Password reset must be performed via Central User Management. BMS cannot manage or reset user passwords."
    )

@router.post("/{id}/hard-delete")
def hard_delete_employee(
    id: str,
    payload: HardDeleteRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("IT_ADMIN")),
    db: Session = Depends(get_db)
):
    service = EmployeeService(db)
    service.hard_delete_employee(id, payload.confirmCode, request=request)
    return {
        "success": True,
        "message": f"BMS membership for employee {id} hard-deleted by IT_ADMIN."
    }
