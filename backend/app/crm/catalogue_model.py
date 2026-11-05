import uuid
from datetime import datetime, timezone, date as py_date
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
    CheckConstraint,
    Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class ServiceCategory(Base):
    __tablename__ = "crm_service_categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)  # LAB-01
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    prefix = Column(String(10), nullable=False)  # WWT, OWC, BIO, SLG, OPT
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    subcategories = relationship("ServiceSubcategory", back_populates="category", cascade="all, delete-orphan")
    services = relationship("Service", back_populates="category")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class ServiceSubcategory(Base):
    __tablename__ = "crm_service_subcategories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    category_id = Column(String(36), ForeignKey("crm_service_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # LAB-01-SUB-01
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    category = relationship("ServiceCategory", back_populates="subcategories")
    services = relationship("Service", back_populates="subcategory")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class BillingUnit(Base):
    __tablename__ = "crm_billing_units"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)  # TEST, SAMPLE, ANALYSIS, PACKAGE, STUDY, ADDON
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class ReportingUnit(Base):
    __tablename__ = "crm_reporting_units"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    symbol = Column(String(50), nullable=False)  # mg/L, %, ppm, NTU
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class SampleType(Base):
    __tablename__ = "crm_sample_types"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class TestingMethod(Base):
    __tablename__ = "crm_testing_methods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    method_name = Column(String(255), nullable=False, index=True)
    standard_reference = Column(String(255), nullable=True)  # IS 3025, APHA, ASTM
    revision = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class Currency(Base):
    __tablename__ = "crm_currencies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(10), unique=True, nullable=False, index=True)  # INR, USD, EUR
    name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False)  # ₹, $, €
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class TaxConfiguration(Base):
    __tablename__ = "crm_tax_configurations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    tax_type = Column(String(50), nullable=False, default="INTRA_STATE")  # INTRA_STATE, INTER_STATE, EXEMPT
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    rates = relationship("TaxRate", back_populates="configuration", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class TaxRate(Base):
    __tablename__ = "crm_tax_rates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    configuration_id = Column(String(36), ForeignKey("crm_tax_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    component_name = Column(String(50), nullable=False)  # CGST, SGST, IGST
    rate_percentage = Column(Numeric(6, 4), nullable=False, default=0.0)  # e.g. 9.0000
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    configuration = relationship("TaxConfiguration", back_populates="rates")


class Service(Base):
    __tablename__ = "crm_services"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_code = Column(String(50), unique=True, nullable=False, index=True)  # WWT-001, OWC-001
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    category_id = Column(String(36), ForeignKey("crm_service_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    subcategory_id = Column(String(36), ForeignKey("crm_service_subcategories.id", ondelete="RESTRICT"), nullable=False, index=True)
    billing_unit_id = Column(String(36), ForeignKey("crm_billing_units.id", ondelete="RESTRICT"), nullable=False, index=True)
    currency_id = Column(String(36), ForeignKey("crm_currencies.id", ondelete="RESTRICT"), nullable=False, index=True)

    minimum_billing_quantity = Column(Integer, nullable=False, default=1)
    standard_price = Column(Numeric(18, 4), nullable=False, default=0.0)
    effective_date = Column(Date, nullable=False, default=lambda: py_date.today())

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    is_addon_eligible = Column(Boolean, default=False, nullable=False)  # Can be selected as an add-on
    can_have_addons = Column(Boolean, default=True, nullable=False)    # Allows add-ons (like C/N Ratio) to attach
    source_note = Column(String(255), nullable=True)  # Preserved unverified note like 'SR 50/51'

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("minimum_billing_quantity >= 1", name="ck_service_min_billing_qty_pos"),
        CheckConstraint("standard_price >= 0", name="ck_service_standard_price_non_neg"),
    )

    category = relationship("ServiceCategory", back_populates="services")
    subcategory = relationship("ServiceSubcategory", back_populates="services")
    billing_unit = relationship("BillingUnit")
    currency = relationship("Currency")

    sample_types = relationship("ServiceSampleType", back_populates="service", cascade="all, delete-orphan")
    testing_methods = relationship("ServiceTestingMethod", back_populates="service", cascade="all, delete-orphan")
    reporting_parameters = relationship("ServiceReportingParameter", back_populates="service", cascade="all, delete-orphan")
    price_history = relationship("ServicePriceHistory", back_populates="service", cascade="all, delete-orphan", order_by="desc(ServicePriceHistory.effective_date)")

    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class ServiceSampleType(Base):
    __tablename__ = "crm_service_sample_types"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_id = Column(String(36), ForeignKey("crm_services.id", ondelete="CASCADE"), nullable=False, index=True)
    sample_type_id = Column(String(36), ForeignKey("crm_sample_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("service_id", "sample_type_id", name="uq_service_sample_type"),
    )

    service = relationship("Service", back_populates="sample_types")
    sample_type = relationship("SampleType")


class ServiceTestingMethod(Base):
    __tablename__ = "crm_service_testing_methods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_id = Column(String(36), ForeignKey("crm_services.id", ondelete="CASCADE"), nullable=False, index=True)
    testing_method_id = Column(String(36), ForeignKey("crm_testing_methods.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("service_id", "testing_method_id", name="uq_service_testing_method"),
    )

    service = relationship("Service", back_populates="testing_methods")
    testing_method = relationship("TestingMethod")


class ServiceReportingParameter(Base):
    __tablename__ = "crm_service_reporting_parameters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_id = Column(String(36), ForeignKey("crm_services.id", ondelete="CASCADE"), nullable=False, index=True)
    testing_method_id = Column(String(36), ForeignKey("crm_testing_methods.id", ondelete="SET NULL"), nullable=True, index=True)
    parameter_name = Column(String(255), nullable=False)
    reporting_unit_id = Column(String(36), ForeignKey("crm_reporting_units.id", ondelete="RESTRICT"), nullable=False, index=True)
    min_range = Column(Numeric(18, 4), nullable=True)
    max_range = Column(Numeric(18, 4), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    service = relationship("Service", back_populates="reporting_parameters")
    testing_method = relationship("TestingMethod")
    reporting_unit = relationship("ReportingUnit")


class ServicePriceHistory(Base):
    __tablename__ = "crm_service_price_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_id = Column(String(36), ForeignKey("crm_services.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Numeric(18, 4), nullable=False)
    currency_id = Column(String(36), ForeignKey("crm_currencies.id", ondelete="RESTRICT"), nullable=False, index=True)
    effective_date = Column(Date, nullable=False, index=True)
    changed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_service_price_history_non_neg"),
    )

    service = relationship("Service", back_populates="price_history")
    currency = relationship("Currency")
    changed_by = relationship("User", foreign_keys=[changed_by_id])


class Package(Base):
    __tablename__ = "crm_packages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    package_code = Column(String(50), unique=True, nullable=False, index=True)  # PKG-001
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    category_id = Column(String(36), ForeignKey("crm_service_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    subcategory_id = Column(String(36), ForeignKey("crm_service_subcategories.id", ondelete="SET NULL"), nullable=True, index=True)
    currency_id = Column(String(36), ForeignKey("crm_currencies.id", ondelete="RESTRICT"), nullable=False, index=True)

    fixed_package_price = Column(Numeric(18, 4), nullable=False, default=0.0)
    current_version = Column(Integer, nullable=False, default=1)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("fixed_package_price >= 0", name="ck_package_price_non_neg"),
    )

    category = relationship("ServiceCategory")
    subcategory = relationship("ServiceSubcategory")
    currency = relationship("Currency")
    versions = relationship("PackageVersion", back_populates="package", cascade="all, delete-orphan", order_by="desc(PackageVersion.version_number)")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class PackageVersion(Base):
    __tablename__ = "crm_package_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    package_id = Column(String(36), ForeignKey("crm_packages.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    fixed_price = Column(Numeric(18, 4), nullable=False)
    currency_id = Column(String(36), ForeignKey("crm_currencies.id", ondelete="RESTRICT"), nullable=False)
    change_summary = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    effective_date = Column(Date, nullable=False, default=lambda: py_date.today())

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("package_id", "version_number", name="uq_package_version_num"),
        CheckConstraint("fixed_price >= 0", name="ck_package_ver_price_non_neg"),
    )

    package = relationship("Package", back_populates="versions")
    currency = relationship("Currency")
    components = relationship("PackageComponent", back_populates="package_version", cascade="all, delete-orphan")
    addon_configurations = relationship("PackageAddOnConfiguration", back_populates="package_version", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_id])


class PackageComponent(Base):
    __tablename__ = "crm_package_components"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    package_version_id = Column(String(36), ForeignKey("crm_package_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(String(36), ForeignKey("crm_services.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    reference_price = Column(Numeric(18, 4), nullable=False, default=0.0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("package_version_id", "service_id", name="uq_pkg_ver_service"),
        CheckConstraint("quantity >= 1", name="ck_pkg_comp_qty_pos"),
    )

    package_version = relationship("PackageVersion", back_populates="components")
    service = relationship("Service")


class PackageAddOnConfiguration(Base):
    __tablename__ = "crm_package_addon_configurations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    package_version_id = Column(String(36), ForeignKey("crm_package_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    addon_service_id = Column(String(36), ForeignKey("crm_services.id", ondelete="RESTRICT"), nullable=False, index=True)
    default_quantity = Column(Integer, nullable=False, default=1)
    override_price = Column(Numeric(18, 4), nullable=True)  # If null, uses service standard_price
    is_mandatory = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("package_version_id", "addon_service_id", name="uq_pkg_ver_addon_service"),
        CheckConstraint("default_quantity >= 1", name="ck_pkg_addon_qty_pos"),
    )

    package_version = relationship("PackageVersion", back_populates="addon_configurations")
    addon_service = relationship("Service")


class OpportunityQuotationItem(Base):
    __tablename__ = "crm_opportunity_quotation_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quotation_id = Column(String(36), ForeignKey("crm_opportunity_quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = Column(String(20), nullable=False)  # "SERVICE", "PACKAGE", "ADDON"

    service_id = Column(String(36), ForeignKey("crm_services.id", ondelete="SET NULL"), nullable=True, index=True)
    package_id = Column(String(36), ForeignKey("crm_packages.id", ondelete="SET NULL"), nullable=True, index=True)
    package_version_id = Column(String(36), ForeignKey("crm_package_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_item_id = Column(String(36), ForeignKey("crm_opportunity_quotation_items.id", ondelete="CASCADE"), nullable=True, index=True)

    # Immutable historical snapshots:
    item_code = Column(String(50), nullable=False)
    item_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    billing_unit = Column(String(50), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)

    standard_price = Column(Numeric(18, 4), nullable=False, default=0.0)
    unit_price = Column(Numeric(18, 4), nullable=False, default=0.0)  # Negotiated / agreed line price
    total_price = Column(Numeric(18, 4), nullable=False, default=0.0)  # quantity * unit_price
    currency = Column(String(10), nullable=False, default="INR")

    # Snapshot JSON strings for historical preservation
    testing_method_snapshot = Column(Text, nullable=True)  # {"name": "...", "standard": "...", "revision": "..."}
    reporting_parameters_snapshot = Column(Text, nullable=True)  # [{"name": "...", "unit": "...", "min": ..., "max": ...}]
    package_components_snapshot = Column(Text, nullable=True)  # [{"code": "...", "name": "...", "qty": ..., "ref_price": ...}]

    # Tax Snapshot
    tax_configuration_id = Column(String(36), ForeignKey("crm_tax_configurations.id", ondelete="SET NULL"), nullable=True)
    tax_type = Column(String(50), nullable=True)
    taxable_amount = Column(Numeric(18, 4), nullable=False, default=0.0)
    cgst_rate = Column(Numeric(6, 4), nullable=False, default=0.0)
    cgst_amount = Column(Numeric(18, 4), nullable=False, default=0.0)
    sgst_rate = Column(Numeric(6, 4), nullable=False, default=0.0)
    sgst_amount = Column(Numeric(18, 4), nullable=False, default=0.0)
    igst_rate = Column(Numeric(6, 4), nullable=False, default=0.0)
    igst_amount = Column(Numeric(18, 4), nullable=False, default=0.0)
    total_tax = Column(Numeric(18, 4), nullable=False, default=0.0)
    final_total = Column(Numeric(18, 4), nullable=False, default=0.0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_quotation_item_qty_pos"),
        CheckConstraint("unit_price >= 0", name="ck_quotation_item_price_non_neg"),
    )

    quotation = relationship("OpportunityQuotation", backref="items")
    service = relationship("Service")
    package = relationship("Package")
    package_version = relationship("PackageVersion")
    parent_item = relationship("OpportunityQuotationItem", remote_side=[id], backref="child_items")
    tax_configuration = relationship("TaxConfiguration")
