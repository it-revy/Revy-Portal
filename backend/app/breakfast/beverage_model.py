import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index
)
from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class BmsBeverage(Base):
    """
    Catalogue table for configured beverages (Tea, Green Tea, Coffee, etc.).
    All beverages use 'Cups' as unit of measurement.
    """
    __tablename__ = "bms_beverages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String(20), default="Cups", nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class BmsBeverageEntry(Base):
    """
    Daily beverage consumption logs by session (MORNING, EVENING).
    Enforces exactly one beverage per employee per session per business date.
    Preserves historical name snapshots and supports soft deletion.
    """
    __tablename__ = "bms_beverage_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(50), nullable=False, index=True)
    employee_name_snapshot = Column(String(150), nullable=False)
    beverage_id = Column(String(36), ForeignKey("bms_beverages.id", ondelete="RESTRICT"), nullable=False, index=True)
    beverage_name_snapshot = Column(String(100), nullable=False)
    business_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    session = Column(String(20), nullable=False, index=True)  # MORNING, EVENING
    quantity = Column(Integer, nullable=False)  # Positive integer >= 1
    unit = Column(String(20), default="Cups", nullable=False)
    source = Column(String(30), default="EMPLOYEE", nullable=False)  # EMPLOYEE, ADMIN
    notes = Column(Text, nullable=True)

    # Soft deletion metadata
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(150), nullable=True)
    deletion_reason = Column(Text, nullable=True)

    # Audit & Tracking
    created_by = Column(String(150), nullable=True)
    updated_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("employee_id", "business_date", "session", name="uq_bms_beverage_entries_emp_date_session"),
        Index("ix_bms_beverage_entries_emp_date", "employee_id", "business_date"),
        Index("ix_bms_beverage_entries_date_session", "business_date", "session"),
    )
