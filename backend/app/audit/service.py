from typing import Optional, Dict, Any, List
from fastapi import Request
from sqlalchemy.orm import Session
from app.audit.repository import AuditRepository
from app.audit.model import AuditLog

class AuditService:
    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(
        self,
        action: str,
        request: Optional[Request] = None,
        target_info: Optional[Dict[str, Any]] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        performed_by_employee_id: Optional[str] = None,
        performed_by_name: Optional[str] = None,
        role_used: Optional[str] = None
    ) -> AuditLog:
        ip_address = None
        if request:
            ip_address = request.client.host if request.client else None
            user = getattr(request.state, "current_user", None)
            if user:
                performed_by_employee_id = performed_by_employee_id or user.employee_id
                performed_by_name = performed_by_name or user.name
                role_used = role_used or user.active_role

        target = target_info or {}
        return self.repo.create(
            action=action,
            performed_by_employee_id=performed_by_employee_id,
            performed_by_name=performed_by_name,
            role_used=role_used,
            target_record_id=target.get("recordId") or target.get("target_record_id") or target.get("orderId") or target.get("requestId"),
            target_employee_id=target.get("targetEmployeeId") or target.get("target_employee_id"),
            target_employee_name=target.get("targetEmployeeName") or target.get("target_employee_name"),
            details=target.get("details"),
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address
        )

    def get_logs(
        self,
        action: Optional[str] = None,
        employee_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        return self.repo.get_logs(action, employee_id, search, limit)
