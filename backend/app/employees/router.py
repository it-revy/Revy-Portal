from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, require_role, CurrentUser
from app.employees.schema import (
    CreateEmployeeRequest,
    UpdateEmployeeRequest,
    ResetPasswordRequest,
    HardDeleteRequest
)
from app.employees.service import EmployeeService
from app.breakfast.model import BreakfastRecord

router = APIRouter(prefix="/employees", tags=["Employees"])

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
    created = service.create_employee(payload.model_dump(), request=request)
    return {
        "success": True,
        "message": "Employee created successfully",
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
            "submittedAt": r.submitted_at.isoformat() if r.submitted_at else None
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
    updated = service.update_employee(id, payload.model_dump(exclude_unset=True), request=request)
    return {
        "success": True,
        "message": "Employee updated successfully",
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
        "message": f"Employee {deactivated['employeeId']} deactivated successfully. Historical records preserved.",
        "employee": deactivated
    }

@router.post("/{id}/reset-password")
def reset_password(
    id: str,
    payload: ResetPasswordRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("user.password.reset")),
    db: Session = Depends(get_db)
):
    service = EmployeeService(db)
    service.reset_password(id, payload.newPassword, payload.confirmPassword, request=request)
    return {
        "success": True,
        "message": f"Password for user updated successfully"
    }

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
        "message": f"Employee {id} hard-deleted by IT_ADMIN."
    }
