from datetime import date as py_date
from decimal import Decimal
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    CurrentUser,
    require_permission,
    get_current_user
)
from app.crm.catalogue_model import (
    ServiceCategory,
    BillingUnit,
    ReportingUnit,
    SampleType,
    TestingMethod,
    Currency,
    TaxConfiguration,
    Service,
    Package,
    OpportunityQuotationItem
)
from app.crm.catalogue_service import CatalogueService
from app.crm.catalogue_schema import (
    ServiceCategoryCreate,
    ServiceCategoryUpdate,
    ServiceCategoryResponse,
    BillingUnitCreate,
    BillingUnitUpdate,
    BillingUnitResponse,
    ReportingUnitCreate,
    ReportingUnitUpdate,
    ReportingUnitResponse,
    SampleTypeCreate,
    SampleTypeUpdate,
    SampleTypeResponse,
    TestingMethodCreate,
    TestingMethodUpdate,
    TestingMethodResponse,
    CurrencyCreate,
    CurrencyUpdate,
    CurrencyResponse,
    TaxConfigurationCreate,
    TaxConfigurationUpdate,
    TaxConfigurationResponse,
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    PackageCreate,
    PackageUpdate,
    PackageNewVersionCreate,
    PackageResponse,
    PackageVersionResponse,
    QuotationItemInput,
    QuotationItemResponse
)

router = APIRouter(prefix="/crm/catalogue", tags=["CRM - Product & Service Catalogue"])


# =========================================================================
# RBAC DEPENDENCY HELPERS
# =========================================================================

def require_catalogue_admin(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """Enforces CRM Admin or global admin role for catalogue modifications."""
    roles = getattr(current_user, "roles", []) or []
    perms = getattr(current_user, "permissions", []) or []
    is_admin = (
        "CRM_ADMIN" in roles or
        "IT_ADMIN" in roles or
        "DIRECTOR" in roles or
        "crm.catalogue.manage" in perms or
        getattr(current_user, "is_admin", False)
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CRM Admin access required to manage catalogue configuration."
        )
    return current_user


def require_catalogue_read(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """Enforces CRM read access to view catalogue."""
    roles = getattr(current_user, "roles", []) or []
    perms = getattr(current_user, "permissions", []) or []
    can_read = (
        "CRM_ADMIN" in roles or
        "CRM_SALES_MANAGER" in roles or
        "CRM_SALES_REP" in roles or
        "IT_ADMIN" in roles or
        "DIRECTOR" in roles or
        "crm.catalogue.view" in perms or
        "crm.catalogue.manage" in perms or
        getattr(current_user, "is_admin", False)
    )
    if not can_read:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CRM access required to view catalogue records."
        )
    return current_user


# =========================================================================
# 1. CATEGORIES & SUBCATEGORIES
# =========================================================================

@router.get("/categories")
def list_categories(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items = service.list_categories(include_inactive=include_inactive)
    serialized = [ServiceCategoryResponse.model_validate(c) for c in items]
    return {
        "success": True,
        "total": len(items),
        "categories": serialized,
        "items": serialized,
        "data": serialized
    }


@router.get("/categories/{category_id}")
def get_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    cat = service.get_category(category_id)
    return {
        "success": True,
        "category": ServiceCategoryResponse.model_validate(cat)
    }


@router.post("/categories")
def create_category(
    payload: ServiceCategoryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    cat = service.create_category(current_user, payload, request)
    return {
        "success": True,
        "category": ServiceCategoryResponse.model_validate(cat)
    }


@router.put("/categories/{category_id}")
def update_category(
    category_id: str,
    payload: ServiceCategoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    cat = service.update_category(current_user, category_id, payload, request)
    return {
        "success": True,
        "category": ServiceCategoryResponse.model_validate(cat)
    }


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    service.soft_delete_category(current_user, category_id, request)
    return {"success": True, "message": "Category soft-deleted successfully."}


# Subcategories (Deprecated - Main Category directly maps to Services)
@router.get("/subcategories")
def list_subcategories(
    category_id: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    return {
        "success": True,
        "total": 0,
        "subcategories": [],
        "items": [],
        "data": []
    }


# =========================================================================
# 2. MASTER DATA (BILLING, REPORTING, SAMPLES, METHODS, CURRENCIES, TAX)
# =========================================================================

# Billing Units
@router.get("/billing-units")
def list_billing_units(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items = service.list_billing_units(include_inactive=include_inactive)
    serialized = [BillingUnitResponse.model_validate(u) for u in items]
    return {
        "success": True,
        "total": len(items),
        "billingUnits": serialized,
        "items": serialized,
        "data": serialized
    }


@router.post("/billing-units")
def create_billing_unit(
    payload: BillingUnitCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    unit = service.create_billing_unit(current_user, payload, request)
    return {
        "success": True,
        "billingUnit": BillingUnitResponse.model_validate(unit)
    }


@router.put("/billing-units/{unit_id}")
def update_billing_unit(
    unit_id: str,
    payload: BillingUnitUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    unit = service.update_billing_unit(current_user, unit_id, payload, request)
    return {
        "success": True,
        "billingUnit": BillingUnitResponse.model_validate(unit)
    }


# Reporting Units
@router.get("/reporting-units")
def list_reporting_units(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items = service.list_reporting_units(include_inactive=include_inactive)
    serialized = [ReportingUnitResponse.model_validate(u) for u in items]
    return {
        "success": True,
        "total": len(items),
        "reportingUnits": serialized,
        "items": serialized,
        "data": serialized
    }


@router.post("/reporting-units")
def create_reporting_unit(
    payload: ReportingUnitCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    unit = service.create_reporting_unit(current_user, payload, request)
    return {
        "success": True,
        "reportingUnit": ReportingUnitResponse.model_validate(unit)
    }


@router.put("/reporting-units/{unit_id}")
def update_reporting_unit(
    unit_id: str,
    payload: ReportingUnitUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    unit = service.update_reporting_unit(current_user, unit_id, payload, request)
    return {
        "success": True,
        "reportingUnit": ReportingUnitResponse.model_validate(unit)
    }


# Sample Types
@router.get("/sample-types")
def list_sample_types(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items = service.list_sample_types(include_inactive=include_inactive)
    serialized = [SampleTypeResponse.model_validate(s) for s in items]
    return {
        "success": True,
        "total": len(items),
        "sampleTypes": serialized,
        "items": serialized,
        "data": serialized
    }


@router.post("/sample-types")
def create_sample_type(
    payload: SampleTypeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    item = service.create_sample_type(current_user, payload, request)
    return {
        "success": True,
        "sampleType": SampleTypeResponse.model_validate(item)
    }


@router.put("/sample-types/{type_id}")
def update_sample_type(
    type_id: str,
    payload: SampleTypeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    item = service.update_sample_type(current_user, type_id, payload, request)
    return {
        "success": True,
        "sampleType": SampleTypeResponse.model_validate(item)
    }


# Testing Methods
@router.get("/testing-methods")
def list_testing_methods(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items = service.list_testing_methods(include_inactive=include_inactive)
    serialized = [TestingMethodResponse.model_validate(m) for m in items]
    return {
        "success": True,
        "total": len(items),
        "testingMethods": serialized,
        "items": serialized,
        "data": serialized
    }


@router.post("/testing-methods")
def create_testing_method(
    payload: TestingMethodCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    item = service.create_testing_method(current_user, payload, request)
    return {
        "success": True,
        "testingMethod": TestingMethodResponse.model_validate(item)
    }


@router.put("/testing-methods/{method_id}")
def update_testing_method(
    method_id: str,
    payload: TestingMethodUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    item = service.update_testing_method(current_user, method_id, payload, request)
    return {
        "success": True,
        "testingMethod": TestingMethodResponse.model_validate(item)
    }


# Currencies
@router.get("/currencies")
def list_currencies(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items = service.list_currencies(include_inactive=include_inactive)
    serialized = [CurrencyResponse.model_validate(c) for c in items]
    return {
        "success": True,
        "total": len(items),
        "currencies": serialized,
        "items": serialized,
        "data": serialized
    }


@router.post("/currencies")
def create_currency(
    payload: CurrencyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    item = service.create_currency(current_user, payload, request)
    return {
        "success": True,
        "currency": CurrencyResponse.model_validate(item)
    }


@router.put("/currencies/{currency_id}")
def update_currency(
    currency_id: str,
    payload: CurrencyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    item = service.update_currency(current_user, currency_id, payload, request)
    return {
        "success": True,
        "currency": CurrencyResponse.model_validate(item)
    }


# Tax Configurations
@router.get("/tax-configurations")
def list_tax_configurations(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items = service.list_tax_configurations(include_inactive=include_inactive)
    serialized = [TaxConfigurationResponse.model_validate(t) for t in items]
    return {
        "success": True,
        "total": len(items),
        "taxConfigurations": serialized,
        "items": serialized,
        "data": serialized
    }


@router.get("/tax-configurations/{config_id}")
def get_tax_configuration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    item = service.get_tax_configuration(config_id)
    return {
        "success": True,
        "taxConfiguration": TaxConfigurationResponse.model_validate(item)
    }


@router.post("/tax-configurations")
def create_tax_configuration(
    payload: TaxConfigurationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    item = service.create_tax_configuration(current_user, payload, request)
    return {
        "success": True,
        "taxConfiguration": TaxConfigurationResponse.model_validate(item)
    }


@router.put("/tax-configurations/{config_id}")
def update_tax_configuration(
    config_id: str,
    payload: TaxConfigurationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    item = service.update_tax_configuration(current_user, config_id, payload, request)
    return {
        "success": True,
        "taxConfiguration": TaxConfigurationResponse.model_validate(item)
    }


# =========================================================================
# 3. SERVICES
# =========================================================================

@router.get("/services")
def list_services(
    categoryId: Optional[str] = Query(None),
    billingUnitId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    isAddonEligible: Optional[bool] = Query(None),
    minPrice: Optional[Decimal] = Query(None),
    maxPrice: Optional[Decimal] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items, total = service.list_services(
        category_id=categoryId,
        search=search,
        is_active=isActive,
        is_addon_eligible=isAddonEligible,
        billing_unit_id=billingUnitId,
        min_price=minPrice,
        max_price=maxPrice,
        page=page,
        page_size=pageSize
    )
    serialized = [ServiceResponse.model_validate(s) for s in items]
    return {
        "success": True,
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "services": serialized,
        "items": serialized,
        "data": serialized
    }


@router.get("/services/{service_id}")
def get_service(
    service_id: str,
    as_of_date: Optional[py_date] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    srv = service.get_service(service_id, as_of_date=as_of_date)
    return {
        "success": True,
        "service": ServiceResponse.model_validate(srv)
    }


@router.post("/services")
def create_service(
    payload: ServiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    srv = service.create_service(current_user, payload, request)
    return {
        "success": True,
        "service": ServiceResponse.model_validate(srv)
    }


@router.put("/services/{service_id}")
def update_service(
    service_id: str,
    payload: ServiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    srv = service.update_service(current_user, service_id, payload, request)
    return {
        "success": True,
        "service": ServiceResponse.model_validate(srv)
    }


@router.delete("/services/{service_id}")
def delete_service(
    service_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    service.soft_delete_service(current_user, service_id, request)
    return {"success": True, "message": "Service soft-deleted successfully."}


# =========================================================================
# 4. PACKAGES & VERSIONS
# =========================================================================

@router.get("/packages")
def list_packages(
    categoryId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items, total = service.list_packages(
        category_id=categoryId,
        search=search,
        is_active=isActive,
        page=page,
        page_size=pageSize
    )
    serialized = [PackageResponse.model_validate(p) for p in items]
    return {
        "success": True,
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "packages": serialized,
        "items": serialized,
        "data": serialized
    }


@router.get("/packages/{package_id}")
def get_package(
    package_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    pkg = service.get_package(package_id)
    return {
        "success": True,
        "package": PackageResponse.model_validate(pkg)
    }


@router.post("/packages")
def create_package(
    payload: PackageCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    pkg = service.create_package(current_user, payload, request)
    return {
        "success": True,
        "package": PackageResponse.model_validate(pkg)
    }


@router.put("/packages/{package_id}")
def update_package_metadata(
    package_id: str,
    payload: PackageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    pkg = service.update_package_metadata(current_user, package_id, payload, request)
    return {
        "success": True,
        "package": PackageResponse.model_validate(pkg)
    }


@router.post("/packages/{package_id}/versions")
def create_new_package_version(
    package_id: str,
    payload: PackageNewVersionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_admin)
):
    service = CatalogueService(db)
    version = service.create_new_package_version(current_user, package_id, payload, request)
    return {
        "success": True,
        "version": PackageVersionResponse.model_validate(version)
    }


# =========================================================================
# 5. QUOTATION ITEMS & SNAPSHOTS
# =========================================================================

@router.get("/quotations/{quotation_id}/items")
def list_quotation_items(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    items = service.list_quotation_items(quotation_id)
    serialized = [QuotationItemResponse.model_validate(i) for i in items]
    return {
        "success": True,
        "total": len(items),
        "items": serialized,
        "data": serialized
    }


@router.post("/quotations/{quotation_id}/items")
def add_quotation_item(
    quotation_id: str,
    payload: QuotationItemInput,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    item = service.add_item_to_quotation(current_user, quotation_id, payload, request)
    return {
        "success": True,
        "item": QuotationItemResponse.model_validate(item)
    }


@router.delete("/quotations/{quotation_id}/items/{item_id}")
def remove_quotation_item(
    quotation_id: str,
    item_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    service.remove_quotation_item(current_user, quotation_id, item_id, request)
    return {"success": True, "message": "Quotation line item deleted successfully."}


@router.get("/opportunities/{opp_id}/quotations/current")
def get_current_opportunity_quotation(
    opp_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    from app.crm.invoice_service import ProformaInvoiceService
    service = CatalogueService(db)
    from app.crm.model import Opportunity, OpportunityQuotation
    from sqlalchemy.orm import joinedload
    from sqlalchemy import or_

    opp = db.query(Opportunity).filter(
        or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opp_id}' not found.")

    q = db.query(OpportunityQuotation).options(
        joinedload(OpportunityQuotation.items).joinedload(OpportunityQuotationItem.tax_configuration)
    ).filter(
        OpportunityQuotation.opportunity_id == opp.id,
        OpportunityQuotation.is_active == True
    ).first()

    if not q:
        return {"success": True, "quotation": None}

    inv_service = ProformaInvoiceService(db)
    email_text = ""
    try:
        email_data = inv_service.generate_quotation_email_text(q.id)
        email_text = email_data.get("emailText", "")
    except Exception:
        pass

    items = [QuotationItemResponse.model_validate(it) for it in q.items]
    return {
        "success": True,
        "quotation": {
            "id": q.id,
            "quotationNumber": q.quotation_number,
            "opportunityId": q.opportunity_id,
            "revisionNumber": q.revision_number,
            "version": q.version,
            "status": q.status,
            "title": q.title,
            "amount": float(q.amount),
            "subtotal": float(q.subtotal or 0.0),
            "taxType": q.tax_type or "INTRA_STATE",
            "taxConfigurationId": q.tax_configuration_id,
            "cgstAmount": float(q.cgst_amount or 0.0),
            "sgstAmount": float(q.sgst_amount or 0.0),
            "igstAmount": float(q.igst_amount or 0.0),
            "totalTax": float(q.total_tax or 0.0),
            "discountAmount": float(q.discount_amount or 0.0),
            "currency": q.currency,
            "quotationDate": q.quotation_date,
            "validUntilDate": q.valid_until_date,
            "termsAndConditions": q.terms_and_conditions,
            "notes": q.notes,
            "items": items,
            "emailText": email_text
        }
    }


@router.post("/opportunities/{opp_id}/quotations/save-current")
def save_current_opportunity_quotation(
    opp_id: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_catalogue_read)
):
    service = CatalogueService(db)
    try:
        q = service.save_current_quotation(current_user, opp_id, payload, request)
        from app.crm.invoice_service import ProformaInvoiceService
        inv_service = ProformaInvoiceService(db)
        email_text = ""
        try:
            email_data = inv_service.generate_quotation_email_text(q.id)
            email_text = email_data.get("emailText", "")
        except Exception:
            pass

        items = [QuotationItemResponse.model_validate(it) for it in q.items]
        return {
            "success": True,
            "message": f"Quotation {q.quotation_number} saved successfully.",
            "quotation": {
                "id": q.id,
                "quotationNumber": q.quotation_number,
                "opportunityId": q.opportunity_id,
                "revisionNumber": q.revision_number,
                "status": q.status,
                "title": q.title,
                "amount": float(q.amount),
                "subtotal": float(q.subtotal or 0.0),
                "taxType": q.tax_type,
                "taxConfigurationId": q.tax_configuration_id,
                "cgstAmount": float(q.cgst_amount or 0.0),
                "sgstAmount": float(q.sgst_amount or 0.0),
                "igstAmount": float(q.igst_amount or 0.0),
                "totalTax": float(q.total_tax or 0.0),
                "discountAmount": float(q.discount_amount or 0.0),
                "currency": q.currency,
                "quotationDate": q.quotation_date,
                "validUntilDate": q.valid_until_date,
                "termsAndConditions": q.terms_and_conditions,
                "notes": q.notes,
                "items": items,
                "emailText": email_text
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

