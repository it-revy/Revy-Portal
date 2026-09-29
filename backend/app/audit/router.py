from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, CurrentUser
from app.audit.service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

@router.get("")
@router.get("/")
def get_audit_logs(
    action: Optional[str] = Query(None),
    employeeId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100),
    current_user: CurrentUser = Depends(require_permission("breakfast.audit.view")),
    db: Session = Depends(get_db)
):
    audit_service = AuditService(db)
    logs = audit_service.get_logs(action=action, employee_id=employeeId, search=search, limit=limit)

    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            "_id": log.id,
            "id": log.id,
            "auditId": log.audit_id,
            "application": log.application,
            "action": log.action,
            "performedBy": {
                "employeeId": log.performed_by_employee_id or "",
                "employeeName": log.performed_by_name or "",
                "roleUsed": log.role_used or ""
            },
            "target": {
                "recordId": log.target_record_id,
                "targetEmployeeId": log.target_employee_id,
                "targetEmployeeName": log.target_employee_name,
                "details": log.details
            },
            "beforeState": log.before_state,
            "afterState": log.after_state,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "createdAt": log.created_at.isoformat() if log.created_at else None
        })

    return {
        "success": True,
        "count": len(formatted_logs),
        "logs": formatted_logs
    }
