import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    audit_id = Column(String(100), unique=True, index=True, nullable=False)
    application = Column(String(50), default="BREAKFAST", nullable=False)
    action = Column(String(100), nullable=False, index=True)
    performed_by_employee_id = Column(String(50), nullable=True, index=True)
    performed_by_name = Column(String(150), nullable=True)
    role_used = Column(String(50), nullable=True)
    target_record_id = Column(String(100), nullable=True)
    target_employee_id = Column(String(50), nullable=True, index=True)
    target_employee_name = Column(String(150), nullable=True)
    details = Column(Text, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
