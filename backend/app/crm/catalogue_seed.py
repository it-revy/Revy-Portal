import logging
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.crm.catalogue_model import (
    ServiceCategory,
    BillingUnit,
    ReportingUnit,
    SampleType,
    Currency,
    TaxConfiguration,
    TaxRate,
    Service,
    ServicePriceHistory,
    Package,
    PackageVersion,
    PackageComponent,
    PackageAddOnConfiguration
)
from app.crm.model import CrmSequence
from app.crm.catalogue_service import CatalogueService

logger = logging.getLogger("revy.crm.catalogue.seed")


def seed_catalogue_data(db: Session):
    """
    Authoritative Catalogue Seeding:
    1. 5 Main Categories (LAB-01 to LAB-05)
    2. Proposed Subcategories mapped logically
    3. Master Data: Billing Units, Sample Types, Currencies, Tax Configurations
    4. 61 Laboratory Services with original standard prices, zero duplicates, active status
    5. C/N Ratio with unverified note 'SR 50/51' and add-on eligibility
    6. Initial Sludge Analysis Package bundle
    """
    logger.info("Starting Product & Service Catalogue Seeding...")

    # =========================================================================
    # 1. CURRENCIES
    # =========================================================================
    currencies_data = [
        {"code": "INR", "name": "Indian Rupee", "symbol": "₹", "is_default": True},
        {"code": "USD", "name": "US Dollar", "symbol": "$", "is_default": False},
        {"code": "EUR", "name": "Euro", "symbol": "€", "is_default": False}
    ]
    currencies = {}
    for c_data in currencies_data:
        curr = db.query(Currency).filter(Currency.code == c_data["code"]).first()
        if not curr:
            curr = Currency(**c_data, is_active=True)
            db.add(curr)
            db.flush()
        currencies[curr.code] = curr

    inr_currency = currencies["INR"]

    # =========================================================================
    # 2. BILLING UNITS
    # =========================================================================
    billing_units_data = [
        {"code": "TEST", "name": "Per Test", "description": "Single analytical test procedure"},
        {"code": "SAMPLE", "name": "Per Sample", "description": "Analysis performed per sample unit"},
        {"code": "ANALYSIS", "name": "Per Analysis", "description": "Analytical run or chemical determination"},
        {"code": "PACKAGE", "name": "Per Package", "description": "Commercial multi-test bundle package"},
        {"code": "STUDY", "name": "Per Study", "description": "Comprehensive biological or process optimization study"},
        {"code": "ADDON", "name": "Per Add-on", "description": "Supplementary test ordered in conjunction with a service or package"}
    ]
    billing_units = {}
    for bu_data in billing_units_data:
        bu = db.query(BillingUnit).filter(BillingUnit.code == bu_data["code"]).first()
        if not bu:
            bu = BillingUnit(**bu_data, is_active=True)
            db.add(bu)
            db.flush()
        billing_units[bu.code] = bu

    # =========================================================================
    # 3. REPORTING UNITS
    # =========================================================================
    reporting_units_data = [
        {"code": "MG_L", "name": "Milligrams per Liter", "symbol": "mg/L"},
        {"code": "PERCENT", "name": "Percentage", "symbol": "%"},
        {"code": "PPM", "name": "Parts Per Million", "symbol": "ppm"},
        {"code": "NTU", "name": "Nephelometric Turbidity Unit", "symbol": "NTU"},
        {"code": "PH_UNIT", "name": "pH Units", "symbol": "pH"},
        {"code": "US_CM", "name": "Microsiemens per Centimeter", "symbol": "µS/cm"},
        {"code": "CELSIUS", "name": "Degrees Celsius", "symbol": "°C"},
        {"code": "ML_G", "name": "Milliliters per Gram", "symbol": "mL/g"},
        {"code": "ML_CH4_G_VS", "name": "Milliliters CH4 per Gram VS", "symbol": "mL CH4/g VS"},
        {"code": "RATIO", "name": "Dimensionless Ratio", "symbol": "ratio"}
    ]
    reporting_units = {}
    for ru_data in reporting_units_data:
        ru = db.query(ReportingUnit).filter(ReportingUnit.code == ru_data["code"]).first()
        if not ru:
            ru = ReportingUnit(**ru_data, is_active=True)
            db.add(ru)
            db.flush()
        reporting_units[ru.code] = ru

    # =========================================================================
    # 4. SAMPLE TYPES
    # =========================================================================
    sample_types_data = [
        {"code": "WASTEWATER", "name": "Wastewater"},
        {"code": "SEWAGE", "name": "Sewage"},
        {"code": "ORGANIC_WASTE", "name": "Organic Waste"},
        {"code": "FOOD_WASTE", "name": "Food Waste"},
        {"code": "AGRI_WASTE", "name": "Agricultural Waste"},
        {"code": "BIOMASS", "name": "Biomass"},
        {"code": "SLUDGE", "name": "Sludge"},
        {"code": "ACTIVATED_SLUDGE", "name": "Activated Sludge"},
        {"code": "BIOGAS", "name": "Biogas"},
        {"code": "DIGESTATE", "name": "Digestate"},
        {"code": "INDUSTRIAL_EFFLUENT", "name": "Industrial Effluent"},
        {"code": "OTHER", "name": "Other"}
    ]
    sample_types = {}
    for st_data in sample_types_data:
        st = db.query(SampleType).filter(SampleType.code == st_data["code"]).first()
        if not st:
            st = SampleType(**st_data, is_active=True)
            db.add(st)
            db.flush()
        sample_types[st.code] = st

    # =========================================================================
    # 5. TAX CONFIGURATIONS (CGST, SGST, IGST)
    # =========================================================================
    tax_configs_data = [
        {
            "code": "GST-18-INTRA",
            "name": "GST 18% Intra-State (9% CGST + 9% SGST)",
            "tax_type": "INTRA_STATE",
            "rates": [
                {"component_name": "CGST", "rate_percentage": Decimal("9.0000")},
                {"component_name": "SGST", "rate_percentage": Decimal("9.0000")}
            ]
        },
        {
            "code": "GST-18-INTER",
            "name": "GST 18% Inter-State (18% IGST)",
            "tax_type": "INTER_STATE",
            "rates": [
                {"component_name": "IGST", "rate_percentage": Decimal("18.0000")}
            ]
        },
        {
            "code": "GST-EXEMPT",
            "name": "Exempt / Zero Rated (0%)",
            "tax_type": "EXEMPT",
            "rates": []
        }
    ]
    tax_configs = {}
    for tc_data in tax_configs_data:
        tc = db.query(TaxConfiguration).filter(TaxConfiguration.code == tc_data["code"]).first()
        if not tc:
            tc = TaxConfiguration(
                code=tc_data["code"],
                name=tc_data["name"],
                tax_type=tc_data["tax_type"],
                is_active=True
            )
            db.add(tc)
            db.flush()
            for r in tc_data["rates"]:
                rate = TaxRate(
                    configuration_id=tc.id,
                    component_name=r["component_name"],
                    rate_percentage=r["rate_percentage"],
                    is_active=True
                )
                db.add(rate)
            db.flush()
        tax_configs[tc.code] = tc

    # =========================================================================
    # 6. MAIN CATEGORIES (EXACTLY 4: LAB-01 to LAB-04)
    # =========================================================================
    categories_data = [
        {"code": "LAB-01", "name": "PHYSICAL CHARACTERISTICS", "prefix": "PHY", "description": "Physical parameters and characteristics of water, wastewater, and effluents."},
        {"code": "LAB-02", "name": "CHEMICAL CHARACTERISTICS", "prefix": "CHM", "description": "Chemical composition, inorganic and organic parameters, nutrients, and heavy metals."},
        {"code": "LAB-03", "name": "ORGANIC WASTE CHARACTERIZATION", "prefix": "OWC", "description": "Proximate, ultimate, and biochemical characterization of solid and semi-solid organic substrates."},
        {"code": "LAB-04", "name": "SLUDGE CHARACTERIZATION", "prefix": "SLG", "description": "Settling indices, biological solids, active biomass, and metagenomic community analysis."}
    ]
    target_category_codes = {c["code"] for c in categories_data}

    # Deactivate and soft-delete any categories not in the 4 target categories (e.g. LAB-05, LAB-06)
    db.query(ServiceCategory).filter(~ServiceCategory.code.in_(target_category_codes)).update(
        {"is_active": False, "is_deleted": True},
        synchronize_session=False
    )
    db.flush()

    categories = {}
    for c_data in categories_data:
        cat = db.query(ServiceCategory).filter(ServiceCategory.code == c_data["code"]).first()
        if not cat:
            cat = ServiceCategory(**c_data, is_active=True, is_deleted=False)
            db.add(cat)
            db.flush()
        else:
            cat.name = c_data["name"]
            cat.prefix = c_data["prefix"]
            cat.description = c_data["description"]
            cat.is_active = True
            cat.is_deleted = False
            db.flush()
        categories[cat.code] = cat

    # =========================================================================
    # 7. AUTHORITATIVE INITIAL SERVICES (EXACTLY 61 SERVICES ACROSS 4 CATEGORIES)
    # =========================================================================
    # Format: (No, Name, Price, CategoryCode, BillingUnitCode, is_addon, source_note)
    services_seed_data = [
        # Category 1: PHYSICAL CHARACTERISTICS (5 services)
        (1, "Colour", 100, "LAB-01", "TEST", False, None),
        (2, "Odour", 100, "LAB-01", "TEST", False, None),
        (3, "Transparency of Water / Wastewater", 100, "LAB-01", "TEST", False, None),
        (4, "Temperature of Liquid Sample", 100, "LAB-01", "TEST", False, None),
        (5, "Physical Appearance", 100, "LAB-01", "TEST", False, None),

        # Category 2: CHEMICAL CHARACTERISTICS (37 services)
        (6, "Electrical conductivity", 200, "LAB-02", "TEST", False, None),
        (7, "pH", 100, "LAB-02", "TEST", False, None),
        (8, "Total Volatile Fatty acid (VFA) (ppm)", 600, "LAB-02", "TEST", False, None),
        (9, "Total Alkalinity (P or MO)", 500, "LAB-02", "TEST", False, None),
        (10, "COD mg/l", 1000, "LAB-02", "TEST", False, None),
        (11, "BOD mg/l", 1500, "LAB-02", "TEST", False, None),
        (12, "Total Dissolved Solid - TDS (mg/l)", 500, "LAB-02", "TEST", False, None),
        (13, "Total Suspended Solids (ppm) (TSS)", 500, "LAB-02", "TEST", False, None),
        (14, "Total Suspended Volatile Solids (ppm) (VSS)", 600, "LAB-02", "TEST", False, None),
        (15, "Ammonical Nitrogen (ppm)", 1500, "LAB-02", "TEST", False, None),
        (16, "Oil n Grease Test", 1500, "LAB-02", "TEST", False, None),
        (17, "Total Kjeldhal Nitrogen", 1800, "LAB-02", "TEST", False, None),
        (18, "Bicarbonates/Bicarbonate Alkalinity (as HCO3)", 500, "LAB-02", "TEST", False, None),
        (19, "Total Hardness as CaCO3 (ppm)", 500, "LAB-02", "TEST", False, None),
        (20, "Temporary Hardness", 500, "LAB-02", "TEST", False, None),
        (21, "Calcium (as Ca)", 500, "LAB-02", "TEST", False, None),
        (22, "Magnesium (as Mg)", 500, "LAB-02", "TEST", False, None),
        (23, "Chloride as Cl (ppm)", 500, "LAB-02", "TEST", False, None),
        (24, "Sulphates as SO4 (ppm)", 1500, "LAB-02", "TEST", False, None),
        (25, "Aluminium", 1500, "LAB-02", "TEST", False, None),
        (26, "Phosphate", 1500, "LAB-02", "TEST", False, None),
        (27, "Iron", 1500, "LAB-02", "TEST", False, None),
        (28, "Silica", 1500, "LAB-02", "TEST", False, None),
        (29, "Sodium", 1000, "LAB-02", "TEST", False, None),
        (30, "Potassium", 1000, "LAB-02", "TEST", False, None),
        (31, "Zn", 1500, "LAB-02", "TEST", False, None),
        (32, "Cr", 1500, "LAB-02", "TEST", False, None),
        (33, "Mn", 1500, "LAB-02", "TEST", False, None),
        (34, "Pb", 1500, "LAB-02", "TEST", False, None),
        (35, "Cu", 1500, "LAB-02", "TEST", False, None),
        (36, "Nitrate", 1500, "LAB-02", "TEST", False, None),
        (37, "Boron", 1500, "LAB-02", "TEST", False, None),
        (38, "Glucose Estimation", 600, "LAB-02", "TEST", False, None),
        (39, "Sugar (Total Reducing Sugar)", 600, "LAB-02", "TEST", False, None),
        (40, "VFA Profiling", 6000, "LAB-02", "ANALYSIS", False, None),
        (41, "Chemical Dose / Optimization", 8000, "LAB-02", "STUDY", False, None),
        (42, "Gas Analysis by GC", 4500, "LAB-02", "ANALYSIS", False, None),

        # Category 3: ORGANIC WASTE CHARACTERIZATION (11 services)
        (43, "Total Solids (ppm) (TS)", 400, "LAB-03", "TEST", False, None),
        (44, "Total Volatile Solids (VS) (ppm) / Organic Content", 600, "LAB-03", "TEST", False, None),
        (45, "Moisture Content", 400, "LAB-03", "TEST", False, None),
        (46, "Ash Content", 600, "LAB-03", "TEST", False, None),
        (47, "Carbon", 1000, "LAB-03", "TEST", False, None),
        (48, "Nitrogen", 1000, "LAB-03", "TEST", False, None),
        (49, "C/N Ratio (along with sr 50 & 51)", 300, "LAB-03", "ADDON", True, "along with sr 50 & 51"),
        (50, "Cellulose / Hemicellulose / Lignin", 5000, "LAB-03", "TEST", False, None),
        (51, "Crude Protein / Crude Fat / Crude Fiber / Silicate", 4000, "LAB-03", "TEST", False, None),
        (52, "Total Organic Carbon (TOC)", 2500, "LAB-03", "TEST", False, None),
        (53, "Anaerobic Degradability Test / BMP", 35000, "LAB-03", "STUDY", False, None),

        # Category 4: SLUDGE CHARACTERIZATION (8 services)
        (54, "MLSS", 1000, "LAB-04", "TEST", False, None),
        (55, "MLVSS", 1000, "LAB-04", "TEST", False, None),
        (56, "SVI", 800, "LAB-04", "TEST", False, None),
        (57, "Sludge Analysis (MLSS, MLVSS, SVI)", 2200, "LAB-04", "ANALYSIS", False, None),
        (58, "Biomass Microscopy", 1000, "LAB-04", "TEST", False, None),
        (59, "Particle Size Analysis (Granulacity)", 3000, "LAB-04", "ANALYSIS", False, None),
        (60, "SMA Test", 15000, "LAB-04", "STUDY", False, None),
        (61, "Metagenomic Study", 25000, "LAB-04", "STUDY", False, None),
    ]

    target_service_names = {s[1] for s in services_seed_data}

    # Deactivate and soft-delete any services not in the new 61 services
    db.query(Service).filter(~Service.name.in_(target_service_names)).update(
        {"is_active": False, "is_deleted": True},
        synchronize_session=False
    )
    db.flush()

    services_by_name = {}
    cat_seq_counters = {"PHY": 0, "CHM": 0, "OWC": 0, "SLG": 0}

    for no, name, price, cat_code, bu_code, is_addon, note in services_seed_data:
        cat = categories[cat_code]
        bu = billing_units[bu_code]

        cat_seq_counters[cat.prefix] += 1
        expected_code = f"{cat.prefix}-{cat_seq_counters[cat.prefix]:03d}"

        svc = db.query(Service).filter(Service.name == name).first()
        if not svc:
            svc = db.query(Service).filter(Service.service_code == expected_code).first()

        if not svc:
            svc = Service(
                service_code=expected_code,
                name=name,
                description=f"Standard laboratory testing service for {name}.",
                category_id=cat.id,
                billing_unit_id=bu.id,
                currency_id=inr_currency.id,
                minimum_billing_quantity=1,
                standard_price=Decimal(str(price)),
                effective_date=date.today(),
                is_active=True,
                is_deleted=False,
                is_addon_eligible=is_addon,
                can_have_addons=True,
                source_note=note
            )
            db.add(svc)
            db.flush()

            hist = ServicePriceHistory(
                service_id=svc.id,
                price=Decimal(str(price)),
                currency_id=inr_currency.id,
                effective_date=date.today(),
                reason="Initial catalogue seeding standard price"
            )
            db.add(hist)
        else:
            svc.service_code = expected_code
            svc.name = name
            svc.category_id = cat.id
            svc.billing_unit_id = bu.id
            svc.currency_id = inr_currency.id
            svc.standard_price = Decimal(str(price))
            svc.is_active = True
            svc.is_deleted = False
            svc.is_addon_eligible = is_addon
            svc.source_note = note
            db.flush()

        services_by_name[name] = svc

    # Ensure CrmSequence values are at least the max seeded counters
    for prefix, count in cat_seq_counters.items():
        entity_key = f"CAT_{prefix}"
        seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).first()
        if not seq:
            seq = CrmSequence(entity_name=entity_key, current_value=count)
            db.add(seq)
        else:
            if seq.current_value < count:
                seq.current_value = count
    db.flush()

    # =========================================================================
    # 8. INITIAL PACKAGE BUNDLE (SLUDGE ANALYSIS PACKAGE)
    # =========================================================================
    mlss = services_by_name.get("MLSS")
    mlvss = services_by_name.get("MLVSS")
    svi = services_by_name.get("SVI")
    cn_ratio = services_by_name.get("C/N Ratio (along with sr 50 & 51)")

    if mlss and mlvss and svi:
        pkg_code = "PKG-001"
        pkg = db.query(Package).filter(Package.package_code == pkg_code).first()
        if not pkg:
            pkg = Package(
                package_code=pkg_code,
                name="Sludge Analysis Package",
                description="Comprehensive sludge analysis including MLSS, MLVSS, and SVI at a discounted package price.",
                category_id=categories["LAB-04"].id,
                currency_id=inr_currency.id,
                fixed_package_price=Decimal("2200.0000"),
                current_version=1,
                is_active=True,
                is_deleted=False
            )
            db.add(pkg)
            db.flush()

            ver = PackageVersion(
                package_id=pkg.id,
                version_number=1,
                fixed_price=Decimal("2200.0000"),
                currency_id=inr_currency.id,
                change_summary="Initial Sludge Analysis Package v1 (MLSS + MLVSS + SVI)",
                is_active=True,
                effective_date=date.today()
            )
            db.add(ver)
            db.flush()

            # Components: MLSS (₹1,000), MLVSS (₹1,000), SVI (₹800). Total ind: ₹2,800. Package: ₹2,200.
            db.add(PackageComponent(package_version_id=ver.id, service_id=mlss.id, quantity=1, reference_price=mlss.standard_price))
            db.add(PackageComponent(package_version_id=ver.id, service_id=mlvss.id, quantity=1, reference_price=mlvss.standard_price))
            db.add(PackageComponent(package_version_id=ver.id, service_id=svi.id, quantity=1, reference_price=svi.standard_price))

            # Add-on configuration: C/N Ratio (₹300 default)
            if cn_ratio:
                db.add(PackageAddOnConfiguration(
                    package_version_id=ver.id,
                    addon_service_id=cn_ratio.id,
                    default_quantity=1,
                    override_price=Decimal("300.0000"),
                    is_mandatory=False
                ))
        else:
            # Re-associate with Category LAB-04 (SLUDGE CHARACTERIZATION)
            pkg.category_id = categories["LAB-04"].id
            pkg.is_active = True
            pkg.is_deleted = False
            ver = db.query(PackageVersion).filter(PackageVersion.package_id == pkg.id).order_by(PackageVersion.version_number.desc()).first()
            if ver:
                comps = db.query(PackageComponent).filter(PackageComponent.package_version_id == ver.id).all()
                if len(comps) >= 3:
                    comps[0].service_id = mlss.id
                    comps[0].reference_price = mlss.standard_price
                    comps[1].service_id = mlvss.id
                    comps[1].reference_price = mlvss.standard_price
                    comps[2].service_id = svi.id
                    comps[2].reference_price = svi.standard_price

    pkg_seq = db.query(CrmSequence).filter(CrmSequence.entity_name == "CAT_PKG").first()
    if not pkg_seq:
        db.add(CrmSequence(entity_name="CAT_PKG", current_value=1))
    else:
        if pkg_seq.current_value < 1:
            pkg_seq.current_value = 1

    db.commit()
    logger.info("Catalogue seeding completed successfully: exactly 4 categories, 61 services, and initial package bundle.")
