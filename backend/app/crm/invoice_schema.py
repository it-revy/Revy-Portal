from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import date as py_date, datetime
from decimal import Decimal
from app.crm.catalogue_schema import CamelResponseModel


class CompanySettingsResponse(CamelResponseModel):
    id: str
    companyName: str
    wordmark: Optional[str] = None
    tagline: Optional[str] = None
    addressLines: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    logoUrl: Optional[str] = None

    bankName: str
    bankAccountNumber: str
    bankIfsc: str
    bankBranch: Optional[str] = None
    serviceDescription: Optional[str] = None
    sacCode: Optional[str] = None

    signatoryName: Optional[str] = None
    signatoryTitle: Optional[str] = None
    signatoryCompanyLabel: Optional[str] = None
    signatureImageUrl: Optional[str] = None

    defaultTerms: List[str] = Field(default_factory=list)
    footerText: Optional[str] = None

    createdAt: datetime
    updatedAt: datetime
    updatedById: Optional[str] = None


class CompanySettingsUpdate(BaseModel):
    companyName: Optional[str] = None
    wordmark: Optional[str] = None
    tagline: Optional[str] = None
    addressLines: Optional[List[str]] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    logoUrl: Optional[str] = None

    bankName: Optional[str] = None
    bankAccountNumber: Optional[str] = None
    bankIfsc: Optional[str] = None
    bankBranch: Optional[str] = None
    serviceDescription: Optional[str] = None
    sacCode: Optional[str] = None

    signatoryName: Optional[str] = None
    signatoryTitle: Optional[str] = None
    signatoryCompanyLabel: Optional[str] = None
    signatureImageUrl: Optional[str] = None

    defaultTerms: Optional[List[str]] = None
    footerText: Optional[str] = None


class ProformaInvoiceItemInput(BaseModel):
    srNo: Optional[int] = Field(None, alias="sr_no")
    itemType: str = Field(default="SERVICE", alias="item_type")  # SERVICE, PACKAGE, ADDON, CUSTOM_SERVICE, CUSTOM_PRODUCT
    serviceId: Optional[str] = Field(None, alias="service_id")
    packageId: Optional[str] = Field(None, alias="package_id")
    itemCode: Optional[str] = Field(None, alias="item_code")
    name: str
    description: Optional[str] = None
    quantity: Decimal = Field(default=Decimal("1.0"), gt=0)
    unit: Optional[str] = None
    rate: Decimal = Field(default=Decimal("0.0"), ge=0)
    notes: Optional[str] = None


class ProformaInvoiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    srNo: int = Field(..., alias="sr_no")
    itemType: str = Field(..., alias="item_type")
    serviceId: Optional[str] = Field(None, alias="service_id")
    packageId: Optional[str] = Field(None, alias="package_id")
    itemCode: Optional[str] = Field(None, alias="item_code")
    name: str = Field(..., alias="item_name")
    description: Optional[str] = None
    quantity: float
    unit: Optional[str] = None
    rate: float
    amount: float
    notes: Optional[str] = None


class ProformaInvoicePreviewRequest(BaseModel):
    opportunityId: str = Field(..., alias="opportunity_id")
    quotationId: str = Field(..., alias="quotation_id")
    items: List[ProformaInvoiceItemInput]
    taxType: str = Field(default="INTRA_STATE", alias="tax_type")  # INTRA_STATE, INTER_STATE, EXEMPT
    taxConfigurationId: Optional[str] = Field(None, alias="tax_configuration_id")
    piDate: Optional[py_date] = Field(None, alias="pi_date")
    referenceNote: Optional[str] = Field(None, alias="reference_note")
    terms: Optional[List[str]] = None
    notes: Optional[str] = None


class ProformaInvoiceCreate(BaseModel):
    opportunityId: str = Field(..., alias="opportunity_id")
    quotationId: str = Field(..., alias="quotation_id")
    items: List[ProformaInvoiceItemInput]
    taxType: str = Field(default="INTRA_STATE", alias="tax_type")  # INTRA_STATE, INTER_STATE, EXEMPT
    taxConfigurationId: Optional[str] = Field(None, alias="tax_configuration_id")
    piDate: Optional[py_date] = Field(None, alias="pi_date")
    referenceNote: Optional[str] = Field(None, alias="reference_note")
    terms: Optional[List[str]] = None
    notes: Optional[str] = None


class ProformaInvoiceRevisionCreate(BaseModel):
    items: List[ProformaInvoiceItemInput]
    taxType: str = Field(default="INTRA_STATE", alias="tax_type")
    taxConfigurationId: Optional[str] = Field(None, alias="tax_configuration_id")
    piDate: Optional[py_date] = Field(None, alias="pi_date")
    referenceNote: Optional[str] = Field(None, alias="reference_note")
    terms: Optional[List[str]] = None
    notes: Optional[str] = None


class ProformaInvoiceRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    proformaInvoiceId: str = Field(..., alias="proforma_invoice_id")
    revisionNumber: int = Field(..., alias="revision_number")
    piNumber: str = Field(..., alias="pi_number")
    piDate: py_date = Field(..., alias="pi_date")
    financialYear: str = Field(..., alias="financial_year")
    status: str
    referenceNote: Optional[str] = Field(None, alias="reference_note")
    currency: str = "INR"
    subtotal: float
    taxType: str = Field(..., alias="tax_type")
    cgstRate: float = Field(..., alias="cgst_rate")
    cgstAmount: float = Field(..., alias="cgst_amount")
    sgstRate: float = Field(..., alias="sgst_rate")
    sgstAmount: float = Field(..., alias="sgst_amount")
    igstRate: float = Field(..., alias="igst_rate")
    igstAmount: float = Field(..., alias="igst_amount")
    totalTax: float = Field(..., alias="total_tax")
    grandTotal: float = Field(..., alias="grand_total")
    companySnapshot: Dict[str, Any] = Field(..., alias="company_snapshot")
    customerSnapshot: Dict[str, Any] = Field(..., alias="customer_snapshot")
    termsSnapshot: List[str] = Field(..., alias="terms_snapshot")
    notes: Optional[str] = None
    createdAt: datetime = Field(..., alias="created_at")
    items: List[ProformaInvoiceItemResponse] = Field(default_factory=list)


class ProformaInvoiceDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    piNumber: str = Field(..., alias="pi_number")
    opportunityId: str = Field(..., alias="opportunity_id")
    quotationId: str = Field(..., alias="quotation_id")
    accountId: str = Field(..., alias="account_id")
    currentRevisionNumber: int = Field(..., alias="current_revision_number")
    financialYear: str = Field(..., alias="financial_year")
    status: str
    createdAt: datetime = Field(..., alias="created_at")
    updatedAt: datetime = Field(..., alias="updated_at")
    currentRevision: Optional[ProformaInvoiceRevisionResponse] = None
    revisions: List[ProformaInvoiceRevisionResponse] = Field(default_factory=list)


class CollateralItem(BaseModel):
    opportunityId: str
    opportunityNumber: str
    opportunityName: str
    accountId: str
    accountName: str
    customerId: Optional[str] = None
    ownerName: Optional[str] = None
    quotationId: Optional[str] = None
    quotationNumber: Optional[str] = None
    quotationStatus: Optional[str] = None
    quotationAmount: Optional[float] = None
    piId: Optional[str] = None
    piNumber: Optional[str] = None
    piStatus: Optional[str] = None
    piRevisionNumber: Optional[int] = None
    piAmount: Optional[float] = None
    lastUpdatedDate: datetime


class CollateralListResponse(BaseModel):
    success: bool = True
    totalCount: int
    items: List[CollateralItem]
