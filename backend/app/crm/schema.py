import re
from typing import Optional, List, Dict, Any
from datetime import datetime, date as py_date
from pydantic import BaseModel, Field, field_validator, model_validator


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
    phone: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
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


class CrmUserAssignRequest(BaseModel):
    userId: str
    roleCode: str
    isActive: bool = True


class AvailableUserItem(BaseModel):
    id: str
    username: str
    name: str
    email: str
    phone: Optional[str] = None
    status: str = "active"
    designation: Optional[str] = None
    department: Optional[str] = None


class AvailableUserListResponse(BaseModel):
    success: bool = True
    count: int
    users: List[AvailableUserItem]


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
    siteName: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    businessArea: Optional[str] = Field(None, description="Biogas or WWT")
    country: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    billingAddress: Optional[str] = None
    shippingAddress: Optional[str] = None
    gstNumber: Optional[str] = Field(None, max_length=30)
    panNumber: Optional[str] = Field(None, max_length=20)
    parentAccountId: Optional[str] = None
    confirmDuplicate: bool = False

    @field_validator("businessArea")
    @classmethod
    def validate_account_business_area(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        clean = v.strip()
        if clean not in ("Biogas", "WWT"):
            raise ValueError("Business Area must be 'Biogas' or 'WWT'.")
        return clean

    @field_validator("name")
    @classmethod
    def validate_account_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Account name cannot be empty.")
        return clean

    @field_validator("website")
    @classmethod
    def validate_account_website(cls, v: Optional[str]) -> Optional[str]:
        return validate_and_normalize_website(v)

    @field_validator("email")
    @classmethod
    def validate_account_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Enter a valid company email address.")
        return clean


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    siteName: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    businessArea: Optional[str] = Field(None, description="Biogas or WWT")
    country: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    billingAddress: Optional[str] = None
    shippingAddress: Optional[str] = None
    gstNumber: Optional[str] = Field(None, max_length=30)
    panNumber: Optional[str] = Field(None, max_length=20)
    parentAccountId: Optional[str] = None
    isActive: Optional[bool] = None
    confirmDuplicate: bool = False

    @field_validator("businessArea")
    @classmethod
    def validate_account_business_area(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        clean = v.strip()
        if clean not in ("Biogas", "WWT"):
            raise ValueError("Business Area must be 'Biogas' or 'WWT'.")
        return clean

    @field_validator("name")
    @classmethod
    def validate_account_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            raise ValueError("Account name cannot be empty.")
        return clean

    @field_validator("website")
    @classmethod
    def validate_account_website(cls, v: Optional[str]) -> Optional[str]:
        return validate_and_normalize_website(v)

    @field_validator("email")
    @classmethod
    def validate_account_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Enter a valid company email address.")
        return clean


class AccountItem(BaseModel):
    id: str
    accountId: str
    name: str
    siteName: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    businessArea: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    billingAddress: Optional[str] = None
    shippingAddress: Optional[str] = None
    gstNumber: Optional[str] = None
    panNumber: Optional[str] = None
    parentAccountId: Optional[str] = None
    parentAccount: Optional[Dict[str, Any]] = None
    subAccounts: Optional[List[Dict[str, Any]]] = None
    createdById: Optional[str] = None
    updatedById: Optional[str] = None
    isActive: bool = True
    contactCount: int = 0
    leadCount: int = 0
    opportunityCount: int = 0
    contacts: Optional[List[Dict[str, Any]]] = None
    leads: Optional[List[Dict[str, Any]]] = None
    opportunities: Optional[List[Dict[str, Any]]] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class AccountListResponse(BaseModel):
    success: bool = True
    count: int
    total: Optional[int] = None
    accounts: List[AccountItem]


class AccountDetailResponse(BaseModel):
    success: bool = True
    account: AccountItem
    contacts: List[Dict[str, Any]] = []
    leads: List[Dict[str, Any]] = []
    opportunities: List[Dict[str, Any]] = []


class AccountMatchItem(BaseModel):
    id: str
    accountId: str
    name: str
    siteName: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    matchReasons: List[str] = []
    contactCount: int = 0
    leadCount: int = 0
    opportunityCount: int = 0


class AccountMatchResponse(BaseModel):
    success: bool = True
    count: int
    matches: List[AccountMatchItem]


# =========================================================================
# 3. CONTACT SCHEMAS
# =========================================================================

class ContactCreate(BaseModel):
    firstName: Optional[str] = Field(None, max_length=100)
    lastName: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=255)
    accountId: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)
    mobileNumber: Optional[str] = Field(None, max_length=50)
    whatsappNumber: Optional[str] = Field(None, max_length=30)
    designation: Optional[str] = Field(None, max_length=100)
    isPrimary: bool = False
    confirmDuplicate: bool = False

    @model_validator(mode="after")
    def compute_contact_name(self) -> "ContactCreate":
        fn = (self.firstName or "").strip()
        ln = (self.lastName or "").strip()
        computed = f"{fn} {ln}".strip()
        if computed:
            self.name = computed
        elif self.name and self.name.strip():
            self.name = self.name.strip()
            parts = self.name.split(None, 1)
            self.firstName = parts[0]
            self.lastName = parts[1] if len(parts) > 1 else None
        else:
            raise ValueError("At least first name or last name is required.")
        return self

    @field_validator("email")
    @classmethod
    def validate_contact_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Enter a valid contact email address.")
        return clean

    @field_validator("mobileNumber")
    @classmethod
    def validate_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        return v.strip()


class ContactUpdate(BaseModel):
    firstName: Optional[str] = Field(None, max_length=100)
    lastName: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    accountId: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)
    mobileNumber: Optional[str] = Field(None, max_length=50)
    whatsappNumber: Optional[str] = Field(None, max_length=30)
    designation: Optional[str] = Field(None, max_length=100)
    isPrimary: Optional[bool] = None
    isActive: Optional[bool] = None
    confirmDuplicate: bool = False

    @field_validator("name")
    @classmethod
    def validate_contact_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            raise ValueError("Contact name cannot be empty.")
        return clean

    @field_validator("email")
    @classmethod
    def validate_contact_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Enter a valid contact email address.")
        return clean

    @field_validator("mobileNumber")
    @classmethod
    def validate_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        return v.strip()


class ContactItem(BaseModel):
    id: str
    contactId: str
    accountId: Optional[str] = None
    accountName: Optional[str] = None
    account: Optional[Dict[str, Any]] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    name: str
    email: Optional[str] = None
    mobileNumber: Optional[str] = None
    whatsappNumber: Optional[str] = None
    designation: Optional[str] = None
    isPrimary: bool = False
    createdById: Optional[str] = None
    updatedById: Optional[str] = None
    isActive: bool = True
    opportunityCount: int = 0
    opportunities: Optional[List[Dict[str, Any]]] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class ContactListResponse(BaseModel):
    success: bool = True
    count: int
    total: Optional[int] = None
    contacts: List[ContactItem]


class ContactDetailResponse(BaseModel):
    success: bool = True
    contact: ContactItem
    leads: List[Dict[str, Any]] = []
    opportunities: List[Dict[str, Any]] = []


class ContactMatchItem(BaseModel):
    id: str
    contactId: str
    accountId: Optional[str] = None
    accountName: Optional[str] = None
    name: str
    email: Optional[str] = None
    mobileNumber: Optional[str] = None
    designation: Optional[str] = None
    matchReasons: List[str] = []


class ContactMatchResponse(BaseModel):
    success: bool = True
    count: int
    matches: List[ContactMatchItem]


# =========================================================================
# 4. LEAD SCHEMAS
# =========================================================================

ALLOWED_BUSINESS_AREAS = {"Biogas", "WWT"}
ALLOWED_REQUIREMENT_TYPES = {"Consulting", "Sample Testing", "Product"}
CANONICAL_LEAD_SOURCES = [
    "Website",
    "Email Received",
    "Email Campaign",
    "Cold Outreach",
    "Inbound Call",
    "In-Person Meeting",
    "Investor",
    "Partner",
    "Referral",
    "Social Media",
    "Trade Show / Expo",
    "Other",
]
ALLOWED_LEAD_SOURCES = set(CANONICAL_LEAD_SOURCES)
ACTIVE_LEAD_SOURCES = ALLOWED_LEAD_SOURCES
HISTORICAL_LEAD_SOURCES = set()

ALLOWED_LEAD_NURTURING_STATUSES = {
    "New",
    "Contacted",
    "In Discussion",
    "Dormant",
    "Disqualified",
}
ALLOWED_LIFECYCLE_STATUSES = ALLOWED_LEAD_NURTURING_STATUSES | {"Qualified"}
DEFAULT_LIFECYCLE_STATUS = "New"
ALLOWED_CHANNELS = {
    "Email", "Phone / Call", "Mobile/Call", "WhatsApp",
    "In-Person Meeting", "Virtual Meeting", "Other"
}
ALLOWED_CONTACT_METHODS = {"Email", "Phone", "WhatsApp", "Meeting"}
ALLOWED_RATINGS = {"Hot", "Warm", "Cold"}
ALLOWED_CLIENT_STATUSES = {"New", "Existing"}


def normalize_and_validate_req_types(
    req_types: Optional[List[str]] = None,
    legacy_single: Optional[str] = None
) -> List[str]:
    selected = []
    if req_types is not None:
        if not isinstance(req_types, list):
            req_types = [req_types]
        for t in req_types:
            if not t:
                continue
            clean = str(t).strip()
            # Map legacy values and synonyms
            if clean in ("Direct Product/Service", "Products", "product", "products"):
                clean = "Product"
            elif clean in ("Undetermined", "Consultancy", "consultancy", "consulting"):
                clean = "Consulting"
            elif clean in ("Sample testing", "sample testing", "Testing"):
                clean = "Sample Testing"

            if clean not in ALLOWED_REQUIREMENT_TYPES:
                raise ValueError(f"Invalid requirement type '{t}'. Must be one of: {sorted(ALLOWED_REQUIREMENT_TYPES)}")
            if clean not in selected:
                selected.append(clean)

    if not selected and legacy_single:
        clean = str(legacy_single).strip()
        if clean in ("Direct Product/Service", "Products", "product", "products"):
            clean = "Product"
        elif clean in ("Undetermined", "Consultancy", "consultancy", "consulting"):
            clean = "Consulting"
        elif clean in ("Sample testing", "sample testing", "Testing"):
            clean = "Sample Testing"

        if clean not in ALLOWED_REQUIREMENT_TYPES:
            raise ValueError(f"Invalid requirement type '{legacy_single}'. Must be one of: {sorted(ALLOWED_REQUIREMENT_TYPES)}")
        selected.append(clean)

    return selected


class LeadCreate(BaseModel):
    # Idempotency Key (Optional)
    clientRequestId: Optional[str] = None

    # Topic / Title (Optional)
    leadName: Optional[str] = None

    # Section 1 - Contact
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    jobTitle: Optional[str] = None
    businessPhone: Optional[str] = None
    mobilePhone: Optional[str] = None
    contactEmail: Optional[str] = None

    # Section 2 - Company
    companyName: Optional[str] = None
    websiteLink: Optional[str] = None
    location: Optional[str] = None
    siteName: Optional[str] = None
    communicationChannel: Optional[str] = "Email"
    connectedDate: Optional[py_date] = None
    companyEmail: Optional[str] = None

    # Section 3 - Additional Lead Information
    leadSource: Optional[str] = "Website"
    rating: Optional[str] = None
    clientStatus: Optional[str] = "New"
    assignedToUserId: Optional[str] = None

    # Section 4 - Description & Business Information
    description: Optional[str] = None
    industry: Optional[str] = None
    numberOfEmployees: Optional[int] = None
    currency: Optional[str] = "INR"
    businessArea: Optional[str] = "Biogas"
    requirementTypes: Optional[List[str]] = None
    requirementType: Optional[str] = None
    requirementSummary: Optional[str] = None
    requestedProductService: Optional[str] = None

    # Section 5 - Contact Method
    contactMethods: Optional[List[str]] = Field(default_factory=list)
    preferredContactMethod: Optional[str] = None

    # Optional existing Contact and Account relationships (not required at creation time)
    contactId: Optional[str] = None
    accountId: Optional[str] = None
    additionalContactIds: Optional[List[str]] = Field(default_factory=list)
    remarks: Optional[str] = None
    nextFollowUpDate: Optional[py_date] = None
    nextFollowUpAction: Optional[str] = None
    lifecycleStatus: Optional[str] = "New"

    @model_validator(mode="before")
    @classmethod
    def process_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Aliases support for Section 1 & 2
            if "topic" in data and not data.get("leadName"):
                data["leadName"] = data["topic"]
            if "company" in data and not data.get("companyName"):
                data["companyName"] = data["company"]
            if "website" in data and not data.get("websiteLink"):
                data["websiteLink"] = data["website"]
            if "clientLocation" in data and not data.get("location"):
                data["location"] = data["clientLocation"]
            if "email" in data and not data.get("contactEmail"):
                data["contactEmail"] = data["email"]
            if "status" in data and data["status"] in ("New", "Existing") and not data.get("clientStatus"):
                data["clientStatus"] = data["status"]

            # Lead title optional: empty string becomes None
            if "leadName" in data and data["leadName"] is not None:
                cleaned = str(data["leadName"]).strip()
                data["leadName"] = cleaned if cleaned else None

            # Topic / Title or Company Name validation (at least one must be provided)
            has_title = bool(data.get("leadName") and str(data.get("leadName")).strip())
            has_company = bool(data.get("companyName") and str(data.get("companyName")).strip())
            has_existing_rel = bool(data.get("contactId") or data.get("accountId"))
            if not has_title and not has_company and not has_existing_rel:
                raise ValueError("At least one identifying title must be provided: either Topic/Title or Company Name.")

            # Multi-select requirement types (Optional during initial lead creation)
            types = data.get("requirementTypes")
            single = data.get("requirementType")
            normalized = normalize_and_validate_req_types(types, single)
            data["requirementTypes"] = normalized
            data["requirementType"] = normalized[0] if normalized else None

            # Contact methods validation
            cms = data.get("contactMethods")
            if "contactMethods" in data and (cms is None or len(cms) == 0):
                raise ValueError("At least one contact method must be selected.")
            elif cms:
                clean_cms = []
                for m in cms:
                    if m and str(m).strip() in ALLOWED_CONTACT_METHODS:
                        clean_m = str(m).strip()
                        if clean_m not in clean_cms:
                            clean_cms.append(clean_m)
                if not clean_cms:
                    raise ValueError(f"Invalid contact methods. Must be chosen from: {sorted(ALLOWED_CONTACT_METHODS)}")
                data["contactMethods"] = clean_cms
            else:
                data["contactMethods"] = ["Email"]

            # Preferred contact method must be one of selected contact methods
            pref = data.get("preferredContactMethod")
            selected_cms = data.get("contactMethods") or ["Email"]
            if pref:
                clean_pref = str(pref).strip()
                if clean_pref not in ALLOWED_CONTACT_METHODS:
                    raise ValueError(f"Invalid preferredContactMethod '{pref}'. Must be one of: {sorted(ALLOWED_CONTACT_METHODS)}")
                if selected_cms and clean_pref not in selected_cms:
                    raise ValueError(f"Preferred contact method '{clean_pref}' must be one of the selected contact methods.")
                data["preferredContactMethod"] = clean_pref
            else:
                data["preferredContactMethod"] = selected_cms[0] if selected_cms else None

            # Business area default
            if not data.get("businessArea"):
                data["businessArea"] = "Biogas"
        return data

    @field_validator("businessArea")
    @classmethod
    def validate_business_area(cls, v: Optional[str]) -> str:
        clean = (v or "Biogas").strip()
        if clean not in ALLOWED_BUSINESS_AREAS:
            raise ValueError(f"Invalid businessArea '{v}'. Must be one of: {sorted(ALLOWED_BUSINESS_AREAS)}")
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
            raise ValueError(f"Invalid leadSource '{v}'. Must be one of: {CANONICAL_LEAD_SOURCES}")
        return mapped

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = v.strip()
        if clean not in ALLOWED_RATINGS:
            raise ValueError(f"Invalid rating '{v}'. Must be one of: {sorted(ALLOWED_RATINGS)}")
        return clean

    @field_validator("clientStatus")
    @classmethod
    def validate_client_status(cls, v: Optional[str]) -> str:
        if not v:
            return "New"
        clean = v.strip()
        if clean not in ALLOWED_CLIENT_STATUSES:
            raise ValueError(f"Invalid clientStatus '{v}'. Must be 'New' or 'Existing'.")
        return clean

    @field_validator("numberOfEmployees")
    @classmethod
    def validate_num_employees(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Number of employees must be a non-negative integer.")
        return v

    @field_validator("connectedDate", mode="before")
    @classmethod
    def validate_lead_connected_date(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)

    @field_validator("websiteLink")
    @classmethod
    def validate_lead_website_link(cls, v: Optional[str]) -> Optional[str]:
        return validate_and_normalize_website(v)

    @field_validator("nextFollowUpDate", mode="before")
    @classmethod
    def validate_next_follow_up_date(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)

    @field_validator("lifecycleStatus")
    @classmethod
    def validate_create_lifecycle_status(cls, v: Optional[str]) -> str:
        if not v:
            return "New"
        clean = v.strip()
        if clean not in ALLOWED_LIFECYCLE_STATUSES:
            raise ValueError(f"Invalid lifecycleStatus '{v}'. Must be one of: {sorted(ALLOWED_LIFECYCLE_STATUSES)}")
        return clean


class LeadUnqualifyRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Mandatory disqualification reason")


class LeadUpdate(BaseModel):
    # Topic / Title
    leadName: Optional[str] = None
    disqualificationReason: Optional[str] = None

    # Section 1 - Contact
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    jobTitle: Optional[str] = None
    businessPhone: Optional[str] = None
    mobilePhone: Optional[str] = None
    contactEmail: Optional[str] = None

    # Section 2 - Company
    companyName: Optional[str] = None
    websiteLink: Optional[str] = None
    location: Optional[str] = None
    siteName: Optional[str] = None
    communicationChannel: Optional[str] = None
    connectedDate: Optional[py_date] = None
    companyEmail: Optional[str] = None

    # Section 3 - Additional Lead Information
    leadSource: Optional[str] = None
    rating: Optional[str] = None
    clientStatus: Optional[str] = None
    assignedToUserId: Optional[str] = None

    # Section 4 - Description & Business Information
    description: Optional[str] = None
    industry: Optional[str] = None
    numberOfEmployees: Optional[int] = None
    currency: Optional[str] = None
    businessArea: Optional[str] = None
    requirementTypes: Optional[List[str]] = None
    requirementType: Optional[str] = None
    requirementSummary: Optional[str] = None
    requestedProductService: Optional[str] = None

    # Section 5 - Contact Method
    contactMethods: Optional[List[str]] = None
    preferredContactMethod: Optional[str] = None

    contactId: Optional[str] = None
    accountId: Optional[str] = None
    additionalContactIds: Optional[List[str]] = None
    remarks: Optional[str] = None
    nextFollowUpDate: Optional[py_date] = None
    nextFollowUpAction: Optional[str] = None
    lifecycleStatus: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def process_update_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "topic" in data and not data.get("leadName"):
                data["leadName"] = data["topic"]
            if "company" in data and not data.get("companyName"):
                data["companyName"] = data["company"]
            if "website" in data and not data.get("websiteLink"):
                data["websiteLink"] = data["website"]
            if "clientLocation" in data and not data.get("location"):
                data["location"] = data["clientLocation"]
            if "email" in data and not data.get("contactEmail"):
                data["contactEmail"] = data["email"]
            if "status" in data and data["status"] in ("New", "Existing") and not data.get("clientStatus"):
                data["clientStatus"] = data["status"]

            if "leadName" in data and data["leadName"] is not None:
                cleaned = str(data["leadName"]).strip()
                data["leadName"] = cleaned if cleaned else None

            types = data.get("requirementTypes")
            single = data.get("requirementType")
            if types is not None or single is not None:
                normalized = normalize_and_validate_req_types(types, single)
                data["requirementTypes"] = normalized
                data["requirementType"] = normalized[0]

            cms = data.get("contactMethods")
            if cms is not None:
                clean_cms = []
                for m in cms:
                    if m and str(m).strip() in ALLOWED_CONTACT_METHODS:
                        clean_m = str(m).strip()
                        if clean_m not in clean_cms:
                            clean_cms.append(clean_m)
                data["contactMethods"] = clean_cms

            pref = data.get("preferredContactMethod")
            if pref:
                clean_pref = str(pref).strip()
                if clean_pref not in ALLOWED_CONTACT_METHODS:
                    raise ValueError(f"Invalid preferredContactMethod '{pref}'. Must be one of: {sorted(ALLOWED_CONTACT_METHODS)}")
                data["preferredContactMethod"] = clean_pref
        return data

    @field_validator("businessArea")
    @classmethod
    def validate_business_area(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if clean not in ALLOWED_BUSINESS_AREAS:
            raise ValueError(f"Invalid businessArea '{v}'. Must be one of: {sorted(ALLOWED_BUSINESS_AREAS)}")
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
            raise ValueError(f"Invalid leadSource '{v}'. Must be one of: {CANONICAL_LEAD_SOURCES}")
        return mapped

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = v.strip()
        if clean not in ALLOWED_RATINGS:
            raise ValueError(f"Invalid rating '{v}'. Must be one of: {sorted(ALLOWED_RATINGS)}")
        return clean

    @field_validator("clientStatus")
    @classmethod
    def validate_client_status(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = v.strip()
        if clean not in ALLOWED_CLIENT_STATUSES:
            raise ValueError(f"Invalid clientStatus '{v}'. Must be 'New' or 'Existing'.")
        return clean

    @field_validator("numberOfEmployees")
    @classmethod
    def validate_num_employees(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Number of employees must be a non-negative integer.")
        return v

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

    @field_validator("connectedDate", mode="before")
    @classmethod
    def validate_update_connected_date(cls, v: Any) -> Optional[py_date]:
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
    accountId: Optional[str] = None
    name: Optional[str] = "Unnamed Account"
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class LeadContactSummary(BaseModel):
    id: str
    contactId: Optional[str] = None
    name: Optional[str] = "Unnamed Contact"
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
    leadName: Optional[str] = None
    displayName: Optional[str] = "Untitled Lead"
    businessArea: Optional[str] = "Biogas"
    requirementType: Optional[str] = None
    requirementTypes: List[str] = []
    requirementSummary: Optional[str] = None
    requestedProductService: Optional[str] = None
    leadSource: Optional[str] = "Website"
    lifecycleStatus: Optional[str] = "New"
    communicationChannel: Optional[str] = None
    remarks: Optional[str] = None
    connectedDate: Optional[str] = None
    nextFollowUpDate: Optional[str] = None
    nextFollowUpAction: Optional[str] = None
    lastConnectedDate: Optional[str] = None
    websiteLink: Optional[str] = None
    location: Optional[str] = None
    siteName: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    # Section 1 Direct Contact Fields
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    jobTitle: Optional[str] = None
    businessPhone: Optional[str] = None
    mobilePhone: Optional[str] = None
    contactEmail: Optional[str] = None

    # Section 2 Direct Company Fields
    companyName: Optional[str] = None
    companyEmail: Optional[str] = None
    disqualificationReason: Optional[str] = None

    # Section 3 & 4 Fields
    rating: Optional[str] = None
    clientStatus: Optional[str] = "New"
    description: Optional[str] = None
    industry: Optional[str] = None
    numberOfEmployees: Optional[int] = None
    currency: Optional[str] = "INR"

    # Section 5 Contact Methods
    contactMethods: List[str] = []
    preferredContactMethod: Optional[str] = None

    # Foreign Keys & Linkages
    accountId: Optional[str] = None
    accountName: Optional[str] = None
    contactId: Optional[str] = None
    contactName: Optional[str] = None
    contactEmailRel: Optional[str] = None
    contactPhoneRel: Optional[str] = None
    additionalContacts: List[Dict[str, Any]] = []
    additionalContactIds: List[str] = []
    assignedToUserId: Optional[str] = None
    assignedToName: Optional[str] = None
    assignedToEmail: Optional[str] = None
    createdById: Optional[str] = None
    createdByName: Optional[str] = None
    account: Optional[LeadAccountSummary] = None
    contact: Optional[LeadContactSummary] = None
    assignedTo: Optional[LeadUserSummary] = None
    createdBy: Optional[LeadUserSummary] = None

    # Qualification Details
    opportunityId: Optional[str] = None
    opportunityName: Optional[str] = None
    opportunity: Optional[Dict[str, Any]] = None
    opportunities: List[Dict[str, Any]] = []
    isQualified: bool = False
    qualifiedAt: Optional[str] = None
    qualifiedById: Optional[str] = None
    qualifiedByName: Optional[str] = None
    convertedAt: Optional[str] = None
    convertedById: Optional[str] = None
    convertedByName: Optional[str] = None
    isConverted: bool = False


class LeadListResponse(BaseModel):
    success: bool = True
    count: int
    total: Optional[int] = None
    totalCount: int
    page: int
    pageSize: int
    totalPages: int
    leads: List[LeadItem]


class LeadDetailResponse(BaseModel):
    success: bool = True
    lead: LeadItem


# =========================================================================
# OPPORTUNITY & QUALIFICATION SCHEMAS
# =========================================================================

class LeadOpportunityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    accountId: Optional[str] = None
    contactId: Optional[str] = None
    originatingLeadId: Optional[str] = None
    status: Optional[str] = "Open"
    stage: Optional[str] = "Enquiry"
    lossReason: Optional[str] = None
    businessArea: Optional[str] = "Biogas"
    expectedCloseDate: Optional[str] = None
    currency: Optional[str] = "INR"
    estimatedValue: Optional[float] = None
    description: Optional[str] = None
    requirementSummary: Optional[str] = None
    requirementTypes: Optional[List[str]] = None
    assignedToUserId: Optional[str] = None
    subStatus: Optional[str] = None
    sub_status: Optional[str] = None

    @model_validator(mode="after")
    def validate_lead_opportunity_create(self) -> "LeadOpportunityCreate":
        if self.estimatedValue is not None and self.estimatedValue < 0:
            raise ValueError("Estimated amount cannot be negative.")

        canonical_stages = ["Enquiry", "Offer", "Negotiation", "Supply", "Payment", "Dormant"]
        stg = self.stage
        if stg and stg not in canonical_stages:
            raise ValueError(f"Invalid stage '{stg}'. Permitted stages are: {', '.join(canonical_stages)}")

        stat = (self.status or "Open").strip()
        if stat not in ("Open", "Won", "Lost"):
            raise ValueError(f"Invalid status '{stat}'. Permitted statuses are Open, Won, Lost.")

        return self


class OpportunityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    accountId: Optional[str] = None
    contactId: Optional[str] = None
    originatingLeadId: Optional[str] = None
    status: Optional[str] = "Open"
    stage: Optional[str] = "Enquiry"
    lossReason: Optional[str] = None
    wonReason: Optional[str] = None
    businessArea: Optional[str] = "Biogas"
    expectedCloseDate: Optional[str] = None
    currency: Optional[str] = "INR"
    estimatedValue: Optional[float] = None
    description: Optional[str] = None
    requirementSummary: Optional[str] = None
    requirementTypes: Optional[List[str]] = None
    assignedToUserId: Optional[str] = None
    subStatus: Optional[str] = None
    sub_status: Optional[str] = None

    @model_validator(mode="after")
    def validate_opportunity_create(self) -> "OpportunityCreate":
        if not (self.accountId and str(self.accountId).strip()) and not (self.contactId and str(self.contactId).strip()):
            raise ValueError("At least one primary relationship (Primary Account or Primary Contact) is required.")

        if self.estimatedValue is not None and self.estimatedValue < 0:
            raise ValueError("Estimated amount cannot be negative.")

        canonical_stages = ["Enquiry", "Offer", "Negotiation", "Supply", "Payment", "Dormant"]
        stg = self.stage
        if stg and stg not in canonical_stages:
            raise ValueError(f"Invalid stage '{stg}'. Permitted stages are: {', '.join(canonical_stages)}")

        stat = (self.status or "Open").strip()
        if stat not in ("Open", "Won", "Lost"):
            raise ValueError(f"Invalid status '{stat}'. Permitted statuses are Open, Won, Lost.")

        if stat == "Lost" and not (self.lossReason and str(self.lossReason).strip()):
            raise ValueError("Loss reason is mandatory when marking an opportunity as Lost.")
        if stat == "Won" and not (self.wonReason and str(self.wonReason).strip()):
            raise ValueError("Won reason is mandatory when marking an opportunity as Won.")

        return self


class OpportunityUpdate(BaseModel):
    name: Optional[str] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    lossReason: Optional[str] = None
    accountId: Optional[str] = None
    contactId: Optional[str] = None
    currency: Optional[str] = None
    estimatedValue: Optional[float] = None
    description: Optional[str] = None
    requirementSummary: Optional[str] = None
    requirementTypes: Optional[List[str]] = None
    assignedToUserId: Optional[str] = None
    subStatus: Optional[str] = None
    sub_status: Optional[str] = None


class OpportunityQuotationItem(BaseModel):
    id: str
    quotationNumber: str
    opportunityId: str
    revisionNumber: int = 1
    version: str = "v1"
    isActive: bool = True
    title: Optional[str] = None
    status: str = "Draft"
    amount: float = 0.0
    currency: str = "INR"
    quotationDate: Optional[str] = None
    validUntilDate: Optional[str] = None
    termsAndConditions: Optional[str] = None
    notes: Optional[str] = None
    rejectionReason: Optional[str] = None
    fileId: Optional[str] = None
    documentName: Optional[str] = None
    approvedById: Optional[str] = None
    approvedByName: Optional[str] = None
    approvedAt: Optional[str] = None
    sentMethod: Optional[str] = None
    sentTo: Optional[str] = None
    sentAt: Optional[str] = None
    sentById: Optional[str] = None
    sentByName: Optional[str] = None
    sendingEvidence: Optional[str] = None
    createdById: Optional[str] = None
    createdByName: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class OpportunityItem(BaseModel):
    id: str
    opportunityId: str
    name: str
    accountId: Optional[str] = None
    accountName: Optional[str] = None
    contactId: Optional[str] = None
    contactName: Optional[str] = None
    account: Optional[Dict[str, Any]] = None
    contact: Optional[Dict[str, Any]] = None
    originatingLead: Optional[Dict[str, Any]] = None
    originatingLeadId: Optional[str] = None
    originatingLeadNumber: Optional[str] = None
    status: str = "Open"
    stage: str = "Qualify"
    lossReason: Optional[str] = None
    wonReason: Optional[str] = None
    closedById: Optional[str] = None
    closedByName: Optional[str] = None
    reopenedAt: Optional[str] = None
    reopenedById: Optional[str] = None
    reopenedByName: Optional[str] = None
    subStatus: Optional[str] = None
    sub_status: Optional[str] = None
    businessArea: Optional[str] = "Biogas"
    expectedCloseDate: Optional[str] = None
    actualCloseDate: Optional[str] = None
    currency: str = "INR"
    estimatedValue: Optional[float] = None
    description: Optional[str] = None
    requirementSummary: Optional[str] = None
    requirementTypes: List[str] = []
    assignedToUserId: Optional[str] = None
    assignedToName: Optional[str] = None
    createdById: Optional[str] = None
    createdByName: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    milestoneCount: int = 0
    workstreamCount: int = 0
    quotationCount: int = 0
    activeQuotation: Optional[OpportunityQuotationItem] = None
    hasQuotationMismatch: bool = False
    activeQuotationAmount: Optional[float] = None
    activeQuotationCurrency: Optional[str] = None
    canReopen: bool = False


class OpportunityListResponse(BaseModel):
    success: bool = True
    count: int
    totalCount: Optional[int] = None
    opportunities: List[OpportunityItem]


class OpportunityDetailResponse(BaseModel):
    success: bool = True
    opportunity: OpportunityItem


class OpportunityStageTransitionRequest(BaseModel):
    newStage: str = Field(..., description="Target stage: Enquiry, Offer, Negotiation, Supply, Payment, Dormant")
    status: Optional[str] = Field(None, description="Optional target status: Open, Won, or Lost")
    lossReason: Optional[str] = Field(None, description="Required when status is Lost")
    wonReason: Optional[str] = Field(None, description="Required when status is Won")
    actualCloseDate: Optional[py_date] = None
    remarks: Optional[str] = None

    @field_validator("actualCloseDate", mode="before")
    @classmethod
    def validate_actual_close_date(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)

    @model_validator(mode="after")
    def validate_transition(self) -> "OpportunityStageTransitionRequest":
        canonical_stages = ["Enquiry", "Offer", "Negotiation", "Supply", "Payment", "Dormant"]
        stg = self.newStage

        if stg not in canonical_stages:
            raise ValueError(f"Invalid stage '{stg}'. Permitted stages are: {', '.join(canonical_stages)}")

        stat = self.status.strip() if self.status else None
        if stat and stat not in ("Open", "Won", "Lost"):
            raise ValueError(f"Invalid status '{stat}'. Permitted statuses are Open, Won, Lost.")

        if stat == "Lost" and not (self.lossReason and self.lossReason.strip()):
            raise ValueError("Loss reason is mandatory when marking an opportunity as Lost.")
        if stat == "Won" and not (self.wonReason and self.wonReason.strip()):
            raise ValueError("Won reason is mandatory when marking an opportunity as Won.")

        return self


class OpportunityUpdateRequest(BaseModel):
    name: Optional[str] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    lossReason: Optional[str] = None
    wonReason: Optional[str] = None
    accountId: Optional[str] = None
    contactId: Optional[str] = None
    currency: Optional[str] = None
    estimatedValue: Optional[float] = None
    estimatedValueChangeReason: Optional[str] = None
    expectedCloseDate: Optional[py_date] = None
    actualCloseDate: Optional[py_date] = None
    businessArea: Optional[str] = None
    requirementTypes: Optional[List[str]] = None
    description: Optional[str] = None
    assignedToUserId: Optional[str] = None
    subStatus: Optional[str] = None
    sub_status: Optional[str] = None

    @field_validator("expectedCloseDate", mode="before")
    @classmethod
    def validate_expected_close_date(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)

    @field_validator("actualCloseDate", mode="before")
    @classmethod
    def validate_actual_close_date(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)

    @model_validator(mode="after")
    def validate_update(self) -> "OpportunityUpdateRequest":
        if self.estimatedValue is not None and self.estimatedValue < 0:
            raise ValueError("Estimated value cannot be negative.")

        canonical_stages = ["Enquiry", "Offer", "Negotiation", "Supply", "Payment", "Dormant"]
        if self.stage:
            if self.stage not in canonical_stages:
                raise ValueError(f"Invalid stage '{self.stage}'. Permitted stages are: {', '.join(canonical_stages)}")

        if self.status:
            stat = self.status.strip()
            if stat not in ("Open", "Won", "Lost"):
                raise ValueError(f"Invalid status '{stat}'. Permitted statuses are Open, Won, Lost.")
            if stat == "Lost" and not (self.lossReason and str(self.lossReason).strip()):
                raise ValueError("Loss reason is mandatory when marking an opportunity as Lost.")

        return self


class PipelineStageMetrics(BaseModel):
    stage: str
    count: int
    totalValue: float


class OpportunityPipelineSummaryResponse(BaseModel):
    success: bool = True
    totalCount: int
    totalOpenValue: float
    byStage: List[PipelineStageMetrics]
    byStatus: Dict[str, int]


# Workstream & Routing Schemas
class WorkstreamItem(BaseModel):
    type: str  # "consulting", "sample_testing", "product"
    id: str
    recordNumber: str
    title: str
    status: str
    details: Dict[str, Any]
    createdAt: Optional[str] = None


class OpportunityWorkstreamsResponse(BaseModel):
    success: bool = True
    opportunityId: str
    workstreams: List[WorkstreamItem]


class RequirementRouteRequest(BaseModel):
    requirementTypes: Optional[List[str]] = None
    notes: Optional[str] = None


class RequirementRouteResponse(BaseModel):
    success: bool = True
    message: str
    opportunityId: str
    routedWorkstreams: List[WorkstreamItem]


# Milestone Schemas
class MilestoneCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    workstreamType: Optional[str] = None
    workstreamId: Optional[str] = None
    plannedStartDate: Optional[py_date] = None
    dueDate: Optional[py_date] = None
    assignedToUserId: Optional[str] = None

    @field_validator("plannedStartDate", "dueDate", mode="before")
    @classmethod
    def validate_milestone_dates(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    workstreamType: Optional[str] = None
    workstreamId: Optional[str] = None
    plannedStartDate: Optional[py_date] = None
    dueDate: Optional[py_date] = None
    assignedToUserId: Optional[str] = None
    completionNotes: Optional[str] = None

    @field_validator("plannedStartDate", "dueDate", mode="before")
    @classmethod
    def validate_milestone_update_dates(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)


class MilestoneStatusTransitionRequest(BaseModel):
    status: str = Field(..., description="Pending, In Progress, Completed, Cancelled")
    completionNotes: Optional[str] = None
    completedAt: Optional[datetime] = None


class MilestoneItem(BaseModel):
    id: str
    milestoneId: str
    opportunityId: str
    opportunityName: Optional[str] = None
    workstreamType: Optional[str] = None
    workstreamId: Optional[str] = None
    title: str
    description: Optional[str] = None
    plannedStartDate: Optional[str] = None
    dueDate: Optional[str] = None
    status: str
    completedAt: Optional[str] = None
    completionNotes: Optional[str] = None
    assignedToUserId: Optional[str] = None
    assignedToName: Optional[str] = None
    createdById: Optional[str] = None
    createdByName: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    isOverdue: bool = False


class MilestoneListResponse(BaseModel):
    success: bool = True
    count: int
    milestones: List[MilestoneItem]


class MilestoneDetailResponse(BaseModel):
    success: bool = True
    milestone: MilestoneItem


class LeadQualificationMatchesResponse(BaseModel):
    success: bool = True
    leadId: str
    matchingAccounts: List[Dict[str, Any]] = []
    matchingContacts: List[Dict[str, Any]] = []
    suggestedAccount: Optional[Dict[str, Any]] = None
    suggestedContact: Optional[Dict[str, Any]] = None
    suggestedClientStatus: str = "New"


class LeadQualifyAccountChoice(BaseModel):
    action: str = Field(..., description="'reuse' or 'create'")
    accountId: Optional[str] = None
    name: Optional[str] = None
    siteName: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    businessArea: Optional[str] = None


class LeadQualifyContactChoice(BaseModel):
    action: str = Field(..., description="'reuse' or 'create'")
    contactId: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    mobileNumber: Optional[str] = None
    designation: Optional[str] = None


class LeadQualifyRequest(BaseModel):
    account: LeadQualifyAccountChoice
    contact: Optional[LeadQualifyContactChoice] = None
    opportunityName: Optional[str] = None
    opportunityDescription: Optional[str] = None
    estimatedValue: Optional[float] = None
    assignedToUserId: Optional[str] = None
    clientStatus: Optional[str] = None


class LeadQualifyResponse(BaseModel):
    success: bool = True
    message: str
    lead: LeadItem
    account: Dict[str, Any]
    contact: Optional[Dict[str, Any]] = None
    opportunity: OpportunityItem


# =========================================================================
# 5. COMMUNICATION SCHEMAS
# =========================================================================

class CommunicationCreate(BaseModel):
    channel: str = Field(...)
    eventType: str = Field(..., min_length=1)
    subject: Optional[str] = None
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
    leadId: Optional[str] = None
    opportunityId: Optional[str] = None
    subject: Optional[str] = None
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


# =========================================================================
# 7. CHARGE-READY BUSINESS SCHEMAS (CONSULTING, SAMPLES, PRODUCTS)
# =========================================================================

class ConsultingEngagementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    accountId: str
    contactId: Optional[str] = None
    leadId: Optional[str] = None
    scopeDescription: Optional[str] = None
    contractStartDate: Optional[py_date] = None
    contractEndDate: Optional[py_date] = None
    durationMonths: Optional[int] = None
    agreedFee: float = 0.0
    billingArrangement: Optional[str] = "Monthly"
    status: Optional[str] = "Draft"


class SampleTestInput(BaseModel):
    testName: str = Field(..., min_length=1, max_length=255)
    testType: Optional[str] = None
    unitPrice: float = 0.0
    quantity: float = 1.0
    notes: Optional[str] = None


class SampleSubmissionCreate(BaseModel):
    sampleDescription: str = Field(..., min_length=1, max_length=255)
    accountId: str
    contactId: Optional[str] = None
    leadId: Optional[str] = None
    sampleType: Optional[str] = None
    receiptDate: Optional[py_date] = None
    conditionOnReceipt: Optional[str] = "Good"
    sampleLevelCharge: float = 0.0
    tests: List[SampleTestInput] = []
    notes: Optional[str] = None


class ProductTransactionCreate(BaseModel):
    productName: str = Field(..., min_length=1, max_length=255)
    accountId: str
    contactId: Optional[str] = None
    leadId: Optional[str] = None
    skuCode: Optional[str] = None
    transactionType: Optional[str] = "Recommendation"
    status: Optional[str] = "Pending"
    quantity: float = 1.0
    unitOfMeasure: Optional[str] = "litres"
    unitRate: float = 0.0
    discountAmount: float = 0.0
    currency: Optional[str] = "INR"
    notes: Optional[str] = None


# =========================================================================
# PHASE 5A: QUOTATION, REOPENING & REVENUE REPORTING SCHEMAS
# =========================================================================

APPROVED_CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "SGD"]
OPPORTUNITY_STAGES = ["Enquiry", "Offer", "Negotiation", "Supply", "Payment", "Dormant"]


class OpportunityQuotationCreate(BaseModel):
    title: Optional[str] = None
    amount: float = Field(..., ge=0, description="Quotation amount")
    currency: Optional[str] = Field("INR", description="Approved currency e.g. INR, USD, EUR")
    quotationDate: Optional[py_date] = None
    validUntilDate: Optional[py_date] = None
    termsAndConditions: Optional[str] = None
    notes: Optional[str] = None
    fileId: Optional[str] = None
    documentName: Optional[str] = None

    @field_validator("quotationDate", "validUntilDate", mode="before")
    @classmethod
    def validate_quotation_dates(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)


class OpportunityQuotationUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    quotationDate: Optional[py_date] = None
    validUntilDate: Optional[py_date] = None
    termsAndConditions: Optional[str] = None
    notes: Optional[str] = None
    fileId: Optional[str] = None
    documentName: Optional[str] = None

    @field_validator("quotationDate", "validUntilDate", mode="before")
    @classmethod
    def validate_quotation_dates(cls, v: Any) -> Optional[py_date]:
        return parse_date_only_value(v)


class OpportunityQuotationApprovalRequest(BaseModel):
    action: str = Field(..., description="Action: 'approve' or 'reject'")
    reason: Optional[str] = Field(None, description="Mandatory reason when action is 'reject'")


class OpportunityQuotationShareRequest(BaseModel):
    sentMethod: str = Field(..., description="Sending method: 'Email', 'Courier', 'In-Person Handover', 'WhatsApp / Portal'")
    sentTo: str = Field(..., min_length=1, description="Recipient email address, contact name, or organization")
    sendingEvidence: Optional[str] = Field(None, description="Manual dispatch reference, delivery note, or client acknowledgment")


class OpportunityQuotationDetailResponse(BaseModel):
    success: bool = True
    quotation: OpportunityQuotationItem


class OpportunityQuotationListResponse(BaseModel):
    success: bool = True
    count: int
    activeQuotation: Optional[OpportunityQuotationItem] = None
    quotations: List[OpportunityQuotationItem]


class OpportunityReopenRequest(BaseModel):
    reopenStage: str = Field(..., description="Target pipeline stage for reopened opportunity (Enquiry, Offer, Negotiation, Supply, Payment)")
    reason: str = Field(..., min_length=1, description="Mandatory business justification reason for reopening a closed Opportunity")

    @model_validator(mode="after")
    def validate_reopen(self) -> "OpportunityReopenRequest":
        stg = self.reopenStage.strip() if self.reopenStage else ""
        open_stages = ["Enquiry", "Offer", "Negotiation", "Supply", "Payment"]
        if stg not in open_stages:
            raise ValueError(f"Invalid reopen stage '{stg}'. Permitted stages are: {', '.join(open_stages)}")
        return self


class RevenueMetricsResponse(BaseModel):
    success: bool = True
    totalCount: int
    openCount: int
    wonCount: int
    lostCount: int
    openPipelineValueByCurrency: Dict[str, float]
    wonOpportunityValueByCurrency: Dict[str, float]
    lostOpportunityValueByCurrency: Dict[str, float]
    byStage: List[PipelineStageMetrics]
    labelingNotice: str = "Won Opportunity Value represents signed commercial commitments and does not represent collected cash or recognized accounting revenue."


# =========================================================================
# LEAD NURTURING & UNIFIED TIMELINE SCHEMAS
# =========================================================================

class NurturingActivityCompleteRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Completion notes or interaction summary")
    outcome: Optional[str] = Field(None, description="Activity completion outcome")
    emailMessageReference: Optional[str] = Field(None, description="External email ID, subject or delivery reference")


class NurturingActivityRescheduleRequest(BaseModel):
    newDueDate: py_date = Field(..., description="New scheduled due date (YYYY-MM-DD)")
    reason: str = Field(..., min_length=1, description="Mandatory reason for rescheduling")


class NurturingActivitySkipRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Mandatory business reason for skipping this nurturing activity")


class CustomerResponseRequest(BaseModel):
    channel: str = Field(..., description="Communication channel: 'Email', 'Phone / Call', 'WhatsApp', 'In-Person Meeting', etc.")
    responseNotes: str = Field(..., min_length=1, description="Details and customer feedback received")
    outcome: str = Field(..., description="Customer interest level or sentiment: 'Interested', 'Not Interested', 'Callback Requested', 'Information Requested', etc.")
    targetLifecycleStatus: Optional[str] = Field(None, description="Optional approved lifecycle status: 'Negotiation', 'Offer', 'Dormant', etc.")
    pauseNurturing: bool = Field(True, description="Whether to automatically pause nurturing workflow upon recording response")


class NurturingPauseRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for pausing nurturing")


class NurturingResumeRequest(BaseModel):
    nextDueDate: Optional[py_date] = Field(None, description="Rescheduled next due date (default: today + 5 calendar days)")


class NurturingCancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Mandatory reason for cancelling nurturing")


class NurturingActivityItem(BaseModel):
    id: str
    activityId: str
    stageNumber: int
    subject: str
    activityType: str
    description: Optional[str] = None
    dueDate: Optional[str] = None
    status: str
    isOverdue: bool = False
    completedAt: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None
    skipReason: Optional[str] = None
    rescheduleReason: Optional[str] = None


class NextActivityItem(BaseModel):
    processStatus: str
    currentStage: int
    currentStageName: Optional[str] = None
    activityId: Optional[str] = None
    activityCode: Optional[str] = None
    stageNumber: Optional[int] = None
    subject: Optional[str] = None
    activityType: Optional[str] = None
    description: Optional[str] = None
    dueDate: Optional[str] = None
    status: Optional[str] = None
    isOverdue: bool = False
    overdueDays: int = 0
    remainingDays: int = 0
    owner: Optional[Dict[str, Any]] = None
    isPaused: Optional[bool] = None
    pauseReason: Optional[str] = None
    pausedAt: Optional[str] = None
    isTerminal: Optional[bool] = None
    stopReason: Optional[str] = None


class NurturingDetailsResponse(BaseModel):
    success: bool = True
    nurturing: Dict[str, Any]


class NextActivityResponse(BaseModel):
    success: bool = True
    nextActivity: Optional[Dict[str, Any]] = None


class UnifiedTimelineResponse(BaseModel):
    success: bool = True
    count: int
    timeline: List[Dict[str, Any]]
