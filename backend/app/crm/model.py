import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    Integer,
    Numeric,
    UniqueConstraint,
    Index,
    Table,
    text
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    account_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    contacts = relationship("Contact", back_populates="account", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="account")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contact_id = Column(String(50), unique=True, index=True, nullable=False)
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    mobile_number = Column(String(50), nullable=True, index=True)
    designation = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    account = relationship("Account", back_populates="contacts")
    leads = relationship("Lead", back_populates="contact")


class LeadRequirementType(Base):
    __tablename__ = "lead_requirement_types"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_type = Column(String(50), nullable=False, index=True)  # "Consulting", "Sample Testing", "Product"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("lead_id", "requirement_type", name="uq_lead_requirement_type"),
    )

    lead = relationship("Lead", back_populates="requirement_types")


# Normalized Association Table for Multiple Contacts on a Lead
lead_additional_contacts = Table(
    "lead_additional_contacts",
    Base.metadata,
    Column("lead_id", String(36), ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
    Column("contact_id", String(36), ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lead_id = Column(String(50), unique=True, index=True, nullable=False)
    lead_name = Column(String(255), nullable=True, index=True)  # Optional per REVY CRM Phase 1
    website_link = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    site_name = Column(String(255), nullable=True)
    business_area = Column(String(50), nullable=False)  # "Biogas", "WWT"
    requirement_type = Column(String(50), nullable=True)  # Preserved for backward-compatibility
    requirement_summary = Column(Text, nullable=True)
    requested_product_service = Column(String(255), nullable=True, index=True)
    normalized_requirement = Column(String(255), nullable=True)
    lead_source = Column(String(50), nullable=False, default="Website")  # Canonical source: Website, Email Received, etc.
    
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False, index=True)  # Primary Contact
    assigned_to_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    lifecycle_status = Column(String(50), nullable=False, default="Open", index=True)  # Open, Qualified, Disqualified
    communication_channel = Column(String(50), nullable=True, default="Email")
    remarks = Column(Text, nullable=True)
    
    connected_date = Column(Date, nullable=True, index=True)  # Client connection date
    next_follow_up_date = Column(Date, nullable=True, index=True)
    next_follow_up_action = Column(Text, nullable=True)
    last_connected_date = Column(DateTime, nullable=True)
    
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_leads_lifecycle_followup", "lifecycle_status", "next_follow_up_date"),
        Index("ix_leads_account_product", "account_id", "requested_product_service"),
        Index("ix_leads_contact_product", "contact_id", "requested_product_service"),
        Index("ix_leads_normalized_requirement", "normalized_requirement"),
    )

    account = relationship("Account", back_populates="leads")
    contact = relationship("Contact", back_populates="leads")  # Primary Contact
    additional_contacts = relationship(
        "Contact",
        secondary=lead_additional_contacts,
        backref="additional_leads",
        lazy="selectin"
    )
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    requirement_types = relationship(
        "LeadRequirementType",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="LeadRequirementType.created_at"
    )
    communications = relationship(
        "LeadCommunicationHistory",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="desc(LeadCommunicationHistory.communication_date)"
    )


class LeadCommunicationHistory(Base):
    __tablename__ = "lead_communications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    communication_id = Column(String(50), unique=True, index=True, nullable=False)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    communication_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    channel = Column(String(50), nullable=False)  # Email, Mobile/Call, WhatsApp, Teams, Other
    event_type = Column(String(100), nullable=False)  # Introductory mail sent, Introductory call, etc.
    summary = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    next_action = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="communications")
    created_by = relationship("User", foreign_keys=[created_by_id])


class CrmSequence(Base):
    __tablename__ = "crm_sequences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_name = Column(String(50), unique=True, nullable=False, index=True)  # "LEAD", "ACCOUNT", "CONTACT", "COMMUNICATION", "ENGAGEMENT", "SAMPLE", "TEST", "CHARGE", "PRODUCT_TX"
    current_value = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# =========================================================================
# CHARGE-READY BUSINESS MODELS (PHASE 1 SPECIFICATION - SECTIONS 8 & 9)
# =========================================================================

class ConsultingEngagement(Base):
    __tablename__ = "crm_consulting_engagements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    engagement_id = Column(String(50), unique=True, index=True, nullable=False)  # ENG-00001
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False, default="Consulting Engagement")
    scope_description = Column(Text, nullable=True)
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    duration_months = Column(Integer, nullable=True)
    agreed_fee = Column(Numeric(12, 2), nullable=False, default=0.0)
    billing_arrangement = Column(String(100), nullable=True)  # Monthly, Milestone-based, Lump Sum, Configurable
    status = Column(String(50), nullable=False, default="Draft")  # Draft, Active, Completed, Terminated, Renewed
    renewal_history = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    account = relationship("Account", backref="consulting_engagements")
    contact = relationship("Contact", backref="consulting_engagements")
    lead = relationship("Lead", backref="consulting_engagements")

    @property
    def duration_description(self):
        return self.scope_description or (f"{self.duration_months} months" if self.duration_months else None)

    @duration_description.setter
    def duration_description(self, val):
        self.scope_description = val

    @property
    def notes(self):
        return self.renewal_history

    @notes.setter
    def notes(self, val):
        self.renewal_history = val


class SampleSubmission(Base):
    __tablename__ = "crm_sample_submissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    sample_id = Column(String(50), unique=True, index=True, nullable=False)  # SMP-00001
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)

    sample_description = Column(String(255), nullable=False)
    sample_type = Column(String(100), nullable=True)
    receipt_date = Column(Date, nullable=True)
    condition_on_receipt = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="Received")  # Received, In-Testing, Completed, Failed, Contaminated, Spoiled, Unsuitable, Cancelled
    sample_level_charge = Column(Numeric(12, 2), nullable=False, default=0.0)

    # Operational failure / unsuitability handling (Section 9)
    is_unsuitable = Column(Boolean, default=False, nullable=False)
    failure_reason = Column(String(255), nullable=True)  # Incorrect sample, Contaminated, Spoiled/expired, Insufficient, Stopped midway, Other
    stage_reached = Column(String(100), nullable=True)
    work_performed = Column(Text, nullable=True)
    charge_decision = Column(String(50), nullable=True)  # Full Charge Authorized, Partial Charge, Waived
    authorized_charge_amount = Column(Numeric(12, 2), nullable=True)
    notes = Column(Text, nullable=True)

    # Replacement / retest sample reference
    replacement_of_sample_id = Column(String(36), ForeignKey("crm_sample_submissions.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    account = relationship("Account", backref="sample_submissions")
    contact = relationship("Contact", backref="sample_submissions")
    lead = relationship("Lead", backref="sample_submissions")
    replacement_of = relationship("SampleSubmission", remote_side=[id], backref="replacements")
    tests = relationship("SampleTestRequest", back_populates="sample", cascade="all, delete-orphan")
    charges = relationship("TestingChargeRecord", back_populates="sample", cascade="all, delete-orphan")

    @property
    def sample_status(self):
        return self.status

    @property
    def sample_charge(self):
        return self.sample_level_charge

    @property
    def chargeable_amount(self):
        return self.authorized_charge_amount

    @property
    def replacement_for_sample_id(self):
        return self.replacement_of_sample_id

    @property
    def requested_tests(self):
        return self.tests


class SampleTestRequest(Base):
    __tablename__ = "crm_sample_tests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    test_record_id = Column(String(50), unique=True, index=True, nullable=False)  # TST-00001
    sample_id = Column(String(36), ForeignKey("crm_sample_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    test_name = Column(String(255), nullable=False)
    test_type = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="Pending")  # Pending, In-Progress, Completed, Cancelled
    unit_price = Column(Numeric(12, 2), nullable=False, default=0.0)
    quantity = Column(Numeric(10, 2), nullable=False, default=1.0)
    test_result_reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    sample = relationship("SampleSubmission", back_populates="tests")

    @property
    def test_rate(self):
        return self.unit_price

    @property
    def billable_units(self):
        return self.quantity


class TestingChargeRecord(Base):
    __tablename__ = "crm_testing_charges"
    __test__ = False

    id = Column(String(36), primary_key=True, default=generate_uuid)
    charge_id = Column(String(50), unique=True, index=True, nullable=False)  # CHG-00001
    sample_id = Column(String(36), ForeignKey("crm_sample_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    charge_type = Column(String(50), nullable=False, default="TEST_CHARGE")
    charge_description = Column(String(255), nullable=True)
    charge_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    agreed_unit_rate = Column(Numeric(12, 2), nullable=True)
    billable_units = Column(Numeric(10, 2), nullable=True, default=1.0)

    sample_charge_applied = Column(Numeric(12, 2), nullable=False, default=0.0)
    tests_total = Column(Numeric(12, 2), nullable=False, default=0.0)
    approved_additional_charges = Column(Numeric(12, 2), nullable=False, default=0.0)
    applicable_discounts = Column(Numeric(12, 2), nullable=False, default=0.0)
    final_calculated_total = Column(Numeric(12, 2), nullable=False, default=0.0)

    currency = Column(String(10), nullable=False, default="INR")
    billing_status = Column(String(50), nullable=False, default="Pending")  # Pending, Billed, Waived, Invoiced
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    sample = relationship("SampleSubmission", back_populates="charges")
    lead = relationship("Lead", backref="testing_charges")
    account = relationship("Account", backref="testing_charges")


class ProductTransaction(Base):
    __tablename__ = "crm_product_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transaction_id = Column(String(50), unique=True, index=True, nullable=False)  # PRD-00001
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)

    product_name = Column(String(255), nullable=False)
    sku_code = Column(String(100), nullable=True)
    transaction_type = Column(String(50), nullable=False, default="Recommendation")  # Recommendation, Quotation, Customer Commitment, Confirmed Order
    status = Column(String(50), nullable=False, default="Pending")  # Pending, Accepted, Invoiced, Cancelled
    quantity = Column(Numeric(10, 2), nullable=False, default=1.0)
    unit_of_measure = Column(String(50), nullable=False, default="litres")  # litres, kilograms, units, metric tons
    unit_rate = Column(Numeric(12, 2), nullable=False, default=0.0)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    calculated_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="INR")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", backref="product_transactions")
    account = relationship("Account", backref="product_transactions")
    contact = relationship("Contact", backref="product_transactions")

    @property
    def product_reference(self):
        return self.product_name

    @product_reference.setter
    def product_reference(self, value):
        self.product_name = value
