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
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    confirmDuplicate: bool = False

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
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    isActive: Optional[bool] = None
    confirmDuplicate: bool = False

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
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
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
    name: str = Field(..., min_length=1, max_length=255)
    accountId: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)
    mobileNumber: Optional[str] = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=100)
    confirmDuplicate: bool = False

    @field_validator("name")
    @classmethod
    def validate_contact_name(cls, v: str) -> str:
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


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    accountId: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)
    mobileNumber: Optional[str] = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=100)
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
    name: str
    email: Optional[str] = None
    mobileNumber: Optional[str] = None
    designation: Optional[str] = None
    isActive: bool = True
    opportunityCount: int = 0
    opportunities: Optional[List[Dict[str, Any]]] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class ContactListResponse(BaseModel):
    success: bool = True
    count: int
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

ALLOWED_LIFECYCLE_STATUSES = {"Open", "Qualified", "Disqualified"}
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
            # Map legacy values
            if clean == "Direct Product/Service":
                clean = "Product"
            elif clean == "Undetermined":
                clean = "Consulting"

            if clean not in ALLOWED_REQUIREMENT_TYPES:
                raise ValueError(f"Invalid requirement type '{t}'. Must be one of: {sorted(ALLOWED_REQUIREMENT_TYPES)}")
            if clean not in selected:
                selected.append(clean)

    if not selected and legacy_single:
        clean = str(legacy_single).strip()
        if clean == "Direct Product/Service":
            clean = "Product"
        elif clean == "Undetermined":
            clean = "Consulting"

        if clean not in ALLOWED_REQUIREMENT_TYPES:
            raise ValueError(f"Invalid requirement type '{legacy_single}'. Must be one of: {sorted(ALLOWED_REQUIREMENT_TYPES)}")
        selected.append(clean)

    return selected


class LeadCreate(BaseModel):
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


class LeadUpdate(BaseModel):
    # Topic / Title
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
    leadName: Optional[str] = None
    displayName: str
    businessArea: str
    requirementType: Optional[str] = None
    requirementTypes: List[str] = []
    requirementSummary: Optional[str] = None
    requestedProductService: Optional[str] = None
    leadSource: str
    lifecycleStatus: str
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

    # Section 3 & 4 Fields
    rating: Optional[str] = None
    clientStatus: str = "New"
    description: Optional[str] = None
    industry: Optional[str] = None
    numberOfEmployees: Optional[int] = None
    currency: str = "INR"

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
    qualifiedAt: Optional[str] = None
    qualifiedById: Optional[str] = None
    qualifiedByName: Optional[str] = None


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
# OPPORTUNITY & QUALIFICATION SCHEMAS
# =========================================================================

class OpportunityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    accountId: str
    contactId: Optional[str] = None
    originatingLeadId: Optional[str] = None
    status: Optional[str] = "Open"
    currency: Optional[str] = "INR"
    estimatedValue: Optional[float] = None
    description: Optional[str] = None
    requirementSummary: Optional[str] = None
    requirementTypes: Optional[List[str]] = None
    assignedToUserId: Optional[str] = None


class OpportunityUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    currency: Optional[str] = None
    estimatedValue: Optional[float] = None
    description: Optional[str] = None
    requirementSummary: Optional[str] = None
    requirementTypes: Optional[List[str]] = None
    assignedToUserId: Optional[str] = None
    contactId: Optional[str] = None


class OpportunityItem(BaseModel):
    id: str
    opportunityId: str
    name: str
    accountId: str
    accountName: Optional[str] = None
    contactId: Optional[str] = None
    contactName: Optional[str] = None
    originatingLeadId: Optional[str] = None
    originatingLeadNumber: Optional[str] = None
    status: str = "Open"
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


class OpportunityListResponse(BaseModel):
    success: bool = True
    count: int
    opportunities: List[OpportunityItem]


class OpportunityDetailResponse(BaseModel):
    success: bool = True
    opportunity: OpportunityItem


class LeadQualificationMatchesResponse(BaseModel):
    success: bool = True
    leadId: str
    matchingAccounts: List[Dict[str, Any]] = []
    matchingContacts: List[Dict[str, Any]] = []
    suggestedAccount: Optional[Dict[str, Any]] = None
    suggestedContact: Optional[Dict[str, Any]] = None


class LeadQualifyAccountChoice(BaseModel):
    action: str = Field(..., description="'reuse' or 'create'")
    accountId: Optional[str] = None
    name: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None


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
