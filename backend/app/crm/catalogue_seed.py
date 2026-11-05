import logging
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.crm.catalogue_model import (
    ServiceCategory,
    ServiceSubcategory,
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
    # 6. MAIN CATEGORIES (LAB-01 to LAB-05)
    # =========================================================================
    categories_data = [
        {"code": "LAB-01", "name": "Water & Wastewater Analysis", "prefix": "WWT", "description": "Physical, chemical, and biological characterization of water, wastewater, and effluents."},
        {"code": "LAB-02", "name": "Organic Waste Characterization", "prefix": "OWC", "description": "Proximate, ultimate, and biochemical characterization of solid and semi-solid organic substrates."},
        {"code": "LAB-03", "name": "Biogas & Anaerobic Digestion", "prefix": "BIO", "description": "Biogas composition, volatile fatty acid profiling, and anaerobic digestion kinetics."},
        {"code": "LAB-04", "name": "Sludge, Biomass & Biological Analysis", "prefix": "SLG", "description": "Settling indices, biological solids, active biomass, and metagenomic community analysis."},
        {"code": "LAB-05", "name": "Process Optimization & Specialized Analysis", "prefix": "OPT", "description": "Chemical dosing studies, sugar estimation, and tailored environmental R&D analyses."}
    ]
    categories = {}
    for c_data in categories_data:
        cat = db.query(ServiceCategory).filter(ServiceCategory.code == c_data["code"]).first()
        if not cat:
            cat = ServiceCategory(**c_data, is_active=True, is_deleted=False)
            db.add(cat)
            db.flush()
        categories[cat.code] = cat

    # =========================================================================
    # 7. PROPOSED SUBCATEGORIES
    # =========================================================================
    subcategories_data = [
        # LAB-01
        {"code": "LAB-01-SUB-01", "category_code": "LAB-01", "name": "Physical Parameters", "description": "Visual, sensory, and bulk physical water properties"},
        {"code": "LAB-01-SUB-02", "category_code": "LAB-01", "name": "General Chemical & Physico-Chemical", "description": "Conductivity, pH, alkalinity, hardness, and general inorganic ions"},
        {"code": "LAB-01-SUB-03", "category_code": "LAB-01", "name": "Organic & Pollution Demand", "description": "Oxygen demand and organic contaminant concentration"},
        {"code": "LAB-01-SUB-04", "category_code": "LAB-01", "name": "Solids Characterization", "description": "Suspended, dissolved, and volatile solids quantification"},
        {"code": "LAB-01-SUB-05", "category_code": "LAB-01", "name": "Nutrients & Nitrogen Forms", "description": "Nitrogenous compounds, phosphorus, and plant nutrients"},
        {"code": "LAB-01-SUB-06", "category_code": "LAB-01", "name": "Heavy Metals & Trace Elements", "description": "Trace elemental and heavy metal determination"},

        # LAB-02
        {"code": "LAB-02-SUB-01", "category_code": "LAB-02", "name": "Proximate & Ultimate Analysis", "description": "Moisture, solids, carbon, nitrogen, and elemental composition of organic wastes"},
        {"code": "LAB-02-SUB-02", "category_code": "LAB-02", "name": "Biochemical Fractions & Composition", "description": "Fiber, lignin, protein, and structural biochemical fractions"},

        # LAB-03
        {"code": "LAB-03-SUB-01", "category_code": "LAB-03", "name": "Gas & Volatile Acid Characterization", "description": "Biogas composition by GC, VFA profiling, and acid monitoring"},
        {"code": "LAB-03-SUB-02", "category_code": "LAB-03", "name": "Methane Potential & Activity", "description": "BMP assays and methanogenic activity kinetics"},

        # LAB-04
        {"code": "LAB-04-SUB-01", "category_code": "LAB-04", "name": "Sludge Physical & Settling Characteristics", "description": "MLSS, MLVSS, SVI, and floc particle size analysis"},
        {"code": "LAB-04-SUB-02", "category_code": "LAB-04", "name": "Biological & Microbial Analysis", "description": "Microscopy, biomass health, and metagenomic analysis"},

        # LAB-05
        {"code": "LAB-05-SUB-01", "category_code": "LAB-05", "name": "Process Sugar & Fermentation Estimation", "description": "Glucose and reducing sugars in fermentation streams"},
        {"code": "LAB-05-SUB-02", "category_code": "LAB-05", "name": "Chemical Optimization Studies", "description": "Chemical dosing, coagulant optimization, and process tuning"}
    ]
    subcategories = {}
    for sc_data in subcategories_data:
        subcat = db.query(ServiceSubcategory).filter(ServiceSubcategory.code == sc_data["code"]).first()
        cat = categories[sc_data["category_code"]]
        if not subcat:
            subcat = ServiceSubcategory(
                category_id=cat.id,
                code=sc_data["code"],
                name=sc_data["name"],
                description=sc_data["description"],
                is_active=True,
                is_deleted=False
            )
            db.add(subcat)
            db.flush()
        subcategories[subcat.code] = subcat

    # =========================================================================
    # 8. AUTHORITATIVE INITIAL SERVICES (ALL 61 SERVICES)
    # =========================================================================
    # Format: (No, Name, Price, CategoryCode, SubcategoryCode, BillingUnitCode, is_addon, source_note)
    services_seed_data = [
        # A. Physical Characteristics (1-5)
        (1, "Colour", 100, "LAB-01", "LAB-01-SUB-01", "TEST", False, None),
        (2, "Odour", 100, "LAB-01", "LAB-01-SUB-01", "TEST", False, None),
        (3, "Transparency of Water/Wastewater", 100, "LAB-01", "LAB-01-SUB-01", "TEST", False, None),
        (4, "Temperature of Liquid Sample", 100, "LAB-01", "LAB-01-SUB-01", "TEST", False, None),
        (5, "Physical Appearance", 100, "LAB-01", "LAB-01-SUB-01", "TEST", False, None),

        # B. Chemical Characteristics (6-42)
        (6, "Electrical Conductivity (EC)", 200, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (7, "pH", 100, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (8, "Volatile Fatty Acids (VFA)", 600, "LAB-03", "LAB-03-SUB-01", "TEST", False, None),
        (9, "Total Alkalinity", 500, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (10, "Chemical Oxygen Demand (COD)", 1000, "LAB-01", "LAB-01-SUB-03", "TEST", False, None),
        (11, "Biochemical Oxygen Demand (BOD)", 1500, "LAB-01", "LAB-01-SUB-03", "TEST", False, None),
        (12, "Total Dissolved Solids (TDS)", 500, "LAB-01", "LAB-01-SUB-04", "TEST", False, None),
        (13, "Total Suspended Solids (TSS)", 500, "LAB-01", "LAB-01-SUB-04", "TEST", False, None),
        (14, "Volatile Suspended Solids (VSS)", 600, "LAB-01", "LAB-01-SUB-04", "TEST", False, None),
        (15, "Ammonical Nitrogen", 1500, "LAB-01", "LAB-01-SUB-05", "TEST", False, None),
        (16, "Oil & Grease", 1500, "LAB-01", "LAB-01-SUB-03", "TEST", False, None),
        (17, "Total Kjeldahl Nitrogen (TKN)", 1800, "LAB-01", "LAB-01-SUB-05", "TEST", False, None),
        (18, "Bicarbonates", 500, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (19, "Total Hardness", 500, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (20, "Temporary Hardness", 500, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (21, "Calcium", 500, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (22, "Magnesium", 500, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (23, "Chloride", 500, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (24, "Sulphates", 1500, "LAB-01", "LAB-01-SUB-02", "TEST", False, None),
        (25, "Aluminium", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (26, "Phosphate", 1500, "LAB-01", "LAB-01-SUB-05", "TEST", False, None),
        (27, "Iron", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (28, "Silica", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (29, "Sodium", 1000, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (30, "Potassium", 1000, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (31, "Zinc (Zn)", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (32, "Chromium (Cr)", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (33, "Manganese (Mn)", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (34, "Lead (Pb)", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (35, "Copper (Cu)", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (36, "Nitrate", 1500, "LAB-01", "LAB-01-SUB-05", "TEST", False, None),
        (37, "Boron", 1500, "LAB-01", "LAB-01-SUB-06", "TEST", False, None),
        (38, "Glucose Estimation", 600, "LAB-05", "LAB-05-SUB-01", "TEST", False, None),
        (39, "Total Reducing Sugar", 600, "LAB-05", "LAB-05-SUB-01", "TEST", False, None),
        (40, "VFA Profiling", 6000, "LAB-03", "LAB-03-SUB-01", "ANALYSIS", False, None),
        (41, "Chemical Dose/Optimization", 8000, "LAB-05", "LAB-05-SUB-02", "STUDY", False, None),
        (42, "Gas Analysis by GC", 4500, "LAB-03", "LAB-03-SUB-01", "ANALYSIS", False, None),

        # C. Organic Waste Characterization (43-53)
        (43, "Total Solids (TS)", 400, "LAB-02", "LAB-02-SUB-01", "TEST", False, None),
        (44, "Volatile Solids (VS)", 600, "LAB-02", "LAB-02-SUB-01", "TEST", False, None),
        (45, "Moisture", 400, "LAB-02", "LAB-02-SUB-01", "TEST", False, None),
        (46, "Ash", 600, "LAB-02", "LAB-02-SUB-01", "TEST", False, None),
        (47, "Carbon", 1000, "LAB-02", "LAB-02-SUB-01", "TEST", False, None),
        (48, "Nitrogen", 1000, "LAB-02", "LAB-02-SUB-01", "TEST", False, None),
        (49, "C/N Ratio", 300, "LAB-02", "LAB-02-SUB-01", "TEST", True, "SR 50/51"),
        (50, "Cellulose/Hemicellulose/Lignin", 5000, "LAB-02", "LAB-02-SUB-02", "ANALYSIS", False, None),
        (51, "Crude Protein/Crude Fat/Crude Fiber/Silicate", 4000, "LAB-02", "LAB-02-SUB-02", "ANALYSIS", False, None),
        (52, "Total Organic Carbon (TOC)", 2500, "LAB-02", "LAB-02-SUB-01", "TEST", False, None),
        (53, "Biochemical Methane Potential (BMP)", 35000, "LAB-03", "LAB-03-SUB-02", "STUDY", False, None),

        # D. Sludge Characterization (54-61)
        (54, "Mixed Liquor Suspended Solids (MLSS)", 1000, "LAB-04", "LAB-04-SUB-01", "TEST", False, None),
        (55, "Mixed Liquor Volatile Suspended Solids (MLVSS)", 1000, "LAB-04", "LAB-04-SUB-01", "TEST", False, None),
        (56, "Sludge Volume Index (SVI)", 800, "LAB-04", "LAB-04-SUB-01", "TEST", False, None),
        (57, "Combined Sludge Analysis (MLSS, MLVSS, SVI)", 2200, "LAB-04", "LAB-04-SUB-01", "ANALYSIS", False, None),
        (58, "Biomass Microscopy", 1000, "LAB-04", "LAB-04-SUB-02", "TEST", False, None),
        (59, "Particle Size Analysis/Granulometry", 3000, "LAB-04", "LAB-04-SUB-01", "ANALYSIS", False, None),
        (60, "Specific Methanogenic Activity (SMA)", 15000, "LAB-03", "LAB-03-SUB-02", "STUDY", False, None),
        (61, "Metagenomic Study", 25000, "LAB-04", "LAB-04-SUB-02", "STUDY", False, None)
    ]

    services_by_name = {}
    cat_seq_counters = {"WWT": 0, "OWC": 0, "BIO": 0, "SLG": 0, "OPT": 0}

    for no, name, price, cat_code, subcat_code, bu_code, is_addon, note in services_seed_data:
        cat = categories[cat_code]
        subcat = subcategories[subcat_code]
        bu = billing_units[bu_code]

        svc = db.query(Service).filter(Service.name == name).first()
        if not svc:
            cat_seq_counters[cat.prefix] += 1
            code = f"{cat.prefix}-{cat_seq_counters[cat.prefix]:03d}"

            svc = Service(
                service_code=code,
                name=name,
                description=f"Standard laboratory testing service for {name}.",
                category_id=cat.id,
                subcategory_id=subcat.id,
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

            # Record initial price in history
            hist = ServicePriceHistory(
                service_id=svc.id,
                price=Decimal(str(price)),
                currency_id=inr_currency.id,
                effective_date=date.today(),
                reason="Initial catalogue seeding standard price"
            )
            db.add(hist)

        services_by_name[name] = svc

    # =========================================================================
    # 9. INITIAL PACKAGE BUNDLE (SLUDGE ANALYSIS PACKAGE)
    # =========================================================================
    mlss = services_by_name.get("Mixed Liquor Suspended Solids (MLSS)")
    mlvss = services_by_name.get("Mixed Liquor Volatile Suspended Solids (MLVSS)")
    svi = services_by_name.get("Sludge Volume Index (SVI)")
    cn_ratio = services_by_name.get("C/N Ratio")

    if mlss and mlvss and svi:
        pkg_code = "PKG-001"
        pkg = db.query(Package).filter(Package.package_code == pkg_code).first()
        if not pkg:
            pkg = Package(
                package_code=pkg_code,
                name="Sludge Analysis Package",
                description="Comprehensive sludge analysis including MLSS, MLVSS, and SVI at a discounted package price.",
                category_id=categories["LAB-04"].id,
                subcategory_id=subcategories["LAB-04-SUB-01"].id,
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

    db.commit()
    logger.info("Catalogue seeding completed successfully: 5 categories, 14 subcategories, 61 services, and initial package bundle.")
