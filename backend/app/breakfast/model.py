import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, JSON, UniqueConstraint, Index
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())


class PublicHoliday(Base):
    __tablename__ = "public_holidays"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    holiday_id = Column(String(100), unique=True, index=True, nullable=False)
    date = Column(String(10), unique=True, index=True, nullable=False)  # YYYY-MM-DD
    name = Column(String(150), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    created_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BreakfastSetting(Base):
    __tablename__ = "breakfast_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    cutoff_time = Column(String(10), default="12:00", nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    auto_lock_enabled = Column(Boolean, default=True, nullable=False)
    breakfast_fund_limit = Column(Float, default=2500.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BreakfastReason(Base):
    __tablename__ = "breakfast_reasons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, index=True, nullable=False)
    label = Column(String(100), nullable=False)
    is_custom_allowed = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BreakfastRecord(Base):
    __tablename__ = "breakfast_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    record_id = Column(String(100), unique=True, index=True, nullable=False)
    employee_id = Column(String(50), nullable=True, index=True)
    employee_name = Column(String(150), nullable=True)
    business_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    record_type = Column(String(20), default="CURRENT", nullable=False, index=True)  # CURRENT, HISTORICAL

    # Historical / Daily item details
    snack = Column(String(150), nullable=True)
    snack_quantity = Column(String(50), nullable=True)  # e.g. "400GM", "500GM", "1kg", "4pkt"
    snack_cost = Column(Float, default=0.0, nullable=True)
    fruit = Column(String(150), nullable=True)
    fruit_quantity = Column(String(50), nullable=True)  # e.g. "1kg", "750GM", "5PKT"
    fruit_cost = Column(Float, default=0.0, nullable=True)
    total_cost = Column(Float, default=0.0, nullable=True)
    paid_by = Column(String(100), nullable=True)
    payment_type = Column(String(50), nullable=True)  # Cash, GPay, Bank Transfer, etc.

    # Source & duplicate tracking
    source = Column(String(50), default="EMPLOYEE", nullable=False)  # EMPLOYEE, ADMIN, HISTORICAL_IMPORT
    source_id = Column(String(100), nullable=True, index=True)  # e.g. HIST-2026-06-23-001
    external_reference = Column(String(100), nullable=True, index=True)

    # Response & status
    response = Column(String(20), default="TAKING", nullable=True)  # YES / NO / TAKING / NOT_TAKING / HISTORICAL
    employee_response = Column(String(20), default="TAKING", nullable=True)
    actual_status = Column(String(20), nullable=True)  # TAKEN / NOT_TAKEN / NO_RESPONSE / NO_SHOW
    actual_status_source = Column(String(30), default="EMPLOYEE_RESPONSE", nullable=False)
    reason_code = Column(String(50), nullable=True)
    reason_text = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    history = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_record_emp_date", "employee_id", "business_date"),
        Index("ix_record_type_date", "record_type", "business_date"),
    )


class BreakfastNonParticipationPeriod(Base):
    __tablename__ = "breakfast_non_participation_periods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    period_id = Column(String(100), unique=True, index=True, nullable=False)
    employee_id = Column(String(50), nullable=False, index=True)
    from_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    to_date = Column(String(10), nullable=False, index=True)    # YYYY-MM-DD
    reason_code = Column(String(50), nullable=False)
    reason_text = Column(Text, nullable=True)
    source = Column(String(30), default="EMPLOYEE", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BreakfastDailyEntry(Base):
    __tablename__ = "breakfast_daily_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    business_date = Column(String(10), unique=True, index=True, nullable=False)  # YYYY-MM-DD
    employee_snapshot = Column(JSON, default=list)
    summary = Column(JSON, default=dict)
    breakfast_items = Column(JSON, default=list)
    common_items = Column(JSON, default=list)
    total_cost = Column(Float, default=0.0, nullable=False)
    record_type = Column(String(20), default="CURRENT", nullable=False, index=True)  # CURRENT, HISTORICAL
    paid_by = Column(String(100), nullable=True)
    payment_type = Column(String(50), nullable=True)
    source = Column(String(50), default="OPERATIONAL", nullable=False)
    source_id = Column(String(100), nullable=True, index=True)
    created_by = Column(String(150), nullable=False)
    updated_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BreakfastAdditionalOrder(Base):
    __tablename__ = "breakfast_additional_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(100), unique=True, index=True, nullable=False)
    business_date = Column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    order_title = Column(String(255), default="Additional Breakfast / Snack Order", nullable=False)
    order_time = Column(String(20), nullable=True)
    applicable_employee_snapshot = Column(JSON, default=list)
    applicable_employee_count = Column(Integer, default=0, nullable=False)
    breakfast_items = Column(JSON, default=list)
    common_items = Column(JSON, default=list)
    total_cost = Column(Float, default=0.0, nullable=False)
    created_by = Column(String(150), nullable=False)
    updated_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BreakfastOrder(Base):
    __tablename__ = "breakfast_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(100), unique=True, index=True, nullable=False)
    business_date = Column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    vendor_name = Column(String(255), default="Internal Catering / Vendor", nullable=False)
    notes = Column(Text, default="", nullable=False)
    created_by_employee_id = Column(String(50), nullable=False)
    created_by_employee_name = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BreakfastOrderItem(Base):
    __tablename__ = "breakfast_order_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    item_id = Column(String(100), unique=True, index=True, nullable=False)
    order_id = Column(String(100), index=True, nullable=False)
    business_date = Column(String(10), index=True, nullable=False)
    order_type = Column(String(20), nullable=False)  # INDIVIDUAL / COMMON
    employee_id = Column(String(50), nullable=True, index=True)
    employee_name = Column(String(150), nullable=True)
    item_name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BreakfastMoneyTransaction(Base):
    __tablename__ = "breakfast_money_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transaction_id = Column(String(100), unique=True, index=True, nullable=False)
    transaction_date = Column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    transaction_time = Column(String(20), nullable=False)
    type = Column(String(50), index=True, nullable=False)  # MONEY_RECEIVED, BREAKFAST_EXPENSE, ADJUSTMENT, REVERSAL
    amount = Column(Float, nullable=False)
    balance_after_transaction = Column(Float, nullable=False)
    source = Column(String(100), default="Finance", nullable=False)
    reference_type = Column(String(50), nullable=False)
    reference_id = Column(String(100), nullable=True)
    expense_category = Column(String(50), default="DAILY_BREAKFAST", nullable=False)
    expense_purpose = Column(String(50), default="EMPLOYEE", nullable=False)
    description = Column(Text, default="", nullable=False)
    note = Column(Text, default="", nullable=False)
    created_by = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_money_txn_date_created", "transaction_date", "created_at"),
    )


class BreakfastFundRequest(Base):
    __tablename__ = "breakfast_fund_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(100), unique=True, index=True, nullable=False)
    requested_by = Column(String(150), nullable=False)
    request_date = Column(String(10), nullable=False)
    request_time = Column(String(20), nullable=False)
    current_balance = Column(Float, nullable=False)
    fund_limit = Column(Float, default=2500.0, nullable=False)
    requested_amount = Column(Float, nullable=False)
    expected_balance = Column(Float, nullable=False)
    reason = Column(Text, default="", nullable=False)
    status = Column(String(50), default="PENDING_APPROVAL", nullable=False, index=True)
    approved_amount = Column(Float, default=0.0, nullable=False)
    approved_by = Column(String(150), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    provided_amount = Column(Float, default=0.0, nullable=False)
    provided_by = Column(String(150), nullable=True)
    provided_at = Column(DateTime, nullable=True)
    provided_date = Column(String(10), nullable=True)
    provided_time = Column(String(20), nullable=True)
    reference = Column(String(255), nullable=True)
    provided_note = Column(Text, nullable=True)
    verified_amount = Column(Float, default=0.0, nullable=False)
    verified_by = Column(String(150), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    difference_reported = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
