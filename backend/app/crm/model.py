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
    UniqueConstraint,
    Index
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


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lead_id = Column(String(50), unique=True, index=True, nullable=False)
    lead_name = Column(String(255), nullable=False, index=True)
    website_link = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    site_name = Column(String(255), nullable=True)
    business_area = Column(String(50), nullable=False)  # "Biogas", "WWT"
    requirement_type = Column(String(50), nullable=False)  # "Direct Product/Service", "Sample Testing", "Undetermined"
    requirement_summary = Column(Text, nullable=True)
    requested_product_service = Column(String(255), nullable=True, index=True)
    normalized_requirement = Column(String(255), nullable=True, index=True)
    lead_source = Column(String(50), nullable=False, default="Website")  # Website, Email, Phone, WhatsApp, Referral, etc.
    
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_to_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    lifecycle_status = Column(String(50), nullable=False, default="Open", index=True)  # Open, Qualified, Disqualified
    communication_channel = Column(String(50), nullable=True, default="Email")
    remarks = Column(Text, nullable=True)
    
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
        Index(
            "uq_open_lead_account_product",
            "account_id",
            "normalized_requirement",
            unique=True,
            postgresql_where="lifecycle_status = 'Open' AND account_id IS NOT NULL AND normalized_requirement IS NOT NULL",
            sqlite_where="lifecycle_status = 'Open' AND account_id IS NOT NULL AND normalized_requirement IS NOT NULL"
        ),
        Index(
            "uq_open_lead_contact_product",
            "contact_id",
            "normalized_requirement",
            unique=True,
            postgresql_where="lifecycle_status = 'Open' AND account_id IS NULL AND normalized_requirement IS NOT NULL",
            sqlite_where="lifecycle_status = 'Open' AND account_id IS NULL AND normalized_requirement IS NOT NULL"
        ),
    )

    account = relationship("Account", back_populates="leads")
    contact = relationship("Contact", back_populates="leads")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
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
    entity_name = Column(String(50), unique=True, nullable=False, index=True)  # "LEAD", "ACCOUNT", "CONTACT", "COMMUNICATION"
    current_value = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
