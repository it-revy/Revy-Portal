import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.audit.model import AuditLog

class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        action: str,
        application: str = "BREAKFAST",
        performed_by_employee_id: Optional[str] = None,
        performed_by_name: Optional[str] = None,
        role_used: Optional[str] = None,
        target_record_id: Optional[str] = None,
        target_employee_id: Optional[str] = None,
        target_employee_name: Optional[str] = None,
        details: Optional[str] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        audit_id = f"AUD-{now_ts}-{str(uuid.uuid4())[:4]}"
        log = AuditLog(
            audit_id=audit_id,
            application=application,
            action=action,
            performed_by_employee_id=performed_by_employee_id,
            performed_by_name=performed_by_name,
            role_used=role_used,
            target_record_id=target_record_id,
            target_employee_id=target_employee_id,
            target_employee_name=target_employee_name,
            details=details,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs(
        self,
        action: Optional[str] = None,
        employee_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        query = self.db.query(AuditLog)

        if action and action != "ALL":
            query = query.filter(AuditLog.action == action)

        if employee_id:
            query = query.filter(AuditLog.performed_by_employee_id == employee_id.upper())

        if search and search.strip():
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    AuditLog.audit_id.ilike(s),
                    AuditLog.action.ilike(s),
                    AuditLog.performed_by_employee_id.ilike(s),
                    AuditLog.performed_by_name.ilike(s),
                    AuditLog.role_used.ilike(s),
                    AuditLog.target_employee_id.ilike(s),
                    AuditLog.target_employee_name.ilike(s),
                    AuditLog.details.ilike(s)
                )
            )

        return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()
