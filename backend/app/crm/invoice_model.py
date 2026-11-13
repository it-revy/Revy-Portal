import uuid
from datetime import datetime, date as py_date, timezone
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Text,
    Numeric,
    Integer,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CrmCompanySettings(Base):
    __tablename__ = "crm_company_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_name = Column(String(255), nullable=False, default="REVY Environmental Solutions Pvt. Ltd.")
    wordmark = Column(String(255), nullable=True, default="REVY Environmental Solutions")
    tagline = Column(String(255), nullable=True, default="Committed for a Greener Earth!")
    address_lines = Column(JSON, nullable=False, default=list)
    email = Column(String(255), nullable=True, default="mail@revy.co.in")
    phone = Column(String(50), nullable=True, default="+91-9876543210")
    website = Column(String(255), nullable=True, default="www.revy.co.in")
    gstin = Column(String(50), nullable=True, default="24AAICR4401M1ZD")
    pan = Column(String(50), nullable=True, default="AAICR4401M")
    logo_url = Column(Text, nullable=True, default="/images/logo.png")

    bank_name = Column(String(255), nullable=False, default="Bank Of Baroda, Alkapuri Branch")
    bank_account_number = Column(String(100), nullable=False, default="01880200001183")
    bank_ifsc = Column(String(50), nullable=False, default="BARB0ALKAPU")
    bank_branch = Column(String(255), nullable=True, default="Alkapuri Branch")
    service_description = Column(String(255), nullable=True, default="Technical Testing & Analysis Services")
    sac_code = Column(String(50), nullable=True, default="998346")

    signatory_name = Column(String(255), nullable=True, default="Vanita Prasad")
    signatory_title = Column(String(255), nullable=True, default="Authorised Signatory")
    signatory_company_label = Column(String(255), nullable=True, default="For REVY Environmental Solutions Pvt. Ltd.")
    signature_image_url = Column(Text, nullable=True, default="/images/signature.png")

    default_terms = Column(JSON, nullable=False, default=list)
    footer_text = Column(Text, nullable=True, default="REVY Environmental Solutions Pvt. Ltd. | 313-314, Siddharth Upscale Vasna Road, Vadodara-390007, Gujarat, India | www.revy.co.in")

    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    updated_by = relationship("User", foreign_keys=[updated_by_id])


class ProformaInvoice(Base):
    __tablename__ = "crm_proforma_invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    pi_number = Column(String(50), unique=True, index=True, nullable=False)  # REVY/PI/2026-27/0001
    opportunity_id = Column(String(36), ForeignKey("crm_opportunities.id", ondelete="CASCADE"), nullable=False, index=True)
    quotation_id = Column(String(36), ForeignKey("crm_opportunity_quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    current_revision_number = Column(Integer, nullable=False, default=1)
    financial_year = Column(String(20), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="Issued", index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    opportunity = relationship("Opportunity", backref="proforma_invoices")
    quotation = relationship("OpportunityQuotation", backref="proforma_invoices")
    account = relationship("Account", backref="proforma_invoices")
    created_by = relationship("User", foreign_keys=[created_by_id])
    revisions = relationship("ProformaInvoiceRevision", back_populates="proforma_invoice", cascade="all, delete-orphan", order_by="desc(ProformaInvoiceRevision.revision_number)")


class ProformaInvoiceRevision(Base):
    __tablename__ = "crm_proforma_invoice_revisions"
    __table_args__ = (
        UniqueConstraint("proforma_invoice_id", "revision_number", name="uq_pi_rev_num"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    proforma_invoice_id = Column(String(36), ForeignKey("crm_proforma_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False, default=1)
    pi_number = Column(String(50), nullable=False, index=True)
    pi_date = Column(Date, nullable=False, default=lambda: py_date.today())
    financial_year = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False, default="Issued")

    reference_note = Column(Text, nullable=True)
    currency = Column(String(10), nullable=False, default="INR")

    subtotal = Column(Numeric(18, 4), nullable=False, default=0.0)
    tax_type = Column(String(50), nullable=False, default="INTRA_STATE")  # INTRA_STATE, INTER_STATE, EXEMPT
    tax_configuration_id = Column(String(36), ForeignKey("crm_tax_configurations.id", ondelete="SET NULL"), nullable=True)
    cgst_rate = Column(Numeric(6, 4), nullable=False, default=0.0)
    cgst_amount = Column(Numeric(18, 4), nullable=False, default=0.0)
    sgst_rate = Column(Numeric(6, 4), nullable=False, default=0.0)
    sgst_amount = Column(Numeric(18, 4), nullable=False, default=0.0)
    igst_rate = Column(Numeric(6, 4), nullable=False, default=0.0)
    igst_amount = Column(Numeric(18, 4), nullable=False, default=0.0)
    total_tax = Column(Numeric(18, 4), nullable=False, default=0.0)
    grand_total = Column(Numeric(18, 4), nullable=False, default=0.0)

    # Immutable historical snapshots:
    company_snapshot = Column(JSON, nullable=False)
    customer_snapshot = Column(JSON, nullable=False)
    terms_snapshot = Column(JSON, nullable=False)
    notes = Column(Text, nullable=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    proforma_invoice = relationship("ProformaInvoice", back_populates="revisions")
    tax_configuration = relationship("TaxConfiguration")
    created_by = relationship("User", foreign_keys=[created_by_id])
    items = relationship("ProformaInvoiceItem", back_populates="revision", cascade="all, delete-orphan", order_by="ProformaInvoiceItem.sr_no")


class ProformaInvoiceItem(Base):
    __tablename__ = "crm_proforma_invoice_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    revision_id = Column(String(36), ForeignKey("crm_proforma_invoice_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    sr_no = Column(Integer, nullable=False, default=1)
    item_type = Column(String(50), nullable=False, default="SERVICE")
    service_id = Column(String(36), ForeignKey("crm_services.id", ondelete="SET NULL"), nullable=True)
    package_id = Column(String(36), ForeignKey("crm_packages.id", ondelete="SET NULL"), nullable=True)

    item_code = Column(String(50), nullable=True)
    item_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False, default=1.0)
    unit = Column(String(50), nullable=True)
    rate = Column(Numeric(18, 4), nullable=False, default=0.0)
    amount = Column(Numeric(18, 4), nullable=False, default=0.0)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    revision = relationship("ProformaInvoiceRevision", back_populates="items")
    service = relationship("Service")
    package = relationship("Package")
