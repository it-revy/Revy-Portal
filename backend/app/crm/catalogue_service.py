import json
import logging
from datetime import datetime, timezone, date as py_date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc, asc, func

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    PermissionDeniedError,
    ConflictError
)
from app.audit.service import AuditService
from app.core.dependencies import CurrentUser
from app.crm.catalogue_model import (
    ServiceCategory,
    BillingUnit,
    ReportingUnit,
    SampleType,
    TestingMethod,
    Currency,
    TaxConfiguration,
    TaxRate,
    Service,
    ServiceSampleType,
    ServiceTestingMethod,
    ServiceReportingParameter,
    ServicePriceHistory,
    Package,
    PackageVersion,
    PackageComponent,
    PackageAddOnConfiguration,
    OpportunityQuotationItem
)
from app.crm.catalogue_schema import (
    ServiceCategoryCreate,
    ServiceCategoryUpdate,
    BillingUnitCreate,
    BillingUnitUpdate,
    ReportingUnitCreate,
    ReportingUnitUpdate,
    SampleTypeCreate,
    SampleTypeUpdate,
    TestingMethodCreate,
    TestingMethodUpdate,
    CurrencyCreate,
    CurrencyUpdate,
    TaxConfigurationCreate,
    TaxConfigurationUpdate,
    ServiceCreate,
    ServiceUpdate,
    PackageCreate,
    PackageUpdate,
    PackageNewVersionCreate,
    QuotationItemInput
)
from app.crm.model import CrmSequence, OpportunityQuotation, Opportunity
from app.crm.service import get_next_sequence_id

logger = logging.getLogger("revy.crm.catalogue")


class CatalogueService:
    def __init__(self, db: Session, audit_service: Optional[AuditService] = None):
        self.db = db
        self.audit_service = audit_service or AuditService(db)

    # =========================================================================
    # AUDIT LOGGING HELPER
    # =========================================================================
    def _audit(
        self,
        actor: CurrentUser,
        action: str,
        entity_name: str,
        entity_id: str,
        target_info: Optional[Dict[str, Any]] = None,
        request: Any = None
    ):
        try:
            self.audit_service.log(
                action=action,
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "entity": entity_name,
                    "entity_id": entity_id,
                    **(target_info or {})
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed for {action} on {entity_name} {entity_id}: {e}")

    # =========================================================================
    # CONCURRENCY-SAFE CODE GENERATOR
    # =========================================================================
    def _generate_catalogue_code(self, prefix: str) -> str:
        """
        Concurrency-safe sequence generator for catalogue codes (e.g. WWT-001, PKG-001).
        Uses CrmSequence with row locking (with_for_update).
        """
        clean_prefix = prefix.strip().upper()
        entity_key = f"CAT_{clean_prefix}"

        seq = self.db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()
        if not seq:
            max_num = 0
            if clean_prefix == "PKG":
                existing = self.db.query(Package.package_code).filter(
                    Package.package_code.like(f"{clean_prefix}-%")
                ).all()
                for (code_val,) in existing:
                    try:
                        num = int(code_val.split("-")[-1])
                        if num > max_num:
                            max_num = num
                    except Exception:
                        pass
            else:
                existing_services = self.db.query(Service.service_code).filter(
                    Service.service_code.like(f"{clean_prefix}-%")
                ).all()
                for (code_val,) in existing_services:
                    try:
                        num = int(code_val.split("-")[-1])
                        if num > max_num:
                            max_num = num
                    except Exception:
                        pass
            seq = CrmSequence(entity_name=entity_key, current_value=max_num)
            self.db.add(seq)
            self.db.flush()

        while True:
            seq.current_value += 1
            candidate = f"{clean_prefix}-{seq.current_value:03d}"
            if clean_prefix == "PKG":
                exists = self.db.query(Package).filter(Package.package_code == candidate).first()
            else:
                exists = self.db.query(Service).filter(Service.service_code == candidate).first()
            if not exists:
                break

        seq.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        return candidate

    # =========================================================================
    # CATEGORIES & SUBCATEGORIES
    # =========================================================================
    def list_categories(self, include_inactive: bool = False) -> List[ServiceCategory]:
        q = self.db.query(ServiceCategory).options(joinedload(ServiceCategory.services)).filter(ServiceCategory.is_deleted == False)
        if not include_inactive:
            q = q.filter(ServiceCategory.is_active == True)
        return q.order_by(ServiceCategory.code).all()

    def get_category(self, category_id: str) -> ServiceCategory:
        cat = self.db.query(ServiceCategory).filter(
            ServiceCategory.id == category_id,
            ServiceCategory.is_deleted == False
        ).first()
        if not cat:
            raise NotFoundError(f"Category '{category_id}' not found.")
        return cat

    def create_category(self, actor: CurrentUser, payload: ServiceCategoryCreate, request: Any = None) -> ServiceCategory:
        existing = self.db.query(ServiceCategory).filter(ServiceCategory.code == payload.code).first()
        if existing:
            if existing.is_deleted:
                # Reactivate previously soft-deleted category
                existing.is_deleted = False
                existing.name = payload.name.strip()
                existing.description = payload.description.strip() if payload.description else None
                existing.prefix = payload.prefix.strip().upper()
                existing.is_active = payload.isActive
                existing.updated_by_id = str(actor.id) if actor.id else None
                self.db.commit()
                self.db.refresh(existing)
                self._audit(actor, "CRM_CATALOGUE_CATEGORY_RESTORED", "ServiceCategory", existing.id, {"code": existing.code}, request)
                return existing
            raise ConflictError(f"Category with code '{payload.code}' already exists.")

        cat = ServiceCategory(
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            prefix=payload.prefix.strip().upper(),
            is_active=payload.isActive,
            is_deleted=False,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(cat)
        self.db.commit()
        self.db.refresh(cat)
        self._audit(actor, "CRM_CATALOGUE_CATEGORY_CREATED", "ServiceCategory", cat.id, {"code": cat.code, "name": cat.name}, request)
        return cat

    def update_category(self, actor: CurrentUser, category_id: str, payload: ServiceCategoryUpdate, request: Any = None) -> ServiceCategory:
        cat = self.get_category(category_id)

        # Deactivation guard: cannot deactivate if associated subcategories have active services
        if payload.isActive is False and cat.is_active is True:
            active_services_count = self.db.query(Service).filter(
                Service.category_id == cat.id,
                Service.is_active == True,
                Service.is_deleted == False
            ).count()
            if active_services_count > 0:
                raise ValidationError(
                    f"Category '{cat.name}' cannot be deactivated because it has {active_services_count} active service(s). "
                    "Deactivate all associated services first."
                )

        changes = {}
        if payload.name is not None and payload.name.strip() != cat.name:
            changes["name"] = {"old": cat.name, "new": payload.name.strip()}
            cat.name = payload.name.strip()

        if payload.description is not None and payload.description != cat.description:
            changes["description"] = {"old": cat.description, "new": payload.description}
            cat.description = payload.description

        if payload.prefix is not None and payload.prefix.strip().upper() != cat.prefix:
            changes["prefix"] = {"old": cat.prefix, "new": payload.prefix.strip().upper()}
            cat.prefix = payload.prefix.strip().upper()

        if payload.isActive is not None and payload.isActive != cat.is_active:
            changes["is_active"] = {"old": cat.is_active, "new": payload.isActive}
            cat.is_active = payload.isActive

        cat.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(cat)
        self._audit(actor, "CRM_CATALOGUE_CATEGORY_UPDATED", "ServiceCategory", cat.id, changes, request)
        return cat

    def soft_delete_category(self, actor: CurrentUser, category_id: str, request: Any = None):
        cat = self.get_category(category_id)
        # Cannot soft delete if it has services
        service_count = self.db.query(Service).filter(
            Service.category_id == cat.id,
            Service.is_deleted == False
        ).count()
        if service_count > 0:
            raise ValidationError(
                f"Main category '{cat.name}' cannot be deleted while it contains {service_count} service(s). "
                "Delete or reassign all services first."
            )

        cat.is_deleted = True
        cat.is_active = False
        cat.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self._audit(actor, "CRM_CATALOGUE_CATEGORY_DELETED", "ServiceCategory", cat.id, {"code": cat.code}, request)

    # --- Subcategories (Deprecated - Main Category directly manages Services) ---
    def list_subcategories(self, category_id: Optional[str] = None, include_inactive: bool = False) -> List[Any]:
        return []

    # =========================================================================
    # MASTER DATA (BILLING UNITS, REPORTING UNITS, SAMPLE TYPES, METHODS, CURRENCIES)
    # =========================================================================
    def list_billing_units(self, include_inactive: bool = False) -> List[BillingUnit]:
        q = self.db.query(BillingUnit)
        if not include_inactive:
            q = q.filter(BillingUnit.is_active == True)
        return q.order_by(BillingUnit.code).all()

    def create_billing_unit(self, actor: CurrentUser, payload: BillingUnitCreate, request: Any = None) -> BillingUnit:
        code = payload.code.strip().upper()
        existing = self.db.query(BillingUnit).filter(BillingUnit.code == code).first()
        if existing:
            raise ConflictError(f"Billing unit '{code}' already exists.")
        unit = BillingUnit(
            code=code,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            is_active=payload.isActive,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(unit)
        self.db.commit()
        self.db.refresh(unit)
        self._audit(actor, "CRM_CATALOGUE_BILLING_UNIT_CREATED", "BillingUnit", unit.id, {"code": unit.code}, request)
        return unit

    def update_billing_unit(self, actor: CurrentUser, unit_id: str, payload: BillingUnitUpdate, request: Any = None) -> BillingUnit:
        unit = self.db.query(BillingUnit).filter(BillingUnit.id == unit_id).first()
        if not unit:
            raise NotFoundError(f"Billing unit '{unit_id}' not found.")
        if payload.name is not None:
            unit.name = payload.name.strip()
        if payload.description is not None:
            unit.description = payload.description
        if payload.isActive is not None:
            unit.is_active = payload.isActive
        unit.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(unit)
        self._audit(actor, "CRM_CATALOGUE_BILLING_UNIT_UPDATED", "BillingUnit", unit.id, {"code": unit.code}, request)
        return unit

    # Reporting Units
    def list_reporting_units(self, include_inactive: bool = False) -> List[ReportingUnit]:
        q = self.db.query(ReportingUnit)
        if not include_inactive:
            q = q.filter(ReportingUnit.is_active == True)
        return q.order_by(ReportingUnit.code).all()

    def create_reporting_unit(self, actor: CurrentUser, payload: ReportingUnitCreate, request: Any = None) -> ReportingUnit:
        code = payload.code.strip().upper()
        existing = self.db.query(ReportingUnit).filter(ReportingUnit.code == code).first()
        if existing:
            raise ConflictError(f"Reporting unit '{code}' already exists.")
        ru = ReportingUnit(
            code=code,
            name=payload.name.strip(),
            symbol=payload.symbol.strip(),
            description=payload.description.strip() if payload.description else None,
            is_active=payload.isActive,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(ru)
        self.db.commit()
        self.db.refresh(ru)
        self._audit(actor, "CRM_CATALOGUE_REPORTING_UNIT_CREATED", "ReportingUnit", ru.id, {"code": ru.code}, request)
        return ru

    def update_reporting_unit(self, actor: CurrentUser, unit_id: str, payload: ReportingUnitUpdate, request: Any = None) -> ReportingUnit:
        ru = self.db.query(ReportingUnit).filter(ReportingUnit.id == unit_id).first()
        if not ru:
            raise NotFoundError(f"Reporting unit '{unit_id}' not found.")
        if payload.name is not None:
            ru.name = payload.name.strip()
        if payload.symbol is not None:
            ru.symbol = payload.symbol.strip()
        if payload.description is not None:
            ru.description = payload.description
        if payload.isActive is not None:
            ru.is_active = payload.isActive
        ru.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(ru)
        self._audit(actor, "CRM_CATALOGUE_REPORTING_UNIT_UPDATED", "ReportingUnit", ru.id, {"code": ru.code}, request)
        return ru

    # Sample Types
    def list_sample_types(self, include_inactive: bool = False) -> List[SampleType]:
        q = self.db.query(SampleType)
        if not include_inactive:
            q = q.filter(SampleType.is_active == True)
        return q.order_by(SampleType.code).all()

    def create_sample_type(self, actor: CurrentUser, payload: SampleTypeCreate, request: Any = None) -> SampleType:
        code = payload.code.strip().upper()
        existing = self.db.query(SampleType).filter(SampleType.code == code).first()
        if existing:
            raise ConflictError(f"Sample type '{code}' already exists.")
        st = SampleType(
            code=code,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            is_active=payload.isActive,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(st)
        self.db.commit()
        self.db.refresh(st)
        self._audit(actor, "CRM_CATALOGUE_SAMPLE_TYPE_CREATED", "SampleType", st.id, {"code": st.code}, request)
        return st

    def update_sample_type(self, actor: CurrentUser, sample_type_id: str, payload: SampleTypeUpdate, request: Any = None) -> SampleType:
        st = self.db.query(SampleType).filter(SampleType.id == sample_type_id).first()
        if not st:
            raise NotFoundError(f"Sample type '{sample_type_id}' not found.")
        if payload.name is not None:
            st.name = payload.name.strip()
        if payload.description is not None:
            st.description = payload.description
        if payload.isActive is not None:
            st.is_active = payload.isActive
        st.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(st)
        self._audit(actor, "CRM_CATALOGUE_SAMPLE_TYPE_UPDATED", "SampleType", st.id, {"code": st.code}, request)
        return st

    # Testing Methods
    def list_testing_methods(self, include_inactive: bool = False) -> List[TestingMethod]:
        q = self.db.query(TestingMethod)
        if not include_inactive:
            q = q.filter(TestingMethod.is_active == True)
        return q.order_by(TestingMethod.code).all()

    def create_testing_method(self, actor: CurrentUser, payload: TestingMethodCreate, request: Any = None) -> TestingMethod:
        code = payload.code.strip().upper()
        existing = self.db.query(TestingMethod).filter(TestingMethod.code == code).first()
        if existing:
            raise ConflictError(f"Testing method '{code}' already exists.")
        tm = TestingMethod(
            code=code,
            method_name=payload.methodName.strip(),
            standard_reference=payload.standardReference.strip() if payload.standardReference else None,
            revision=payload.revision.strip() if payload.revision else None,
            description=payload.description.strip() if payload.description else None,
            is_active=payload.isActive,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(tm)
        self.db.commit()
        self.db.refresh(tm)
        self._audit(actor, "CRM_CATALOGUE_TESTING_METHOD_CREATED", "TestingMethod", tm.id, {"code": tm.code}, request)
        return tm

    def update_testing_method(self, actor: CurrentUser, method_id: str, payload: TestingMethodUpdate, request: Any = None) -> TestingMethod:
        tm = self.db.query(TestingMethod).filter(TestingMethod.id == method_id).first()
        if not tm:
            raise NotFoundError(f"Testing method '{method_id}' not found.")
        if payload.methodName is not None:
            tm.method_name = payload.methodName.strip()
        if payload.standardReference is not None:
            tm.standard_reference = payload.standardReference.strip() if payload.standardReference else None
        if payload.revision is not None:
            tm.revision = payload.revision.strip() if payload.revision else None
        if payload.description is not None:
            tm.description = payload.description
        if payload.isActive is not None:
            tm.is_active = payload.isActive
        tm.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(tm)
        self._audit(actor, "CRM_CATALOGUE_TESTING_METHOD_UPDATED", "TestingMethod", tm.id, {"code": tm.code}, request)
        return tm

    # Currencies
    def list_currencies(self, include_inactive: bool = False) -> List[Currency]:
        q = self.db.query(Currency)
        if not include_inactive:
            q = q.filter(Currency.is_active == True)
        return q.order_by(desc(Currency.is_default), Currency.code).all()

    def get_default_currency(self) -> Currency:
        curr = self.db.query(Currency).filter(Currency.is_default == True, Currency.is_active == True).first()
        if not curr:
            curr = self.db.query(Currency).filter(Currency.code == "INR").first()
        if not curr:
            curr = Currency(code="INR", name="Indian Rupee", symbol="₹", is_default=True, is_active=True)
            self.db.add(curr)
            self.db.commit()
            self.db.refresh(curr)
        return curr

    def create_currency(self, actor: CurrentUser, payload: CurrencyCreate, request: Any = None) -> Currency:
        code = payload.code.strip().upper()
        existing = self.db.query(Currency).filter(Currency.code == code).first()
        if existing:
            raise ConflictError(f"Currency '{code}' already exists.")
        if payload.isDefault:
            # Clear default from other currencies
            self.db.query(Currency).filter(Currency.is_default == True).update({"is_default": False})

        curr = Currency(
            code=code,
            name=payload.name.strip(),
            symbol=payload.symbol.strip(),
            is_default=payload.isDefault,
            is_active=payload.isActive,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(curr)
        self.db.commit()
        self.db.refresh(curr)
        self._audit(actor, "CRM_CATALOGUE_CURRENCY_CREATED", "Currency", curr.id, {"code": curr.code}, request)
        return curr

    def update_currency(self, actor: CurrentUser, currency_id: str, payload: CurrencyUpdate, request: Any = None) -> Currency:
        curr = self.db.query(Currency).filter(Currency.id == currency_id).first()
        if not curr:
            raise NotFoundError(f"Currency '{currency_id}' not found.")
        if payload.name is not None:
            curr.name = payload.name.strip()
        if payload.symbol is not None:
            curr.symbol = payload.symbol.strip()
        if payload.isDefault is True:
            self.db.query(Currency).filter(Currency.is_default == True).update({"is_default": False})
            curr.is_default = True
        elif payload.isDefault is False:
            curr.is_default = False
        if payload.isActive is not None:
            curr.is_active = payload.isActive
        curr.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(curr)
        self._audit(actor, "CRM_CATALOGUE_CURRENCY_UPDATED", "Currency", curr.id, {"code": curr.code}, request)
        return curr

    # Tax Configurations
    def list_tax_configurations(self, include_inactive: bool = False) -> List[TaxConfiguration]:
        q = self.db.query(TaxConfiguration).options(joinedload(TaxConfiguration.rates))
        if not include_inactive:
            q = q.filter(TaxConfiguration.is_active == True)
        return q.order_by(TaxConfiguration.code).all()

    def get_tax_configuration(self, config_id: str) -> TaxConfiguration:
        tc = self.db.query(TaxConfiguration).options(joinedload(TaxConfiguration.rates)).filter(
            TaxConfiguration.id == config_id
        ).first()
        if not tc:
            raise NotFoundError(f"Tax configuration '{config_id}' not found.")
        return tc

    def create_tax_configuration(self, actor: CurrentUser, payload: TaxConfigurationCreate, request: Any = None) -> TaxConfiguration:
        code = payload.code.strip().upper()
        existing = self.db.query(TaxConfiguration).filter(TaxConfiguration.code == code).first()
        if existing:
            raise ConflictError(f"Tax configuration with code '{code}' already exists.")

        tc = TaxConfiguration(
            code=code,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            tax_type=payload.taxType.strip().upper(),
            is_active=payload.isActive,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(tc)
        self.db.flush()

        for r_in in payload.rates:
            c_name = getattr(r_in, "componentName", None) or getattr(r_in, "rateName", "") or ""
            r_pct = getattr(r_in, "ratePercentage", None) if getattr(r_in, "ratePercentage", None) is not None else getattr(r_in, "percentage", Decimal("0.0"))
            rate = TaxRate(
                configuration_id=tc.id,
                component_name=c_name.strip().upper(),
                rate_percentage=r_pct,
                is_active=True
            )
            self.db.add(rate)

        self.db.commit()
        self.db.refresh(tc)
        self._audit(actor, "CRM_CATALOGUE_TAX_CONFIG_CREATED", "TaxConfiguration", tc.id, {"code": tc.code}, request)
        return tc

    def update_tax_configuration(self, actor: CurrentUser, config_id: str, payload: TaxConfigurationUpdate, request: Any = None) -> TaxConfiguration:
        tc = self.get_tax_configuration(config_id)
        if payload.name is not None:
            tc.name = payload.name.strip()
        if payload.description is not None:
            tc.description = payload.description
        if payload.taxType is not None:
            tc.tax_type = payload.taxType.strip().upper()
        if payload.isActive is not None:
            tc.is_active = payload.isActive

        if payload.rates is not None:
            # Replace rates
            self.db.query(TaxRate).filter(TaxRate.configuration_id == tc.id).delete()
            for r_in in payload.rates:
                c_name = getattr(r_in, "componentName", None) or getattr(r_in, "rateName", "") or ""
                r_pct = getattr(r_in, "ratePercentage", None) if getattr(r_in, "ratePercentage", None) is not None else getattr(r_in, "percentage", Decimal("0.0"))
                rate = TaxRate(
                    configuration_id=tc.id,
                    component_name=c_name.strip().upper(),
                    rate_percentage=r_pct,
                    is_active=True
                )
                self.db.add(rate)

        tc.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(tc)
        self._audit(actor, "CRM_CATALOGUE_TAX_CONFIG_UPDATED", "TaxConfiguration", tc.id, {"code": tc.code}, request)
        return tc

    # =========================================================================
    # SERVICES
    # =========================================================================
    def list_services(
        self,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_addon_eligible: Optional[bool] = None,
        billing_unit_id: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        page: int = 1,
        page_size: int = 25
    ) -> Tuple[List[Service], int]:
        q = self.db.query(Service).filter(Service.is_deleted == False)

        if category_id:
            q = q.filter(Service.category_id == category_id)
        if billing_unit_id:
            q = q.filter(Service.billing_unit_id == billing_unit_id)
        if is_active is not None:
            q = q.filter(Service.is_active == is_active)
        if is_addon_eligible is not None:
            q = q.filter(Service.is_addon_eligible == is_addon_eligible)
        if min_price is not None:
            q = q.filter(Service.standard_price >= min_price)
        if max_price is not None:
            q = q.filter(Service.standard_price <= max_price)
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(or_(
                Service.service_code.ilike(term),
                Service.name.ilike(term),
                Service.description.ilike(term)
            ))

        total = q.count()
        offset = (max(1, page) - 1) * page_size
        items = q.options(
            joinedload(Service.category),
            joinedload(Service.billing_unit),
            joinedload(Service.currency),
            joinedload(Service.sample_types).joinedload(ServiceSampleType.sample_type),
            joinedload(Service.testing_methods).joinedload(ServiceTestingMethod.testing_method),
            joinedload(Service.reporting_parameters).joinedload(ServiceReportingParameter.reporting_unit),
            joinedload(Service.reporting_parameters).joinedload(ServiceReportingParameter.testing_method)
        ).order_by(Service.service_code).offset(offset).limit(page_size).all()

        return items, total

    def get_service(self, service_id: str, as_of_date: Optional[py_date] = None) -> Service:
        svc = self.db.query(Service).options(
            joinedload(Service.category),
            joinedload(Service.billing_unit),
            joinedload(Service.currency),
            joinedload(Service.sample_types).joinedload(ServiceSampleType.sample_type),
            joinedload(Service.testing_methods).joinedload(ServiceTestingMethod.testing_method),
            joinedload(Service.reporting_parameters).joinedload(ServiceReportingParameter.reporting_unit),
            joinedload(Service.reporting_parameters).joinedload(ServiceReportingParameter.testing_method),
            joinedload(Service.price_history)
        ).filter(
            or_(Service.id == service_id, Service.service_code == service_id),
            Service.is_deleted == False
        ).first()

        if not svc:
            raise NotFoundError(f"Service '{service_id}' not found.")

        # Calculate effective price for effective-dated pricing
        svc.effective_price = self.get_effective_service_price(svc.id, as_of_date or py_date.today())
        return svc

    def get_effective_service_price(self, service_id: str, as_of_date: py_date) -> Decimal:
        """
        Calculates the applicable service price as of quotation creation date.
        Selects the latest price version whose effective date is on or before as_of_date.
        """
        history_entry = self.db.query(ServicePriceHistory).filter(
            ServicePriceHistory.service_id == service_id,
            ServicePriceHistory.effective_date <= as_of_date
        ).order_by(desc(ServicePriceHistory.effective_date), desc(ServicePriceHistory.created_at)).first()

        if history_entry:
            return Decimal(str(history_entry.price))

        svc = self.db.query(Service).filter(Service.id == service_id).first()
        return Decimal(str(svc.standard_price)) if svc else Decimal("0.0")

    def create_service(self, actor: CurrentUser, payload: ServiceCreate, request: Any = None) -> Service:
        # Rule 1: A service must belong to an active main category
        category = self.get_category(payload.categoryId)
        if not category.is_active:
            raise ValidationError(f"Cannot create service in inactive main category '{category.name}'.")

        # Rule 4: Each service must have exactly one billing unit
        billing_unit = self.db.query(BillingUnit).filter(BillingUnit.id == payload.billingUnitId).first()
        if not billing_unit or not billing_unit.is_active:
            raise ValidationError(f"Active billing unit is required.")

        # Currency
        currency_id = payload.currencyId
        if currency_id:
            currency = self.db.query(Currency).filter(Currency.id == currency_id).first()
            if not currency or not currency.is_active:
                raise ValidationError("Active currency is required.")
        else:
            currency = self.get_default_currency()

        # Rule 5: Minimum billing quantity must be a positive integer
        if payload.minimumBillingQuantity < 1:
            raise ValidationError("Minimum billing quantity must be a positive integer greater than or equal to 1.")

        # Rule 7: Auto-generate concurrency-safe category-based service code
        service_code = self._generate_catalogue_code(category.prefix)
        eff_date = payload.effectiveDate or py_date.today()

        svc = Service(
            service_code=service_code,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            category_id=category.id,
            billing_unit_id=billing_unit.id,
            currency_id=currency.id,
            minimum_billing_quantity=payload.minimumBillingQuantity,
            standard_price=payload.standardPrice,
            effective_date=eff_date,
            is_active=payload.isActive,
            is_deleted=False,
            is_addon_eligible=payload.isAddonEligible,
            can_have_addons=payload.canHaveAddons,
            source_note=payload.sourceNote.strip() if payload.sourceNote else None,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(svc)
        self.db.flush()

        # Record initial price history entry
        price_history = ServicePriceHistory(
            service_id=svc.id,
            price=payload.standardPrice,
            currency_id=currency.id,
            effective_date=eff_date,
            changed_by_id=str(actor.id) if actor.id else None,
            reason="Initial standard catalogue price setup."
        )
        self.db.add(price_history)

        # Sample Types
        for st_id in payload.sampleTypeIds:
            st = self.db.query(SampleType).filter(SampleType.id == st_id).first()
            if st and st.is_active:
                self.db.add(ServiceSampleType(service_id=svc.id, sample_type_id=st.id))

        # Testing Methods (at most one default)
        tms = []
        if getattr(payload, "testingMethods", None):
            tms = payload.testingMethods
        elif getattr(payload, "testingMethodIds", None):
            for tm_id in payload.testingMethodIds:
                tms.append(ServiceTestingMethodInput(testingMethodId=tm_id, isDefault=False))

        default_method_assigned = False
        for tm_in in tms:
            tm = self.db.query(TestingMethod).filter(TestingMethod.id == tm_in.testingMethodId).first()
            if not tm or not tm.is_active:
                continue
            is_def = getattr(tm_in, "isDefault", False) and not default_method_assigned
            if is_def:
                default_method_assigned = True
            self.db.add(ServiceTestingMethod(service_id=svc.id, testing_method_id=tm.id, is_default=is_def))

        # Reporting Parameters
        for rp_in in payload.reportingParameters:
            ru = self.db.query(ReportingUnit).filter(ReportingUnit.id == rp_in.reportingUnitId).first()
            if not ru or not ru.is_active:
                continue
            self.db.add(ServiceReportingParameter(
                service_id=svc.id,
                testing_method_id=rp_in.testingMethodId,
                parameter_name=rp_in.parameterName.strip(),
                reporting_unit_id=ru.id,
                min_range=rp_in.minRange,
                max_range=rp_in.maxRange,
                is_active=rp_in.isActive
            ))

        self.db.commit()
        self.db.refresh(svc)
        self._audit(actor, "CRM_CATALOGUE_SERVICE_CREATED", "Service", svc.id, {
            "service_code": svc.service_code,
            "name": svc.name,
            "standard_price": float(svc.standard_price)
        }, request)
        return self.get_service(svc.id)

    def update_service(self, actor: CurrentUser, service_id: str, payload: ServiceUpdate, request: Any = None) -> Service:
        svc = self.get_service(service_id)
        changes = {}

        if payload.name is not None and payload.name.strip() != svc.name:
            changes["name"] = {"old": svc.name, "new": payload.name.strip()}
            svc.name = payload.name.strip()

        if payload.description is not None and payload.description != svc.description:
            changes["description"] = {"old": svc.description, "new": payload.description}
            svc.description = payload.description

        # Category reassignment
        if payload.categoryId and payload.categoryId != svc.category_id:
            cat = self.get_category(payload.categoryId)
            if not cat.is_active:
                raise ValidationError(f"Cannot assign inactive category '{cat.name}'.")
            changes["category_id"] = {"old": svc.category_id, "new": cat.id}
            svc.category_id = cat.id

        if payload.billingUnitId is not None and payload.billingUnitId != svc.billing_unit_id:
            bu = self.db.query(BillingUnit).filter(BillingUnit.id == payload.billingUnitId).first()
            if not bu or not bu.is_active:
                raise ValidationError("Active billing unit required.")
            changes["billing_unit_id"] = {"old": svc.billing_unit_id, "new": bu.id}
            svc.billing_unit_id = bu.id

        if payload.currencyId is not None and payload.currencyId != svc.currency_id:
            curr = self.db.query(Currency).filter(Currency.id == payload.currencyId).first()
            if not curr or not curr.is_active:
                raise ValidationError("Active currency required.")
            changes["currency_id"] = {"old": svc.currency_id, "new": curr.id}
            svc.currency_id = curr.id

        if payload.minimumBillingQuantity is not None:
            if payload.minimumBillingQuantity < 1:
                raise ValidationError("Minimum billing quantity must be a positive integer greater than or equal to 1.")
            svc.minimum_billing_quantity = payload.minimumBillingQuantity

        # Effective-dated standard price change
        if payload.standardPrice is not None and Decimal(str(payload.standardPrice)) != Decimal(str(svc.standard_price)):
            new_eff_date = payload.effectiveDate or py_date.today()
            changes["standard_price"] = {"old": float(svc.standard_price), "new": float(payload.standardPrice), "effective_date": new_eff_date.isoformat()}
            svc.standard_price = payload.standardPrice
            svc.effective_date = new_eff_date

            # Add to price history
            history_entry = ServicePriceHistory(
                service_id=svc.id,
                price=payload.standardPrice,
                currency_id=svc.currency_id,
                effective_date=new_eff_date,
                changed_by_id=str(actor.id) if actor.id else None,
                reason=getattr(payload, "changeReason", None) or getattr(payload, "priceChangeReason", None) or "Admin price update"
            )
            self.db.add(history_entry)

        if payload.isActive is not None and payload.isActive != svc.is_active:
            changes["is_active"] = {"old": svc.is_active, "new": payload.isActive}
            svc.is_active = payload.isActive

        if payload.isAddonEligible is not None:
            svc.is_addon_eligible = payload.isAddonEligible

        if payload.canHaveAddons is not None:
            svc.can_have_addons = payload.canHaveAddons

        if payload.sourceNote is not None:
            svc.source_note = payload.sourceNote.strip() if payload.sourceNote else None

        # Sample Types
        if payload.sampleTypeIds is not None:
            self.db.query(ServiceSampleType).filter(ServiceSampleType.service_id == svc.id).delete()
            for st_id in payload.sampleTypeIds:
                st = self.db.query(SampleType).filter(SampleType.id == st_id).first()
                if st and st.is_active:
                    self.db.add(ServiceSampleType(service_id=svc.id, sample_type_id=st.id))

        # Testing Methods (at most one default)
        if getattr(payload, "testingMethods", None) is not None or getattr(payload, "testingMethodIds", None) is not None:
            self.db.query(ServiceTestingMethod).filter(ServiceTestingMethod.service_id == svc.id).delete()
            tms = []
            if getattr(payload, "testingMethods", None):
                tms = payload.testingMethods
            elif getattr(payload, "testingMethodIds", None):
                for tm_id in payload.testingMethodIds:
                    tms.append(ServiceTestingMethodInput(testingMethodId=tm_id, isDefault=False))

            default_assigned = False
            for tm_in in tms:
                tm = self.db.query(TestingMethod).filter(TestingMethod.id == tm_in.testingMethodId).first()
                if not tm or not tm.is_active:
                    continue
                is_def = getattr(tm_in, "isDefault", False) and not default_assigned
                if is_def:
                    default_assigned = True
                self.db.add(ServiceTestingMethod(service_id=svc.id, testing_method_id=tm.id, is_default=is_def))

        # Reporting Parameters
        if payload.reportingParameters is not None:
            self.db.query(ServiceReportingParameter).filter(ServiceReportingParameter.service_id == svc.id).delete()
            for rp_in in payload.reportingParameters:
                ru = self.db.query(ReportingUnit).filter(ReportingUnit.id == rp_in.reportingUnitId).first()
                if not ru or not ru.is_active:
                    continue
                self.db.add(ServiceReportingParameter(
                    service_id=svc.id,
                    testing_method_id=rp_in.testingMethodId,
                    parameter_name=rp_in.parameterName.strip(),
                    reporting_unit_id=ru.id,
                    min_range=rp_in.minRange,
                    max_range=rp_in.maxRange,
                    is_active=rp_in.isActive
                ))

        svc.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(svc)
        self._audit(actor, "CRM_CATALOGUE_SERVICE_UPDATED", "Service", svc.id, changes, request)
        return self.get_service(svc.id)

    def soft_delete_service(self, actor: CurrentUser, service_id: str, request: Any = None):
        svc = self.get_service(service_id)
        # Check if service is currently part of any active package
        active_pkg_comp = self.db.query(PackageComponent).join(
            PackageVersion, PackageComponent.package_version_id == PackageVersion.id
        ).join(
            Package, PackageVersion.package_id == Package.id
        ).filter(
            PackageComponent.service_id == svc.id,
            Package.is_active == True,
            Package.is_deleted == False
        ).count()

        if active_pkg_comp > 0:
            raise ValidationError(
                f"Service '{svc.name}' cannot be deleted because it is an active component in {active_pkg_comp} package(s). "
                "Remove the service from packages first."
            )

        svc.is_deleted = True
        svc.is_active = False
        svc.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self._audit(actor, "CRM_CATALOGUE_SERVICE_DELETED", "Service", svc.id, {"service_code": svc.service_code}, request)

    # =========================================================================
    # PACKAGES & PACKAGE VERSIONS
    # =========================================================================
    def list_packages(
        self,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 25
    ) -> Tuple[List[Package], int]:
        q = self.db.query(Package).filter(Package.is_deleted == False)

        if category_id:
            q = q.filter(Package.category_id == category_id)
        if is_active is not None:
            q = q.filter(Package.is_active == is_active)
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(or_(
                Package.package_code.ilike(term),
                Package.name.ilike(term),
                Package.description.ilike(term)
            ))

        total = q.count()
        offset = (max(1, page) - 1) * page_size
        items = q.options(
            joinedload(Package.category),
            joinedload(Package.currency),
            joinedload(Package.versions).joinedload(PackageVersion.components).joinedload(PackageComponent.service),
            joinedload(Package.versions).joinedload(PackageVersion.addon_configurations).joinedload(PackageAddOnConfiguration.addon_service)
        ).order_by(Package.package_code).offset(offset).limit(page_size).all()

        return items, total

    def get_package(self, package_id: str) -> Package:
        pkg = self.db.query(Package).options(
            joinedload(Package.category),
            joinedload(Package.currency),
            joinedload(Package.versions).joinedload(PackageVersion.components).joinedload(PackageComponent.service),
            joinedload(Package.versions).joinedload(PackageVersion.addon_configurations).joinedload(PackageAddOnConfiguration.addon_service)
        ).filter(
            or_(Package.id == package_id, Package.package_code == package_id),
            Package.is_deleted == False
        ).first()

        if not pkg:
            raise NotFoundError(f"Package '{package_id}' not found.")
        return pkg

    def create_package(self, actor: CurrentUser, payload: PackageCreate, request: Any = None) -> Package:
        # Rule 10: Must contain at least one valid component service
        if not payload.components or len(payload.components) == 0:
            raise ValidationError("A package must contain at least one valid catalogue service component.")

        # Currency
        if payload.currencyId:
            currency = self.db.query(Currency).filter(Currency.id == payload.currencyId).first()
            if not currency or not currency.is_active:
                raise ValidationError("Active currency required.")
        else:
            currency = self.get_default_currency()

        if getattr(payload, "code", None) and payload.code.strip():
            package_code = payload.code.strip().upper()
            existing_pkg = self.db.query(Package).filter(Package.package_code == package_code).first()
            if existing_pkg:
                raise ConflictError(f"Package code '{package_code}' already exists.")
        else:
            package_code = self._generate_catalogue_code("PKG")

        pkg = Package(
            package_code=package_code,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            category_id=payload.categoryId,
            currency_id=currency.id,
            fixed_package_price=payload.fixedPackagePrice,
            current_version=1,
            is_active=payload.isActive,
            is_deleted=False,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(pkg)
        self.db.flush()

        # Create Version 1
        ver = PackageVersion(
            package_id=pkg.id,
            version_number=1,
            fixed_price=payload.fixedPackagePrice,
            currency_id=currency.id,
            change_summary="Initial Package Version v1",
            is_active=True,
            effective_date=py_date.today(),
            created_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(ver)
        self.db.flush()

        # Add Components
        for comp_in in payload.components:
            svc = self.get_service(comp_in.serviceId)
            if not svc.is_active:
                raise ValidationError(f"Cannot add inactive service '{svc.name}' to a package.")
            if comp_in.quantity < 1:
                raise ValidationError("Component quantity must be a positive integer.")

            self.db.add(PackageComponent(
                package_version_id=ver.id,
                service_id=svc.id,
                quantity=comp_in.quantity,
                reference_price=svc.standard_price
            ))

        # Add Add-on Configurations
        for addon_in in payload.addonConfigurations:
            addon_svc = self.get_service(addon_in.addonServiceId)
            if not addon_svc.is_addon_eligible:
                raise ValidationError(f"Service '{addon_svc.name}' is not marked as add-on eligible.")
            if addon_in.defaultQuantity < 1:
                raise ValidationError("Add-on quantity must be a positive integer.")

            self.db.add(PackageAddOnConfiguration(
                package_version_id=ver.id,
                addon_service_id=addon_svc.id,
                default_quantity=addon_in.defaultQuantity,
                override_price=addon_in.overridePrice,
                is_mandatory=addon_in.isMandatory
            ))

        self.db.commit()
        self.db.refresh(pkg)
        self._audit(actor, "CRM_CATALOGUE_PACKAGE_CREATED", "Package", pkg.id, {
            "package_code": pkg.package_code,
            "name": pkg.name,
            "price": float(pkg.fixed_package_price)
        }, request)
        return self.get_package(pkg.id)

    def create_new_package_version(
        self,
        actor: CurrentUser,
        package_id: str,
        payload: PackageNewVersionCreate,
        request: Any = None
    ) -> PackageVersion:
        """
        Rule: Component changes create a new package version.
        Preserves previous package versions so historical quotations remain accurate.
        """
        pkg = self.get_package(package_id)

        if not payload.components or len(payload.components) == 0:
            raise ValidationError("A package version must contain at least one valid component service.")

        new_version_num = pkg.current_version + 1

        # Deactivate older versions if requested
        self.db.query(PackageVersion).filter(
            PackageVersion.package_id == pkg.id
        ).update({"is_active": False})

        ver = PackageVersion(
            package_id=pkg.id,
            version_number=new_version_num,
            fixed_price=payload.fixedPackagePrice,
            currency_id=pkg.currency_id,
            change_summary=payload.changeSummary or f"Package version {new_version_num}",
            is_active=True,
            effective_date=payload.effectiveDate or py_date.today(),
            created_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(ver)
        self.db.flush()

        for comp_in in payload.components:
            svc = self.get_service(comp_in.serviceId)
            if not svc.is_active:
                raise ValidationError(f"Cannot add inactive service '{svc.name}' to package version.")
            if comp_in.quantity < 1:
                raise ValidationError("Component quantity must be a positive integer.")

            self.db.add(PackageComponent(
                package_version_id=ver.id,
                service_id=svc.id,
                quantity=comp_in.quantity,
                reference_price=svc.standard_price
            ))

        for addon_in in payload.addonConfigurations:
            addon_svc = self.get_service(addon_in.addonServiceId)
            if not addon_svc.is_addon_eligible:
                raise ValidationError(f"Service '{addon_svc.name}' is not marked as add-on eligible.")
            if addon_in.defaultQuantity < 1:
                raise ValidationError("Add-on quantity must be a positive integer.")

            self.db.add(PackageAddOnConfiguration(
                package_version_id=ver.id,
                addon_service_id=addon_svc.id,
                default_quantity=addon_in.defaultQuantity,
                override_price=addon_in.overridePrice,
                is_mandatory=addon_in.isMandatory
            ))

        pkg.current_version = new_version_num
        pkg.fixed_package_price = payload.fixedPackagePrice
        pkg.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(ver)
        self._audit(actor, "CRM_CATALOGUE_PACKAGE_VERSION_CREATED", "PackageVersion", ver.id, {
            "package_code": pkg.package_code,
            "version": new_version_num,
            "price": float(ver.fixed_price)
        }, request)
        return ver

    def update_package_metadata(self, actor: CurrentUser, package_id: str, payload: PackageUpdate, request: Any = None) -> Package:
        pkg = self.get_package(package_id)
        changes = {}

        if payload.name is not None and payload.name.strip() != pkg.name:
            changes["name"] = {"old": pkg.name, "new": payload.name.strip()}
            pkg.name = payload.name.strip()

        if payload.description is not None and payload.description != pkg.description:
            changes["description"] = {"old": pkg.description, "new": payload.description}
            pkg.description = payload.description

        if payload.categoryId is not None:
            pkg.category_id = payload.categoryId

        if payload.isActive is not None and payload.isActive != pkg.is_active:
            changes["is_active"] = {"old": pkg.is_active, "new": payload.isActive}
            pkg.is_active = payload.isActive

        pkg.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(pkg)
        self._audit(actor, "CRM_CATALOGUE_PACKAGE_UPDATED", "Package", pkg.id, changes, request)
        return self.get_package(pkg.id)

    # =========================================================================
    # QUOTATION ITEM CREATION & TAX SNAPSHOTS
    # =========================================================================
    def calculate_tax(
        self,
        taxable_amount: Decimal,
        tax_config: Optional[TaxConfiguration]
    ) -> Dict[str, Any]:
        """
        Decimal-safe calculation of CGST, SGST, IGST and final totals.
        """
        result = {
            "tax_type": tax_config.tax_type if tax_config else "EXEMPT",
            "cgst_rate": Decimal("0.0"),
            "cgst_amount": Decimal("0.0"),
            "sgst_rate": Decimal("0.0"),
            "sgst_amount": Decimal("0.0"),
            "igst_rate": Decimal("0.0"),
            "igst_amount": Decimal("0.0"),
            "total_tax": Decimal("0.0"),
            "final_total": taxable_amount
        }

        if not tax_config or not tax_config.rates:
            return result

        total_tax = Decimal("0.0")
        for rate in tax_config.rates:
            if not rate.is_active:
                continue
            rate_pct = Decimal(str(rate.rate_percentage))
            comp_amount = (taxable_amount * (rate_pct / Decimal("100.0"))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            comp_name = rate.component_name.upper()

            if "CGST" in comp_name:
                result["cgst_rate"] = rate_pct
                result["cgst_amount"] = comp_amount
            elif "SGST" in comp_name or "UTGST" in comp_name:
                result["sgst_rate"] = rate_pct
                result["sgst_amount"] = comp_amount
            elif "IGST" in comp_name:
                result["igst_rate"] = rate_pct
                result["igst_amount"] = comp_amount

            total_tax += comp_amount

        result["total_tax"] = total_tax
        result["final_total"] = taxable_amount + total_tax
        return result

    def add_item_to_quotation(
        self,
        actor: CurrentUser,
        quotation_id: str,
        payload: QuotationItemInput,
        request: Any = None
    ) -> OpportunityQuotationItem:
        quotation = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.id == quotation_id
        ).first()
        if not quotation:
            raise NotFoundError(f"Quotation '{quotation_id}' not found.")

        if quotation.status in ("Accepted", "Superseded"):
            raise ValidationError(f"Cannot add items to quotation in '{quotation.status}' status.")

        quotation_date = quotation.quotation_date or py_date.today()

        # Tax configuration
        tax_config = None
        if payload.taxConfigurationId:
            tax_config = self.get_tax_configuration(payload.taxConfigurationId)
        elif quotation.tax_type in ("INTRA_STATE", "INTER_STATE"):
            tax_config = self.db.query(TaxConfiguration).filter(
                TaxConfiguration.tax_type == quotation.tax_type,
                TaxConfiguration.is_active == True
            ).first()

        if payload.itemType == "SERVICE":
            if not payload.serviceId:
                raise ValidationError("Service ID is mandatory for service line items.")
            svc = self.get_service(payload.serviceId, as_of_date=quotation_date)

            if payload.quantity < svc.minimum_billing_quantity:
                raise ValidationError(
                    f"Quantity {payload.quantity} is below minimum billing quantity {svc.minimum_billing_quantity} for '{svc.name}'."
                )

            std_price = svc.effective_price or svc.standard_price
            unit_price = getattr(payload, "unitPrice", None) if getattr(payload, "unitPrice", None) is not None else (getattr(payload, "negotiatedUnitPrice", None) if getattr(payload, "negotiatedUnitPrice", None) is not None else std_price)
            taxable_amount = Decimal(str(unit_price)) * Decimal(str(payload.quantity))

            tax_res = self.calculate_tax(taxable_amount, tax_config)

            # Testing method snapshot
            method_snapshot = None
            testing_method_id = getattr(payload, "testingMethodId", None)
            testing_method_name = getattr(payload, "testingMethod", None)

            if testing_method_id:
                tm = self.db.query(TestingMethod).filter(TestingMethod.id == testing_method_id).first()
                if tm:
                    method_snapshot = json.dumps({
                        "name": tm.method_name,
                        "standard": tm.standard_reference,
                        "revision": tm.revision
                    })
            elif testing_method_name:
                tm = self.db.query(TestingMethod).filter(
                    (TestingMethod.method_name == testing_method_name) | (TestingMethod.code == testing_method_name)
                ).first()
                if tm:
                    method_snapshot = json.dumps({
                        "name": tm.method_name,
                        "standard": tm.standard_reference,
                        "revision": tm.revision
                    })
                else:
                    method_snapshot = json.dumps({"name": testing_method_name})
            elif svc.testing_methods:
                def_method = next((m for m in svc.testing_methods if m.is_default), svc.testing_methods[0])
                if def_method and def_method.testing_method:
                    method_snapshot = json.dumps({
                        "name": def_method.testing_method.method_name,
                        "standard": def_method.testing_method.standard_reference,
                        "revision": def_method.testing_method.revision
                    })

            # Reporting parameters snapshot
            param_snapshots = []
            for rp in svc.reporting_parameters:
                param_snapshots.append({
                    "name": rp.parameter_name,
                    "unit": rp.reporting_unit.symbol if rp.reporting_unit else None,
                    "min": float(rp.min_range) if rp.min_range is not None else None,
                    "max": float(rp.max_range) if rp.max_range is not None else None
                })
            reporting_snapshot = json.dumps(param_snapshots) if param_snapshots else None

            item = OpportunityQuotationItem(
                quotation_id=quotation.id,
                item_type="SERVICE",
                service_id=svc.id,
                item_code=svc.service_code,
                item_name=svc.name,
                description=svc.description,
                billing_unit=svc.billing_unit.code if svc.billing_unit else None,
                quantity=payload.quantity,
                standard_price=std_price,
                unit_price=unit_price,
                total_price=taxable_amount,
                currency=svc.currency.code if svc.currency else "INR",
                testing_method_snapshot=method_snapshot,
                reporting_parameters_snapshot=reporting_snapshot,
                tax_configuration_id=tax_config.id if tax_config else None,
                tax_type=tax_res["tax_type"],
                taxable_amount=taxable_amount,
                cgst_rate=tax_res["cgst_rate"],
                cgst_amount=tax_res["cgst_amount"],
                sgst_rate=tax_res["sgst_rate"],
                sgst_amount=tax_res["sgst_amount"],
                igst_rate=tax_res["igst_rate"],
                igst_amount=tax_res["igst_amount"],
                total_tax=tax_res["total_tax"],
                final_total=tax_res["final_total"]
            )
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            self._audit(actor, "CRM_QUOTATION_ITEM_ADDED", "OpportunityQuotationItem", item.id, {
                "quotation_id": quotation.id,
                "item_code": item.item_code,
                "total": float(item.final_total)
            }, request)
            return item

        elif payload.itemType == "PACKAGE":
            if not payload.packageId:
                raise ValidationError("Package ID is mandatory for package line items.")
            pkg = self.get_package(payload.packageId)

            # Get latest active version or specified version
            if payload.packageVersionId:
                ver = next((v for v in pkg.versions if v.id == payload.packageVersionId), None)
                if not ver:
                    raise NotFoundError(f"Package version '{payload.packageVersionId}' not found.")
            else:
                ver = next((v for v in pkg.versions if v.is_active), None) or (pkg.versions[0] if pkg.versions else None)

            if not ver:
                raise ValidationError("Package has no active versions.")

            std_price = ver.fixed_price
            unit_price = payload.negotiatedUnitPrice if payload.negotiatedUnitPrice is not None else std_price
            taxable_amount = Decimal(str(unit_price)) * Decimal(str(payload.quantity))

            tax_res = self.calculate_tax(taxable_amount, tax_config)

            # Snapshot components with quantities multiplied by package quantity
            component_snapshots = []
            for comp in ver.components:
                svc = comp.service
                component_snapshots.append({
                    "service_id": comp.service_id,
                    "service_code": svc.service_code if svc else None,
                    "service_name": svc.name if svc else None,
                    "unit_quantity": comp.quantity,
                    "total_quantity": comp.quantity * payload.quantity,
                    "reference_price": float(comp.reference_price)
                })

            item = OpportunityQuotationItem(
                quotation_id=quotation.id,
                item_type="PACKAGE",
                package_id=pkg.id,
                package_version_id=ver.id,
                item_code=pkg.package_code,
                item_name=pkg.name,
                description=pkg.description,
                billing_unit="PACKAGE",
                quantity=payload.quantity,
                standard_price=std_price,
                unit_price=unit_price,
                total_price=taxable_amount,
                currency=ver.currency.code if ver.currency else "INR",
                package_components_snapshot=json.dumps(component_snapshots),
                tax_configuration_id=tax_config.id if tax_config else None,
                tax_type=tax_res["tax_type"],
                taxable_amount=taxable_amount,
                cgst_rate=tax_res["cgst_rate"],
                cgst_amount=tax_res["cgst_amount"],
                sgst_rate=tax_res["sgst_rate"],
                sgst_amount=tax_res["sgst_amount"],
                igst_rate=tax_res["igst_rate"],
                igst_amount=tax_res["igst_amount"],
                total_tax=tax_res["total_tax"],
                final_total=tax_res["final_total"]
            )
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            self._audit(actor, "CRM_QUOTATION_PACKAGE_ADDED", "OpportunityQuotationItem", item.id, {
                "quotation_id": quotation.id,
                "package_code": item.item_code,
                "version": ver.version_number,
                "total": float(item.final_total)
            }, request)
            return item

        elif payload.itemType == "ADDON":
            if not payload.serviceId:
                raise ValidationError("Add-on service ID is mandatory.")
            svc = self.get_service(payload.serviceId, as_of_date=quotation_date)
            if not svc.is_addon_eligible:
                raise ValidationError(f"Service '{svc.name}' is not marked as add-on eligible.")

            std_price = svc.effective_price or svc.standard_price
            unit_price = getattr(payload, "unitPrice", None) if getattr(payload, "unitPrice", None) is not None else (getattr(payload, "negotiatedUnitPrice", None) if getattr(payload, "negotiatedUnitPrice", None) is not None else std_price)
            taxable_amount = Decimal(str(unit_price)) * Decimal(str(payload.quantity))
            tax_res = self.calculate_tax(taxable_amount, tax_config)

            item = OpportunityQuotationItem(
                quotation_id=quotation.id,
                item_type="ADDON",
                service_id=svc.id,
                parent_item_id=payload.parentItemId,
                item_code=svc.service_code,
                item_name=f"[Add-On] {svc.name}",
                description=svc.description,
                billing_unit="ADDON",
                quantity=payload.quantity,
                standard_price=std_price,
                unit_price=unit_price,
                total_price=taxable_amount,
                currency=svc.currency.code if svc.currency else "INR",
                tax_configuration_id=tax_config.id if tax_config else None,
                tax_type=tax_res["tax_type"],
                taxable_amount=taxable_amount,
                cgst_rate=tax_res["cgst_rate"],
                cgst_amount=tax_res["cgst_amount"],
                sgst_rate=tax_res["sgst_rate"],
                sgst_amount=tax_res["sgst_amount"],
                igst_rate=tax_res["igst_rate"],
                igst_amount=tax_res["igst_amount"],
                total_tax=tax_res["total_tax"],
                final_total=tax_res["final_total"]
            )
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            self._audit(actor, "CRM_QUOTATION_ADDON_ADDED", "OpportunityQuotationItem", item.id, {
                "quotation_id": quotation.id,
                "addon_code": item.item_code,
                "total": float(item.final_total)
            }, request)
            return item

        elif payload.itemType in ("CUSTOM_SERVICE", "CUSTOM_PRODUCT", "PRODUCT"):
            item_name = (getattr(payload, "itemName", None) or "Custom Item").strip()
            unit_price = getattr(payload, "unitPrice", None) if getattr(payload, "unitPrice", None) is not None else getattr(payload, "negotiatedUnitPrice", Decimal("0.0"))
            if unit_price is None:
                unit_price = Decimal("0.0")
            unit_price = Decimal(str(unit_price))

            service_rec = None
            if getattr(payload, "savePermanently", False):
                is_admin = False
                roles = getattr(actor, "roles", []) or []
                if actor.active_role in ("CRM_ADMIN", "IT_ADMIN", "SUPER_ADMIN") or "CRM_ADMIN" in roles:
                    is_admin = True
                if not is_admin:
                    raise PermissionError("Only CRM Admins can save custom items permanently to the catalogue.")

                cat_id = getattr(payload, "categoryId", None)
                if not cat_id:
                    first_cat = self.db.query(ServiceCategory).filter(ServiceCategory.is_active == True).first()
                    cat_id = first_cat.id if first_cat else None

                code_prefix = "SRV"
                if cat_id:
                    cat = self.get_category(cat_id)
                    code_prefix = cat.category_code

                svc_code = get_next_sequence_id(self.db, f"SRV_{code_prefix}", f"{code_prefix}", padding=3, commit=False)

                service_rec = Service(
                    service_code=svc_code,
                    name=item_name,
                    category_id=cat_id,
                    billing_unit_id=getattr(payload, "billingUnitId", None),
                    description=getattr(payload, "description", None) or f"Custom catalogue item: {item_name}",
                    standard_price=unit_price,
                    is_active=True
                )
                self.db.add(service_rec)
                self.db.flush()

            line_discount = Decimal(str(getattr(payload, "discountAmount", 0) or 0))
            taxable_amount = (Decimal(str(payload.quantity)) * unit_price) - line_discount
            if taxable_amount < 0:
                taxable_amount = Decimal("0.0")
            tax_res = self.calculate_tax(taxable_amount, tax_config)

            item = OpportunityQuotationItem(
                quotation_id=quotation.id,
                item_type=payload.itemType,
                service_id=service_rec.id if service_rec else None,
                item_code=service_rec.service_code if service_rec else f"CUST-{int(datetime.now(timezone.utc).timestamp()) % 10000:04d}",
                item_name=item_name,
                description=getattr(payload, "description", None),
                billing_unit=getattr(payload, "billingUnit", None) or (service_rec.billing_unit.code if (service_rec and service_rec.billing_unit) else "Unit"),
                quantity=payload.quantity,
                standard_price=unit_price,
                unit_price=unit_price,
                discount_amount=line_discount,
                total_price=taxable_amount,
                currency="INR",
                tax_configuration_id=tax_config.id if tax_config else None,
                tax_type=tax_res["tax_type"],
                taxable_amount=taxable_amount,
                cgst_rate=tax_res["cgst_rate"],
                cgst_amount=tax_res["cgst_amount"],
                sgst_rate=tax_res["sgst_rate"],
                sgst_amount=tax_res["sgst_amount"],
                igst_rate=tax_res["igst_rate"],
                igst_amount=tax_res["igst_amount"],
                total_tax=tax_res["total_tax"],
                final_total=tax_res["final_total"]
            )
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            self._audit(actor, "CRM_QUOTATION_CUSTOM_ITEM_ADDED", "OpportunityQuotationItem", item.id, {
                "quotation_id": quotation.id,
                "item_code": item.item_code,
                "saved_permanently": bool(service_rec),
                "total": float(item.final_total)
            }, request)
            return item
        else:
            raise ValidationError(f"Unsupported item type '{payload.itemType}'.")

    def list_quotation_items(self, quotation_id: str) -> List[OpportunityQuotationItem]:
        items = self.db.query(OpportunityQuotationItem).options(
            joinedload(OpportunityQuotationItem.child_items),
            joinedload(OpportunityQuotationItem.tax_configuration)
        ).filter(
            OpportunityQuotationItem.quotation_id == quotation_id,
            OpportunityQuotationItem.parent_item_id == None
        ).order_by(OpportunityQuotationItem.created_at).all()
        return items

    def remove_quotation_item(self, actor: CurrentUser, quotation_id: str, item_id: str, request: Any = None):
        item = self.db.query(OpportunityQuotationItem).filter(
            OpportunityQuotationItem.id == item_id,
            OpportunityQuotationItem.quotation_id == quotation_id
        ).first()
        if not item:
            raise NotFoundError(f"Quotation item '{item_id}' not found.")

        quotation = item.quotation
        if quotation and quotation.status in ("Accepted", "Superseded"):
            raise ValidationError(f"Cannot modify quotation in '{quotation.status}' status.")

        self.db.delete(item)
        self.db.commit()
        self._audit(actor, "CRM_QUOTATION_ITEM_REMOVED", "OpportunityQuotationItem", item_id, {
            "quotation_id": quotation_id
        }, request)

    def save_current_quotation(
        self,
        actor: CurrentUser,
        opp_id: str,
        payload: Dict[str, Any],
        request: Any = None
    ) -> OpportunityQuotation:
        """
        Maintains only the single current quotation per opportunity.
        Replaces existing quotation line items cleanly without creating revision history.
        """
        opp = self.db.query(Opportunity).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        # Find existing active quotation
        quotation = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            OpportunityQuotation.is_active == True
        ).first()

        title = payload.get("title") or f"Quotation for {opp.name}"
        q_date = payload.get("quotationDate") or py_date.today()
        valid_until = payload.get("validUntilDate")
        terms = payload.get("termsAndConditions")
        notes = payload.get("notes")
        currency = payload.get("currency") or "INR"
        tax_type = payload.get("taxType") or "INTRA_STATE"
        tax_config_id = payload.get("taxConfigurationId")
        if not tax_config_id and tax_type in ("INTRA_STATE", "INTER_STATE"):
            def_tax = self.db.query(TaxConfiguration).filter(
                TaxConfiguration.tax_type == tax_type,
                TaxConfiguration.is_active == True
            ).first()
            if def_tax:
                tax_config_id = def_tax.id

        if not quotation:
            quotation_num = get_next_sequence_id(self.db, "QUOTATION", "QT", padding=5, commit=False)
            quotation = OpportunityQuotation(
                quotation_number=quotation_num,
                opportunity_id=opp.id,
                revision_number=1,
                version="v1",
                is_active=True,
                title=title,
                status="Draft",
                currency=currency,
                quotation_date=q_date,
                valid_until_date=valid_until,
                terms_and_conditions=terms,
                notes=notes,
                tax_type=tax_type,
                tax_configuration_id=tax_config_id,
                created_by_id=str(actor.id) if getattr(actor, "id", None) else None,
                updated_by_id=str(actor.id) if getattr(actor, "id", None) else None
            )
            self.db.add(quotation)
            self.db.flush()
        else:
            quotation.title = title
            quotation.quotation_date = q_date
            quotation.valid_until_date = valid_until
            quotation.terms_and_conditions = terms
            quotation.notes = notes
            quotation.currency = currency
            quotation.tax_type = tax_type
            quotation.tax_configuration_id = tax_config_id
            quotation.updated_by_id = str(actor.id) if getattr(actor, "id", None) else None
            quotation.updated_at = datetime.now(timezone.utc)
            # Remove old items to replace with updated set
            self.db.query(OpportunityQuotationItem).filter(
                OpportunityQuotationItem.quotation_id == quotation.id
            ).delete()
            self.db.flush()

        # Add all line items
        raw_items = payload.get("items") or []
        subtotal = Decimal("0.00")
        total_cgst = Decimal("0.00")
        total_sgst = Decimal("0.00")
        total_igst = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_discount = Decimal("0.00")

        for raw_item in raw_items:
            item_input = QuotationItemInput.model_validate(raw_item)
            if not item_input.taxConfigurationId:
                item_input.taxConfigurationId = tax_config_id
            created_item = self.add_item_to_quotation(actor, quotation.id, item_input, request)
            subtotal += Decimal(str(created_item.total_price))
            total_cgst += Decimal(str(created_item.cgst_amount))
            total_sgst += Decimal(str(created_item.sgst_amount))
            total_igst += Decimal(str(created_item.igst_amount))
            total_tax += Decimal(str(created_item.total_tax))
            total_discount += Decimal(str(created_item.discount_amount or 0))

        grand_total = subtotal + total_tax
        quotation.subtotal = subtotal
        quotation.cgst_amount = total_cgst
        quotation.sgst_amount = total_sgst
        quotation.igst_amount = total_igst
        quotation.total_tax = total_tax
        quotation.discount_amount = total_discount
        quotation.amount = grand_total

        self.db.commit()
        self.db.refresh(quotation)

        self._audit(actor, "CRM_QUOTATION_SAVED", "OpportunityQuotation", quotation.id, {
            "quotation_number": quotation.quotation_number,
            "opportunity_id": opp.opportunity_id,
            "items_count": len(raw_items),
            "amount": float(grand_total)
        }, request)

        return quotation

