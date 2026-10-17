import re
from typing import Optional, List, Dict, Any
from datetime import datetime, date as py_date
from pydantic import BaseModel, Field, field_validator


# =========================================================================
# DOMAIN / WEBSITE VALIDATION HELPER
# =========================================================================

DOMAIN_REGEX = re.compile(
    r"^(?:https?://)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?$",
    re.IGNORECASE
)

def validate_and_normalize_website(url: Optional[str]) -> Optional[str]:
    if not url or not url.strip():
        return None
    val = url.strip()
    lower_val = val.lower()
    if lower_val.startswith(("javascript:", "data:", "vbscript:", "file:")):
        raise ValueError("Invalid website format. Unsafe schemes are not permitted.")
    if not DOMAIN_REGEX.match(val):
        raise ValueError("Invalid website format. Must be a valid domain or URL (e.g. renergydynamics.com).")
    return val


def parse_date_only_value(v: Any) -> Optional[py_date]:
    if v is None or v == "":
        return None
    if isinstance(v, py_date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        trimmed = v.strip()
        if not trimmed:
            return None
        if "T" in trimmed:
            trimmed = trimmed.split("T")[0]
        elif " " in trimmed:
            trimmed = trimmed.split(" ")[0]
        try:
            return py_date.fromisoformat(trimmed)
        except Exception:
            raise ValueError(f"Invalid date format '{v}'. Expected YYYY-MM-DD.")
    return v


# =========================================================================
# 1. CRM USER HUB SCHEMAS
# =========================================================================

class CrmUserItem(BaseModel):
    userId: str
    username: str
    name: str
    email: str
    status: str
    crmAccess: bool
    crmRoleCode: Optional[str] = None
    crmRoleName: Optional[str] = None
    assignedLeadCount: int = 0
    createdAt: Optional[str] = None


class CrmUserListResponse(BaseModel):
    success: bool = True
    count: int
    users: List[CrmUserItem]


class CrmUserAccessRequest(BaseModel):
    enabled: Optional[bool] = None
    isEnabled: Optional[bool] = None
    roleCode: Optional[str] = None


class CrmUserRoleRequest(BaseModel):
    roleCode: str


class CrmRoleItem(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    moduleId: str
    isActive: bool = True


class CrmRoleListResponse(BaseModel):
    success: bool = True
    roles: List[CrmRoleItem]


# =========================================================================
# 2. ACCOUNT SCHEMAS
# =========================================================================

class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None

    @field_validator("website")
    @classmethod
    def validate_account_website(cls, v: Optional[str]) -> Optional[str]:
        return validate_and_normalize_website(v)


class AccountItem(BaseModel):
    id: str
    accountId: str
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    isActive: bool = True
    contactCount: int = 0
    leadCount: int = 0
    createdAt: Optional[str] = None


class AccountListResponse(BaseModel):
    success: bool = True
    count: int
    accounts: List[AccountItem]


class AccountDetailResponse(BaseModel):
    success: bool = True
    account: AccountItem
    contacts: List[Dict[str, Any]] = []
    leads: List[Dict[str, Any]] = []


# =========================================================================
# 3. CONTACT SCHEMAS
# =========================================================================

class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    accountId: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)
    mobileNumber: Optional[str] = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=100)


class ContactItem(BaseModel):
    id: str
    contactId: str
    accountId: Optional[str] = None
    accountName: Optional[str] = None
    name: str
    email: Optional[str] = None
    mobileNumber: Optional[str] = None
    designation: Optional[str] = None
    isActive: bool = True
    createdAt: Optional[str] = None


class ContactListResponse(BaseModel):
    success: bool = True
    count: int
    contacts: List[ContactItem]


class ContactDetailResponse(BaseModel):
    success: bool = True
    contact: ContactItem


# =========================================================================
# 4. LEAD SCHEMAS
# =========================================================================

ALLOWED_BUSINESS_AREAS = {"Biogas", "WWT"}
ALLOWED_REQUIREMENT_TYPES = {"Direct Product/Service", "Sample Testing", "Undetermined"}
ALLOWED_LEAD_SOURCES = {
    "Website", "Email Campaign", "Referral", "Partner", "Trade Show / Expo",
    "Cold Outreach", "Inbound Call", "Investor", "In-Person Meeting",
    "Social Media", "Other"
}
ALLOWED_LIFECYCLE_STATUSES = {"Open", "Qualified", "Disqualified"}
ALLOWED_CHANNELS = {
    "Email", "Phone / Call", "Mobile/Call", "WhatsApp",
    "In-Person Meeting", "Virtual Meeting", "Other"
}


class LeadCreate(BaseModel):
    leadName: str = Field(..., min_length=1, max_length=255)
    businessArea: str = Field(...)
    requirementType: str = Field(...)
    requirementSummary: Optional[str] = None
    requestedProductService: Optional[str] = Field(None, max_length=255)
    leadSource: Optional[str] = "Website"
    contactId: str = Field(...)
    accountId: Optional[str] = None
    assignedToUserId: Optional[str] = None
    websiteLink: Optional[str] = None
    location: Optional[str] = None
    siteName: Optional[str] = None
    communicationChannel: Optional[str] = "Email"
    remarks: Optional[str] = None
    nextFollowUpDate: Optional[py_date] = None
    nextFollowUpAction: Optional[str] = None

    @field_validator("leadName")
    @classmethod
    def validate_lead_name(cls, v: str) -> str:
        clean = (v or "").strip()
        if not clean:
            raise ValueError("Lead Title / Name is mandatory and cannot be empty.")
        return clean

    @field_validator("businessArea")
    @classmethod
    def validate_business_area(cls, v: str) -> str:
        clean = (v or "").strip()
        if clean not in ALLOWED_BUSINESS_AREAS:
            raise ValueError(f"Invalid businessArea '{v}'. Must be one of: {sorted(ALLOWED_BUSINESS_AREAS)}")
        return clean

    @field_validator("requirementType")
    @classmethod
    def validate_req_type(cls, v: str) -> str:
        clean = (v or "").strip()
        if clean not in ALLOWED_REQUIREMENT_TYPES:
            raise ValueError(f"Invalid requirementType '{v}'. Must be one of: {sorted(ALLOWED_REQUIREMENT_TYPES)}")
        return clean

    @field_validator("leadSource")
    @classmethod
    def validate_lead_source(cls, v: Optional[str]) -> str:
        if not v:
            return "Website"
        clean = v.strip()
        mapping = {
            "Cold Call": "Cold Outreach",
            "Partner / Referral": "Partner",
            "Website Enquiry": "Website",
        }
        mapped = mapping.get(clean, clean)
        if mapped not in ALLOWED_LEAD_SOURCES:
            raise ValueError(f"Invalid leadSource '{v}'. Must be one of: {sorted(ALLOWED_LEAD_SOURCES)}")
        return mapped

    @field_validator("websiteLink")
    @classmethod
    def validate_lead_website_link(cls, v: Optional[str]) -> Optional[str]:
        return validate_and_normalize_website(v)

    @field_validator("nextFollowUpDate", mode="before")
    @classmethod
    def validate_next_follow_up_date(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)


class LeadUpdate(BaseModel):
    leadName: Optional[str] = None
    businessArea: Optional[str] = None
    requirementType: Optional[str] = None
    requirementSummary: Optional[str] = None
    requestedProductService: Optional[str] = None
    leadSource: Optional[str] = None
    contactId: Optional[str] = None
    accountId: Optional[str] = None
    assignedToUserId: Optional[str] = None
    websiteLink: Optional[str] = None
    location: Optional[str] = None
    siteName: Optional[str] = None
    communicationChannel: Optional[str] = None
    remarks: Optional[str] = None
    nextFollowUpDate: Optional[py_date] = None
    nextFollowUpAction: Optional[str] = None
    lifecycleStatus: Optional[str] = None

    @field_validator("leadName")
    @classmethod
    def validate_lead_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("Lead Title / Name cannot be empty.")
            return clean
        return None

    @field_validator("businessArea")
    @classmethod
    def validate_business_area(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if clean not in ALLOWED_BUSINESS_AREAS:
            raise ValueError(f"Invalid businessArea '{v}'. Must be one of: {sorted(ALLOWED_BUSINESS_AREAS)}")
        return clean

    @field_validator("requirementType")
    @classmethod
    def validate_req_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if clean not in ALLOWED_REQUIREMENT_TYPES:
            raise ValueError(f"Invalid requirementType '{v}'. Must be one of: {sorted(ALLOWED_REQUIREMENT_TYPES)}")
        return clean

    @field_validator("leadSource")
    @classmethod
    def validate_lead_source(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        mapping = {
            "Cold Call": "Cold Outreach",
            "Partner / Referral": "Partner",
            "Website Enquiry": "Website",
        }
        mapped = mapping.get(clean, clean)
        if mapped not in ALLOWED_LEAD_SOURCES:
            raise ValueError(f"Invalid leadSource '{v}'. Must be one of: {sorted(ALLOWED_LEAD_SOURCES)}")
        return mapped

    @field_validator("websiteLink")
    @classmethod
    def validate_lead_website_link(cls, v: Optional[str]) -> Optional[str]:
        return validate_and_normalize_website(v)

    @field_validator("lifecycleStatus")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if clean not in ALLOWED_LIFECYCLE_STATUSES:
            raise ValueError(f"Invalid lifecycleStatus '{v}'. Must be one of: {sorted(ALLOWED_LIFECYCLE_STATUSES)}")
        return clean

    @field_validator("nextFollowUpDate", mode="before")
    @classmethod
    def validate_next_follow_up_date(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)


class LeadStatusTransitionRequest(BaseModel):
    status: str = Field(...)
    remarks: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean = (v or "").strip()
        if clean not in ALLOWED_LIFECYCLE_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of: {sorted(ALLOWED_LIFECYCLE_STATUSES)}")
        return clean


class LeadAccountSummary(BaseModel):
    id: str
    accountId: str
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class LeadContactSummary(BaseModel):
    id: str
    contactId: str
    name: str
    designation: Optional[str] = None
    email: Optional[str] = None
    mobileNumber: Optional[str] = None
    accountId: Optional[str] = None
    accountName: Optional[str] = None


class LeadUserSummary(BaseModel):
    id: str
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None


class LeadItem(BaseModel):
    id: str
    leadId: str
    leadName: str
    businessArea: str
    requirementType: str
    requirementSummary: Optional[str] = None
    requestedProductService: Optional[str] = None
    leadSource: str
    lifecycleStatus: str
    communicationChannel: Optional[str] = None
    remarks: Optional[str] = None
    nextFollowUpDate: Optional[str] = None
    nextFollowUpAction: Optional[str] = None
    lastConnectedDate: Optional[str] = None
    websiteLink: Optional[str] = None
    location: Optional[str] = None
    siteName: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    accountId: Optional[str] = None
    accountName: Optional[str] = None
    contactId: Optional[str] = None
    contactName: Optional[str] = None
    contactEmail: Optional[str] = None
    contactPhone: Optional[str] = None
    assignedToUserId: Optional[str] = None
    assignedToName: Optional[str] = None
    assignedToEmail: Optional[str] = None
    createdById: Optional[str] = None
    createdByName: Optional[str] = None
    account: Optional[LeadAccountSummary] = None
    contact: Optional[LeadContactSummary] = None
    assignedTo: Optional[LeadUserSummary] = None
    createdBy: Optional[LeadUserSummary] = None



class LeadListResponse(BaseModel):
    success: bool = True
    count: int
    totalCount: int
    page: int
    pageSize: int
    totalPages: int
    leads: List[LeadItem]


class LeadDetailResponse(BaseModel):
    success: bool = True
    lead: LeadItem


# =========================================================================
# 5. COMMUNICATION SCHEMAS
# =========================================================================

class CommunicationCreate(BaseModel):
    channel: str = Field(...)
    eventType: str = Field(..., min_length=1)
    date: Optional[datetime] = None
    summary: Optional[str] = None
    outcome: Optional[str] = None
    nextAction: Optional[str] = None
    followUpDate: Optional[py_date] = None

    @field_validator("followUpDate", mode="before")
    @classmethod
    def validate_comm_follow_up_date(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)


class CommunicationItem(BaseModel):
    id: str
    communicationId: str
    leadId: str
    communicationDate: str
    channel: str
    eventType: str
    summary: Optional[str] = None
    outcome: Optional[str] = None
    nextAction: Optional[str] = None
    followUpDate: Optional[str] = None
    createdById: Optional[str] = None
    createdByName: Optional[str] = None
    createdAt: Optional[str] = None


class CommunicationListResponse(BaseModel):
    success: bool = True
    count: int
    communications: List[CommunicationItem]


# =========================================================================
# 6. DASHBOARD METRICS SCHEMA
# =========================================================================

class DashboardMetricsResponse(BaseModel):
    success: bool = True
    totalLeads: int
    openLeads: int
    qualifiedLeads: int
    disqualifiedLeads: int
    myLeads: int
    followUpsDue: int
    overdueFollowUps: int
