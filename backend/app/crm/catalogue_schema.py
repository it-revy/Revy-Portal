from datetime import datetime, date
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from decimal import Decimal


def to_camel_case(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(x.title() for x in parts[1:])


class CamelResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def convert_orm(cls, data: Any) -> Any:
        if hasattr(data, "__table__"):
            d = {}
            for col in data.__table__.columns:
                val = getattr(data, col.name)
                camel = to_camel_case(col.name)
                d[camel] = val
                d[col.name] = val
            return d
        return data


# =========================================================================
# COMMON & PAGINATION
# =========================================================================

class PaginationMeta(BaseModel):
    page: int
    pageSize: int
    totalItems: int
    totalPages: int


# =========================================================================
# CATEGORIES & SUBCATEGORIES
# =========================================================================

class ServiceCategoryBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    prefix: Optional[str] = None
    isActive: bool = True


class ServiceCategoryCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    prefix: Optional[str] = None
    isActive: bool = True

    @field_validator("code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="before")
    @classmethod
    def set_default_prefix(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("prefix") and data.get("code"):
                data["prefix"] = data["code"][:6].upper()
        return data


class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prefix: Optional[str] = None
    isActive: Optional[bool] = None


class ServiceSubcategoryBase(BaseModel):
    categoryId: str
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    isActive: bool = True


class ServiceSubcategoryCreate(BaseModel):
    categoryId: str
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    isActive: bool = True

    @field_validator("code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        return v.strip().upper()


class ServiceSubcategoryUpdate(BaseModel):
    categoryId: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    isActive: Optional[bool] = None


class ServiceSubcategoryResponse(CamelResponseModel):
    id: str
    categoryId: str
    code: str
    name: str
    description: Optional[str] = None
    isActive: bool
    isDeleted: bool
    createdAt: datetime
    updatedAt: datetime
    activeServicesCount: Optional[int] = 0


class ServiceCategoryResponse(CamelResponseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    prefix: str
    isActive: bool
    isDeleted: bool
    createdAt: datetime
    updatedAt: datetime
    serviceCount: Optional[int] = 0
    activeServicesCount: Optional[int] = 0

    @model_validator(mode="before")
    @classmethod
    def convert_cat_orm(cls, data: Any) -> Any:
        if hasattr(data, "__table__"):
            d = {}
            for col in data.__table__.columns:
                val = getattr(data, col.name)
                camel = to_camel_case(col.name)
                d[camel] = val
                d[col.name] = val
            if hasattr(data, "services"):
                cnt = sum(1 for s in (data.services or []) if s.is_active and not s.is_deleted)
                d["activeServicesCount"] = cnt
                d["serviceCount"] = cnt
            return d
        return data


# =========================================================================
# MASTER DATA (BILLING UNITS, REPORTING UNITS, SAMPLE TYPES, METHODS, CURRENCIES)
# =========================================================================

class MasterItemBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    isActive: bool = True


class BillingUnitCreate(MasterItemBase):
    pass


class BillingUnitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    isActive: Optional[bool] = None


class BillingUnitResponse(CamelResponseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    isActive: bool
    createdAt: datetime
    updatedAt: datetime


class ReportingUnitCreate(MasterItemBase):
    symbol: str = Field(..., max_length=50)


class ReportingUnitUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    description: Optional[str] = None
    isActive: Optional[bool] = None


class ReportingUnitResponse(CamelResponseModel):
    id: str
    code: str
    name: str
    symbol: str
    description: Optional[str] = None
    isActive: bool
    createdAt: datetime
    updatedAt: datetime


class SampleTypeCreate(MasterItemBase):
    pass


class SampleTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    isActive: Optional[bool] = None


class SampleTypeResponse(CamelResponseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    isActive: bool
    createdAt: datetime
    updatedAt: datetime


class TestingMethodCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    standardAgency: Optional[str] = None
    referenceStandard: Optional[str] = None
    revision: Optional[str] = None
    description: Optional[str] = None
    isActive: bool = True


class TestingMethodUpdate(BaseModel):
    name: Optional[str] = None
    standardAgency: Optional[str] = None
    referenceStandard: Optional[str] = None
    revision: Optional[str] = None
    description: Optional[str] = None
    isActive: Optional[bool] = None


class TestingMethodResponse(CamelResponseModel):
    id: str
    code: str
    name: str
    standardAgency: Optional[str] = None
    referenceStandard: Optional[str] = None
    revision: Optional[str] = None
    description: Optional[str] = None
    isActive: bool
    createdAt: datetime
    updatedAt: datetime


class CurrencyCreate(BaseModel):
    code: str = Field(..., max_length=10)
    name: str = Field(..., max_length=50)
    symbol: str = Field("₹", max_length=10)
    isDefault: bool = False
    isActive: bool = True


class CurrencyUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    isDefault: Optional[bool] = None
    isActive: Optional[bool] = None


class CurrencyResponse(CamelResponseModel):
    id: str
    code: str
    name: str
    symbol: str
    isDefault: bool
    isActive: bool
    createdAt: datetime
    updatedAt: datetime


# =========================================================================
# TAX CONFIGURATIONS & RATES
# =========================================================================

class TaxRateInput(BaseModel):
    rateName: Optional[str] = None
    componentName: Optional[str] = None
    percentage: Optional[Decimal] = None
    ratePercentage: Optional[Decimal] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("rateName") and data.get("componentName"):
                data["rateName"] = data["componentName"]
            if data.get("percentage") is None and data.get("ratePercentage") is not None:
                data["percentage"] = data["ratePercentage"]
        return data


class TaxRateResponse(CamelResponseModel):
    id: str
    taxConfigurationId: Optional[str] = None
    rateName: str
    percentage: Decimal
    isActive: bool

    @model_validator(mode="before")
    @classmethod
    def convert_tax_rate_orm(cls, data: Any) -> Any:
        if hasattr(data, "__table__"):
            d = {}
            for col in data.__table__.columns:
                val = getattr(data, col.name)
                camel = to_camel_case(col.name)
                d[camel] = val
                d[col.name] = val
            d["taxConfigurationId"] = getattr(data, "configuration_id", None)
            d["rateName"] = getattr(data, "component_name", "")
            d["percentage"] = getattr(data, "rate_percentage", Decimal("0.0"))
            return d
        if isinstance(data, dict):
            if "taxConfigurationId" not in data and "configuration_id" in data:
                data["taxConfigurationId"] = data["configuration_id"]
            if "rateName" not in data and "component_name" in data:
                data["rateName"] = data["component_name"]
            if "percentage" not in data and "rate_percentage" in data:
                data["percentage"] = data["rate_percentage"]
            return data
        return data


class TaxConfigurationCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    taxType: str = Field("GST", max_length=50)
    isDefault: bool = False
    isActive: bool = True
    rates: List[TaxRateInput] = []


class TaxConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    taxType: Optional[str] = None
    isDefault: Optional[bool] = None
    isActive: Optional[bool] = None
    rates: Optional[List[TaxRateInput]] = None


class TaxConfigurationResponse(CamelResponseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    taxType: str
    isDefault: bool = False
    isActive: bool
    createdAt: datetime
    updatedAt: datetime
    rates: List[TaxRateResponse] = []
    totalTaxPercentage: Decimal = Decimal("0.0")

    @model_validator(mode="before")
    @classmethod
    def convert_tax_orm(cls, data: Any) -> Any:
        if hasattr(data, "__table__"):
            d = {}
            for col in data.__table__.columns:
                val = getattr(data, col.name)
                camel = to_camel_case(col.name)
                d[camel] = val
                d[col.name] = val
            rates = getattr(data, "rates", []) or []
            d["rates"] = rates
            explicit_total = getattr(data, "total_percentage", None)
            if explicit_total is not None:
                d["totalTaxPercentage"] = Decimal(str(explicit_total))
            else:
                total = Decimal("0.0")
                for r in rates:
                    val = getattr(r, "rate_percentage", getattr(r, "percentage", None))
                    if val is not None:
                        total += Decimal(str(val))
                d["totalTaxPercentage"] = total
            return d
        if isinstance(data, dict):
            if "totalTaxPercentage" not in data:
                rates = data.get("rates", []) or []
                total = Decimal("0.0")
                for r in rates:
                    if isinstance(r, dict):
                        val = r.get("rate_percentage", r.get("percentage", 0))
                    else:
                        val = getattr(r, "rate_percentage", getattr(r, "percentage", 0))
                    total += Decimal(str(val or 0))
                data["totalTaxPercentage"] = total
            return data
        return data


# =========================================================================
# SERVICE REPORTING PARAMETERS & TESTING METHODS
# =========================================================================

class ServiceReportingParameterInput(BaseModel):
    id: Optional[str] = None
    parameterName: str = Field(..., max_length=255)
    reportingUnitId: Optional[str] = None
    testingMethodId: Optional[str] = None
    minRange: Optional[Decimal] = None
    maxRange: Optional[Decimal] = None
    displayOrder: int = 0
    isActive: bool = True


class ServiceReportingParameterResponse(CamelResponseModel):
    id: str
    serviceId: str
    parameterName: str
    reportingUnitId: Optional[str] = None
    reportingUnitSymbol: Optional[str] = None
    reportingUnitName: Optional[str] = None
    testingMethodId: Optional[str] = None
    testingMethodName: Optional[str] = None
    minRange: Optional[Decimal] = None
    maxRange: Optional[Decimal] = None
    displayOrder: int = 0
    isActive: bool


class ServiceTestingMethodInput(BaseModel):
    testingMethodId: str
    isDefault: bool = False


class ServiceTestingMethodResponse(CamelResponseModel):
    id: str
    serviceId: str
    testingMethodId: str
    isDefault: bool
    testingMethodName: Optional[str] = None
    standardAgency: Optional[str] = None
    referenceStandard: Optional[str] = None
    revision: Optional[str] = None


class ServiceSampleTypeResponse(CamelResponseModel):
    id: str
    serviceId: str
    sampleTypeId: str
    sampleTypeCode: Optional[str] = None
    sampleTypeName: Optional[str] = None


class ServicePriceHistoryResponse(CamelResponseModel):
    id: str
    serviceId: str
    oldPrice: Optional[Decimal] = None
    newPrice: Decimal
    currencyId: str
    currencyCode: Optional[str] = None
    effectiveDate: date
    changeReason: Optional[str] = None
    createdById: Optional[str] = None
    createdByName: Optional[str] = None
    createdAt: datetime


# =========================================================================
# SERVICES
# =========================================================================

class ServiceCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    categoryId: str
    billingUnitId: str
    currencyId: Optional[str] = None
    minimumBillingQuantity: int = Field(1, ge=1)
    standardPrice: Decimal = Field(..., ge=0)
    effectiveDate: Optional[date] = None
    isActive: bool = True
    isAddonEligible: bool = False
    canHaveAddons: bool = True
    sourceNote: Optional[str] = None
    sampleTypeIds: List[str] = []
    testingMethodIds: List[str] = []
    reportingParameters: List[ServiceReportingParameterInput] = []


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    categoryId: Optional[str] = None
    billingUnitId: Optional[str] = None
    currencyId: Optional[str] = None
    minimumBillingQuantity: Optional[int] = Field(None, ge=1)
    standardPrice: Optional[Decimal] = Field(None, ge=0)
    effectiveDate: Optional[date] = None
    isActive: Optional[bool] = None
    isAddonEligible: Optional[bool] = None
    canHaveAddons: Optional[bool] = None
    sourceNote: Optional[str] = None
    changeReason: Optional[str] = None
    sampleTypeIds: Optional[List[str]] = None
    testingMethodIds: Optional[List[str]] = None
    reportingParameters: Optional[List[ServiceReportingParameterInput]] = None


class ServiceResponse(CamelResponseModel):
    id: str
    code: str
    serviceCode: Optional[str] = None
    name: str
    description: Optional[str] = None
    categoryId: str
    categoryName: Optional[str] = None
    categoryCode: Optional[str] = None
    subcategoryId: Optional[str] = None
    subcategoryName: Optional[str] = None
    subcategoryCode: Optional[str] = None
    billingUnitId: str
    billingUnitCode: Optional[str] = None
    billingUnitName: Optional[str] = None
    currencyId: str
    currencyCode: Optional[str] = None
    currencySymbol: Optional[str] = None
    minimumBillingQuantity: int
    standardPrice: Decimal
    effectivePrice: Optional[Decimal] = None
    effectiveDate: date
    isActive: bool
    isDeleted: bool
    isAddonEligible: bool
    canHaveAddons: bool
    sourceNote: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    sampleTypes: List[ServiceSampleTypeResponse] = []
    testingMethods: List[ServiceTestingMethodResponse] = []
    reportingParameters: List[ServiceReportingParameterResponse] = []

    @model_validator(mode="before")
    @classmethod
    def convert_service_orm(cls, data: Any) -> Any:
        if hasattr(data, "__table__"):
            d = {}
            for col in data.__table__.columns:
                val = getattr(data, col.name)
                camel = to_camel_case(col.name)
                d[camel] = val
                d[col.name] = val

            # service_code column mapping
            sc = getattr(data, "service_code", getattr(data, "code", ""))
            d["code"] = sc
            d["serviceCode"] = sc
            d["service_code"] = sc

            cat = getattr(data, "category", None)
            d["categoryName"] = cat.name if cat else None
            d["categoryCode"] = cat.code if cat else None
            d["subcategoryName"] = None
            d["subcategoryCode"] = None
            bunit = getattr(data, "billing_unit", None)
            d["billingUnitCode"] = bunit.code if bunit else None
            d["billingUnitName"] = bunit.name if bunit else None
            curr = getattr(data, "currency", None)
            d["currencyCode"] = curr.code if curr else "INR"
            d["currencySymbol"] = curr.symbol if curr else "₹"
            d["effectivePrice"] = getattr(data, "effective_price", data.standard_price)

            # Sample types
            st_list = []
            for st in getattr(data, "sample_types", []) or []:
                st_obj = getattr(st, "sample_type", None)
                st_list.append({
                    "id": st.id,
                    "serviceId": st.service_id,
                    "sampleTypeId": st.sample_type_id,
                    "sampleTypeCode": st_obj.code if st_obj else None,
                    "sampleTypeName": st_obj.name if st_obj else None
                })
            d["sampleTypes"] = st_list

            # Testing methods
            tm_list = []
            for tm in getattr(data, "testing_methods", []) or []:
                tm_obj = getattr(tm, "testing_method", None)
                tm_list.append({
                    "id": tm.id,
                    "serviceId": tm.service_id,
                    "testingMethodId": tm.testing_method_id,
                    "isDefault": tm.is_default,
                    "testingMethodName": tm_obj.name if tm_obj else None,
                    "standardAgency": getattr(tm_obj, "standard_agency", None) if tm_obj else None,
                    "referenceStandard": getattr(tm_obj, "reference_standard", None) if tm_obj else None,
                    "revision": getattr(tm_obj, "revision", None) if tm_obj else None
                })
            d["testingMethods"] = tm_list

            # Reporting parameters
            rp_list = []
            for rp in getattr(data, "reporting_parameters", []) or []:
                rp_u = getattr(rp, "reporting_unit", None)
                rp_m = getattr(rp, "testing_method", None)
                rp_list.append({
                    "id": rp.id,
                    "serviceId": rp.service_id,
                    "parameterName": rp.parameter_name,
                    "reportingUnitId": rp.reporting_unit_id,
                    "reportingUnitSymbol": rp_u.symbol if rp_u else None,
                    "reportingUnitName": rp_u.name if rp_u else None,
                    "testingMethodId": rp.testing_method_id,
                    "testingMethodName": rp_m.name if rp_m else None,
                    "minRange": rp.min_range,
                    "maxRange": rp.max_range,
                    "displayOrder": getattr(rp, "display_order", 0),
                    "isActive": rp.is_active
                })
            d["reportingParameters"] = rp_list
            return d
        return data


class ServiceListResponse(BaseModel):
    success: bool = True
    total: int
    services: List[ServiceResponse]


# =========================================================================
# PACKAGES
# =========================================================================

class PackageComponentInput(BaseModel):
    serviceId: str
    quantity: int = Field(1, ge=1)
    isMandatory: bool = True


class PackageComponentResponse(CamelResponseModel):
    id: str
    packageVersionId: str
    serviceId: str
    serviceCode: Optional[str] = None
    serviceName: Optional[str] = None
    quantity: int
    referenceUnitPrice: Decimal
    subtotalPrice: Decimal
    isMandatory: bool


class PackageAddOnConfigurationResponse(CamelResponseModel):
    id: str
    packageId: str
    serviceId: str
    serviceCode: Optional[str] = None
    serviceName: Optional[str] = None
    defaultQuantity: int
    overridePrice: Optional[Decimal] = None
    isMandatory: bool
    isActive: bool


class PackageVersionResponse(CamelResponseModel):
    id: str
    packageId: str
    versionNumber: int
    packagePrice: Decimal
    effectiveDate: date
    changeReason: Optional[str] = None
    referenceComponentSum: Decimal
    isActive: bool
    createdAt: datetime
    components: List[PackageComponentResponse] = []

    @model_validator(mode="before")
    @classmethod
    def convert_ver_orm(cls, data: Any) -> Any:
        if hasattr(data, "__table__"):
            d = {}
            for col in data.__table__.columns:
                val = getattr(data, col.name)
                camel = to_camel_case(col.name)
                d[camel] = val
                d[col.name] = val
            comp_list = []
            for c in getattr(data, "components", []) or []:
                s = getattr(c, "service", None)
                ref_p = getattr(c, "reference_price", Decimal("0.0"))
                qty = getattr(c, "quantity", 1)
                comp_list.append({
                    "id": c.id,
                    "packageVersionId": c.package_version_id,
                    "serviceId": c.service_id,
                    "serviceCode": s.service_code if s else None,
                    "serviceName": s.name if s else None,
                    "quantity": qty,
                    "referenceUnitPrice": ref_p,
                    "subtotalPrice": Decimal(str(ref_p)) * qty,
                    "isMandatory": getattr(c, "is_mandatory", True)
                })
            d["components"] = comp_list
            d["packagePrice"] = getattr(data, "fixed_price", getattr(data, "package_price", Decimal("0.0")))
            d["changeReason"] = getattr(data, "change_summary", getattr(data, "change_reason", None))
            d["referenceComponentSum"] = sum(Decimal(str(c.reference_price)) * c.quantity for c in getattr(data, "components", []) or [])
            return d
        return data


class PackageCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    categoryId: Optional[str] = None
    currencyId: Optional[str] = None
    packagePrice: Decimal = Field(default=Decimal("0.0"), ge=0)
    fixedPackagePrice: Decimal = Field(default=Decimal("0.0"), ge=0)
    effectiveDate: Optional[date] = None
    isActive: bool = True
    components: List[PackageComponentInput] = Field(..., min_length=1)
    addonConfigurations: List[Any] = []

    @model_validator(mode="before")
    @classmethod
    def sync_prices(cls, data: Any) -> Any:
        if isinstance(data, dict):
            p = data.get("packagePrice") if data.get("packagePrice") is not None else data.get("fixedPackagePrice", Decimal("0.0"))
            data["packagePrice"] = p
            data["fixedPackagePrice"] = p
        return data


class PackageUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    categoryId: Optional[str] = None
    currencyId: Optional[str] = None
    isActive: Optional[bool] = None


class PackageNewVersionCreate(BaseModel):
    packagePrice: Decimal = Field(default=Decimal("0.0"), ge=0)
    fixedPackagePrice: Decimal = Field(default=Decimal("0.0"), ge=0)
    effectiveDate: Optional[date] = None
    changeReason: Optional[str] = None
    changeSummary: Optional[str] = None
    components: List[PackageComponentInput] = Field(..., min_length=1)
    addonConfigurations: List[Any] = []

    @model_validator(mode="before")
    @classmethod
    def sync_prices(cls, data: Any) -> Any:
        if isinstance(data, dict):
            p = data.get("packagePrice") if data.get("packagePrice") is not None else data.get("fixedPackagePrice", Decimal("0.0"))
            data["packagePrice"] = p
            data["fixedPackagePrice"] = p
            r = data.get("changeReason") or data.get("changeSummary")
            data["changeReason"] = r
            data["changeSummary"] = r
        return data


class PackageResponse(CamelResponseModel):
    id: str
    code: str
    packageCode: Optional[str] = None
    name: str
    description: Optional[str] = None
    categoryId: Optional[str] = None
    categoryName: Optional[str] = None
    subcategoryId: Optional[str] = None
    subcategoryName: Optional[str] = None
    currentVersion: Optional[int] = None
    fixedPackagePrice: Optional[Decimal] = None
    latestVersion: Optional[Any] = None
    currencyId: str
    currencyCode: Optional[str] = None
    currencySymbol: Optional[str] = None
    isActive: bool
    isDeleted: bool
    createdAt: datetime
    updatedAt: datetime

    activeVersion: Optional[PackageVersionResponse] = None
    versions: List[PackageVersionResponse] = []
    addons: List[PackageAddOnConfigurationResponse] = []

    @model_validator(mode="before")
    @classmethod
    def convert_pkg_orm(cls, data: Any) -> Any:
        if hasattr(data, "__table__"):
            d = {}
            for col in data.__table__.columns:
                val = getattr(data, col.name)
                camel = to_camel_case(col.name)
                d[camel] = val
                d[col.name] = val
            
            pkg_code = getattr(data, "package_code", getattr(data, "code", ""))
            d["code"] = pkg_code
            d["packageCode"] = pkg_code
            d["package_code"] = pkg_code

            cat = getattr(data, "category", None)
            d["categoryName"] = cat.name if cat else None
            d["subcategoryName"] = None
            curr = getattr(data, "currency", None)
            d["currencyCode"] = curr.code if curr else "INR"
            d["currencySymbol"] = curr.symbol if curr else "₹"

            # Versions
            versions = getattr(data, "versions", []) or []
            v_list = []
            active_v = None
            for v in versions:
                comp_list = []
                for c in getattr(v, "components", []) or []:
                    s = getattr(c, "service", None)
                    ref_p = getattr(c, "reference_price", Decimal("0.0"))
                    qty = getattr(c, "quantity", 1)
                    comp_list.append({
                        "id": c.id,
                        "packageVersionId": c.package_version_id,
                        "serviceId": c.service_id,
                        "serviceCode": s.service_code if s else None,
                        "serviceName": s.name if s else None,
                        "quantity": qty,
                        "referenceUnitPrice": ref_p,
                        "subtotalPrice": Decimal(str(ref_p)) * qty,
                        "isMandatory": getattr(c, "is_mandatory", True)
                    })
                ref_sum = sum(Decimal(str(c.reference_price)) * c.quantity for c in getattr(v, "components", []) or [])
                v_dict = {
                    "id": v.id,
                    "packageId": v.package_id,
                    "versionNumber": v.version_number,
                    "packagePrice": getattr(v, "fixed_price", getattr(v, "package_price", Decimal("0.0"))),
                    "effectiveDate": v.effective_date,
                    "changeReason": getattr(v, "change_summary", getattr(v, "change_reason", None)),
                    "referenceComponentSum": ref_sum,
                    "isActive": v.is_active,
                    "createdAt": v.created_at,
                    "components": comp_list
                }
                v_list.append(v_dict)
                if v.is_active:
                    active_v = v_dict

            best_version = active_v or (v_list[0] if v_list else None)
            d["versions"] = v_list
            d["activeVersion"] = best_version
            d["latestVersion"] = best_version
            d["currentVersion"] = best_version["versionNumber"] if best_version else 1
            d["fixedPackagePrice"] = best_version["packagePrice"] if best_version else Decimal("0.0")
            d["addons"] = []
            return d
        return data


class PackageListResponse(BaseModel):
    success: bool = True
    total: int
    packages: List[PackageResponse]


# =========================================================================
# QUOTATION LINE ITEMS
# =========================================================================

class QuotationItemInput(BaseModel):
    itemType: str = Field(..., pattern="^(SERVICE|PACKAGE|ADDON)$")
    serviceId: Optional[str] = None
    packageId: Optional[str] = None
    packageVersionId: Optional[str] = None
    parentItemId: Optional[str] = None
    quantity: int = Field(1, ge=1)
    unitPrice: Optional[Decimal] = Field(None, ge=0)
    negotiatedUnitPrice: Optional[Decimal] = Field(None, ge=0)
    sampleType: Optional[str] = None
    sampleTypeId: Optional[str] = None
    testingMethod: Optional[str] = None
    testingMethodId: Optional[str] = None
    taxConfigurationId: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_unit_prices(cls, data: Any) -> Any:
        if isinstance(data, dict):
            p = data.get("unitPrice") if data.get("unitPrice") is not None else data.get("negotiatedUnitPrice")
            data["unitPrice"] = p
            data["negotiatedUnitPrice"] = p
        return data


class QuotationItemResponse(CamelResponseModel):
    id: str
    quotationId: str
    itemType: str
    serviceId: Optional[str] = None
    packageId: Optional[str] = None
    packageVersionId: Optional[str] = None
    parentItemId: Optional[str] = None

    itemCode: str
    itemName: str
    description: Optional[str] = None
    billingUnit: Optional[str] = None
    quantity: int

    standardPrice: Decimal
    unitPrice: Decimal
    lineTotal: Decimal
    taxRatePercentage: Decimal
    taxAmount: Decimal
    totalPrice: Decimal
    currency: str

    sampleType: Optional[str] = None
    testingMethod: Optional[str] = None
    snapshotData: Optional[Any] = None
    createdAt: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_quotation_fields(cls, data: Any) -> Any:
        import json
        if hasattr(data, "__table__"):
            d = cls.convert_orm(data)
        elif isinstance(data, dict):
            d = dict(data)
        else:
            return data

        # lineTotal = taxable_amount or total_price
        line_total = d.get("lineTotal")
        if line_total is None:
            line_total = d.get("taxableAmount") if d.get("taxableAmount") is not None else (d.get("totalPrice") or Decimal("0.0"))
        d["lineTotal"] = Decimal(str(line_total))

        # taxAmount = total_tax
        tax_amount = d.get("taxAmount")
        if tax_amount is None:
            tax_amount = d.get("totalTax") or Decimal("0.0")
        d["taxAmount"] = Decimal(str(tax_amount))

        # taxRatePercentage = sum of cgst_rate + sgst_rate + igst_rate
        tax_rate = d.get("taxRatePercentage")
        if tax_rate is None:
            cgst = d.get("cgstRate") or Decimal("0.0")
            sgst = d.get("sgstRate") or Decimal("0.0")
            igst = d.get("igstRate") or Decimal("0.0")
            tax_rate = Decimal(str(cgst)) + Decimal(str(sgst)) + Decimal(str(igst))
        d["taxRatePercentage"] = Decimal(str(tax_rate))

        # totalPrice = final_total or (line_total + tax_amount)
        final_total = d.get("finalTotal")
        if final_total is None or Decimal(str(final_total)) == Decimal("0.0"):
            final_total = Decimal(str(d["lineTotal"])) + Decimal(str(d["taxAmount"]))
        d["totalPrice"] = Decimal(str(final_total))

        # snapshotData
        if not d.get("snapshotData"):
            raw_snap = d.get("packageComponentsSnapshot") or d.get("reportingParametersSnapshot") or d.get("testingMethodSnapshot")
            if raw_snap:
                try:
                    d["snapshotData"] = json.loads(raw_snap)
                except Exception:
                    d["snapshotData"] = raw_snap

        return d
