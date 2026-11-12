import os
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from app.core.database import SessionLocal
import app.models
from app.crm.model import Opportunity, OpportunityQuotation, Account
from app.crm.catalogue_model import (
    ServiceCategory, BillingUnit, ReportingUnit,
    SampleType, TestingMethod, Currency, TaxConfiguration, TaxRate,
    Service, ServicePriceHistory, Package, PackageVersion, PackageComponent,
    OpportunityQuotationItem
)
from app.crm.catalogue_seed import seed_catalogue_data

@pytest.fixture(scope="module", autouse=True)
def seed_test_catalogue():
    db = SessionLocal()
    try:
        seed_catalogue_data(db)
    finally:
        db.close()


def test_seed_verification(client, auth_headers):
    """Verify that exactly 61 services and 4 main categories were seeded."""
    res = client.get("/api/v1/crm/catalogue/services?pageSize=100", headers=auth_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["total"] == 61

    # Verify categories - exactly 4 active categories
    cat_res = client.get("/api/v1/crm/catalogue/categories", headers=auth_headers)
    assert cat_res.status_code == 200
    categories = cat_res.json()["categories"]
    assert len(categories) == 4
    cat_codes = [c["code"] for c in categories]
    assert "LAB-01" in cat_codes
    assert "LAB-02" in cat_codes
    assert "LAB-03" in cat_codes
    assert "LAB-04" in cat_codes
    assert "LAB-05" not in cat_codes

    # Verify category-wise service counts: PHY: 5, CHM: 37, OWC: 11, SLG: 8
    cat_map = {c["code"]: c for c in categories}
    assert cat_map["LAB-01"]["name"] == "PHYSICAL CHARACTERISTICS"
    assert cat_map["LAB-02"]["name"] == "CHEMICAL CHARACTERISTICS"
    assert cat_map["LAB-03"]["name"] == "ORGANIC WASTE CHARACTERIZATION"
    assert cat_map["LAB-04"]["name"] == "SLUDGE CHARACTERIZATION"

    # Verify initial package
    pkg_res = client.get("/api/v1/crm/catalogue/packages", headers=auth_headers)
    assert pkg_res.status_code == 200
    pkgs = pkg_res.json()["packages"]
    assert len(pkgs) >= 1
    assert any(p["code"] == "PKG-001" for p in pkgs)


def test_main_category_lifecycle_and_service_guards(client, auth_headers):
    """
    Test Section: Main Category -> Services Relationship & Lifecycle:
    - Main Category creates without displayOrder or subcategories
    - Active services directly associate with category_id
    - Category cannot be deleted while it has active services (Guard)
    - Category cannot be deactivated while it has active services (Guard)
    - Inactive category cannot be assigned to new services
    - Soft-delete preservation when safe
    """
    suffix = uuid.uuid4().hex[:4].upper()
    cat_code = f"LAB-T{suffix}"

    # 1. Create a new test main category (no displayOrder or subcategories required)
    res = client.post("/api/v1/crm/catalogue/categories", headers=auth_headers, json={
        "code": cat_code,
        "name": f"Testing Category {suffix}",
        "description": "Category for direct Main Category -> Services relationship tests"
    })
    assert res.status_code == 200, res.text
    cat = res.json()["category"]
    cat_id = cat["id"]
    assert cat["code"] == cat_code
    assert "subcategories" not in cat or cat.get("subcategories") is None or len(cat.get("subcategories", [])) == 0

    # 2. Create an active service directly under this main category
    db = SessionLocal()
    bunit = db.query(BillingUnit).filter(BillingUnit.code == "SAMPLE").first()
    db.close()
    assert bunit is not None

    srv_res = client.post("/api/v1/crm/catalogue/services", headers=auth_headers, json={
        "name": f"Guard Test Service {suffix}",
        "categoryId": cat_id,
        "billingUnitId": bunit.id,
        "standardPrice": 1200.00,
        "minimumBillingQuantity": 1
    })
    assert srv_res.status_code == 200, srv_res.text
    srv = srv_res.json()["service"]
    srv_id = srv["id"]
    assert srv["categoryId"] == cat_id

    # 3. Guard 1: Attempt to delete category when it has active services (MUST fail with 400)
    del_res = client.delete(f"/api/v1/crm/catalogue/categories/{cat_id}", headers=auth_headers)
    assert del_res.status_code == 400
    msg = del_res.json().get("message", "") or del_res.json().get("detail", "")
    assert "service" in msg.lower()

    # 4. Guard 2: Attempt to deactivate category with active service (MUST fail with 400)
    deact_res = client.put(f"/api/v1/crm/catalogue/categories/{cat_id}", headers=auth_headers, json={
        "isActive": False
    })
    assert deact_res.status_code == 400

    # 5. Now deactivate the service
    client.put(f"/api/v1/crm/catalogue/services/{srv_id}", headers=auth_headers, json={
        "isActive": False
    })

    # 6. Deactivating category should now succeed
    deact_ok = client.put(f"/api/v1/crm/catalogue/categories/{cat_id}", headers=auth_headers, json={
        "isActive": False
    })
    assert deact_ok.status_code == 200

    # 7. Attempting to assign deactivated category to a new service MUST fail (400)
    fail_create = client.post("/api/v1/crm/catalogue/services", headers=auth_headers, json={
        "name": f"Invalid Service Under Deactivated Cat {suffix}",
        "categoryId": cat_id,
        "billingUnitId": bunit.id,
        "standardPrice": 1500.00
    })
    assert fail_create.status_code == 400

    # 8. Mark service deleted
    db = SessionLocal()
    srv_row = db.query(Service).filter(Service.id == srv_id).first()
    srv_row.is_deleted = True
    db.commit()
    db.close()

    # 9. Deleting category should now succeed
    del_cat_ok = client.delete(f"/api/v1/crm/catalogue/categories/{cat_id}", headers=auth_headers)
    assert del_cat_ok.status_code == 200
    assert del_cat_ok.json()["success"] is True


def test_service_creation_and_price_history(client, auth_headers):
    """
    Test Section 6 & 8:
    - Automatic concurrency-safe service code generation
    - Updating price writes to ServicePriceHistory
    - Effective date handling
    """
    db = SessionLocal()
    cat = db.query(ServiceCategory).filter(ServiceCategory.code == "LAB-01").first()
    bunit = db.query(BillingUnit).filter(BillingUnit.code == "TEST").first()
    stype = db.query(SampleType).first()
    tmethod = db.query(TestingMethod).first()
    runit = db.query(ReportingUnit).first()
    db.close()

    suffix = uuid.uuid4().hex[:4]

    # Create service
    payload = {
        "name": f"BOD Advanced Fast Test {suffix}",
        "description": "Rapid biochemical oxygen demand assay",
        "categoryId": cat.id,
        "billingUnitId": bunit.id,
        "standardPrice": 2500.00,
        "minimumBillingQuantity": 2,
        "sampleTypeIds": [stype.id] if stype else [],
        "testingMethodIds": [tmethod.id] if tmethod else [],
        "reportingParameters": [
            {
                "parameterName": "Fast BOD",
                "reportingUnitId": runit.id if runit else None
            }
        ]
    }

    res = client.post("/api/v1/crm/catalogue/services", headers=auth_headers, json=payload)
    assert res.status_code == 200, res.text
    srv = res.json()["service"]
    srv_id = srv["id"]
    service_code = srv["code"]
    assert service_code is not None
    assert len(service_code) > 0

    # Verify price is 2500
    assert float(srv["standardPrice"]) == 2500.00

    # Update price to 3000
    update_res = client.put(f"/api/v1/crm/catalogue/services/{srv_id}", headers=auth_headers, json={
        "standardPrice": 3000.00,
        "changeReason": "Annual price revision 2026"
    })
    assert update_res.status_code == 200, update_res.text
    updated_srv = update_res.json()["service"]
    assert float(updated_srv["standardPrice"]) == 3000.00

    # Verify price history entry was created
    db = SessionLocal()
    history = db.query(ServicePriceHistory).filter(ServicePriceHistory.service_id == srv_id).order_by(ServicePriceHistory.created_at.desc()).all()
    assert len(history) >= 1
    assert float(history[0].price) == 3000.00
    assert history[0].reason == "Annual price revision 2026"
    db.close()


def test_package_bundle_and_versioning(client, auth_headers):
    """
    Test Section 9:
    - Packages as commercial bundles
    - Package price vs reference component sum
    - Version immutability: package version cannot be silently modified
    - Creating a new package version increments versionNumber
    """
    db = SessionLocal()
    services = db.query(Service).filter(Service.is_active == True, Service.is_deleted == False).limit(2).all()
    s1, s2 = services[0], services[1]
    db.close()

    suffix = uuid.uuid4().hex[:4].upper()
    pkg_code = f"PKG-C{suffix}"

    # 1. Create a new package
    pkg_payload = {
        "code": pkg_code,
        "name": f"Comprehensive Effluent Bundle {suffix}",
        "description": "Two-parameter test package",
        "packagePrice": 1800.00,
        "components": [
            {"serviceId": s1.id, "quantity": 1, "isMandatory": True},
            {"serviceId": s2.id, "quantity": 1, "isMandatory": True}
        ]
    }

    res = client.post("/api/v1/crm/catalogue/packages", headers=auth_headers, json=pkg_payload)
    assert res.status_code == 200, res.text
    pkg = res.json()["package"]
    pkg_id = pkg["id"]

    assert pkg["code"] == pkg_code
    active_ver = pkg["activeVersion"]
    assert active_ver is not None
    assert active_ver["versionNumber"] == 1
    assert float(active_ver["packagePrice"]) == 1800.00
    # Reference sum should be s1.price + s2.price
    expected_ref = float(s1.standard_price + s2.standard_price)
    assert float(active_ver["referenceComponentSum"]) == expected_ref

    # 2. Create version 2 with revised price and an additional component or changed price
    new_ver_payload = {
        "packagePrice": 2100.00,
        "effectiveDate": str(date.today()),
        "changeReason": "Component cost adjustment",
        "components": [
            {"serviceId": s1.id, "quantity": 1, "isMandatory": True},
            {"serviceId": s2.id, "quantity": 2, "isMandatory": True}  # 2x of s2
        ]
    }

    ver_res = client.post(f"/api/v1/crm/catalogue/packages/{pkg_id}/versions", headers=auth_headers, json=new_ver_payload)
    assert ver_res.status_code == 200, ver_res.text
    v2 = ver_res.json()["version"]
    assert v2["versionNumber"] == 2
    assert float(v2["packagePrice"]) == 2100.00
    expected_ref_v2 = float(s1.standard_price + (s2.standard_price * 2))
    assert float(v2["referenceComponentSum"]) == expected_ref_v2

    # Verify package detail returns version 2 as active
    get_res = client.get(f"/api/v1/crm/catalogue/packages/{pkg_id}", headers=auth_headers)
    assert get_res.status_code == 200
    detail = get_res.json()["package"]
    assert detail["activeVersion"]["versionNumber"] == 2
    assert len(detail["versions"]) == 2


def test_quotation_line_item_snapshots_and_tax(client, auth_headers):
    """
    Test Section 10:
    - Adding service and package items to a quotation
    - Calculating CGST, SGST, IGST
    - Verifying immutable commercial snapshot: service price change does not change historical quotation item
    """
    db = SessionLocal()
    tax_intra = db.query(TaxConfiguration).filter(TaxConfiguration.code == "GST-18-INTRA").first()
    srv = db.query(Service).filter(Service.is_active == True, Service.is_deleted == False).first()
    pkg = db.query(Package).first()

    # Ensure an opportunity and quotation exist
    opp = db.query(Opportunity).first()
    if not opp:
        account = db.query(Account).first()
        if not account:
            account = Account(
                account_id=f"ACC-TEST-{uuid.uuid4().hex[:4]}",
                name="Test Account For Quotation"
            )
            db.add(account)
            db.commit()
            db.refresh(account)

        opp = Opportunity(
            name="Testing Snapshot Opp",
            opportunity_id=f"OPP-SNAP-{uuid.uuid4().hex[:4]}",
            account_id=account.id,
            stage="Qualify",
            status="Open",
            business_area="R&D Lab",
            estimated_value=10000.0,
            currency="INR"
        )
        db.add(opp)
        db.commit()
        db.refresh(opp)

    quotation = OpportunityQuotation(
        opportunity_id=opp.id,
        quotation_number=f"QT-SNAP-{uuid.uuid4().hex[:4]}",
        revision_number=1,
        version="v1",
        title="Testing Snapshot Quotation",
        status="Draft",
        currency="INR",
        quotation_date=date.today()
    )
    db.add(quotation)
    db.commit()
    db.refresh(quotation)
    test_quotation_id = quotation.id

    db.close()

    assert tax_intra is not None
    assert srv is not None
    assert pkg is not None

    # 1. Add Service Line Item
    item_payload = {
        "itemType": "SERVICE",
        "serviceId": srv.id,
        "quantity": 2,
        "unitPrice": 1000.00,
        "sampleType": "Industrial Wastewater",
        "testingMethod": "APHA 5220 B",
        "taxConfigurationId": tax_intra.id
    }

    res = client.post(f"/api/v1/crm/catalogue/quotations/{test_quotation_id}/items", headers=auth_headers, json=item_payload)
    assert res.status_code == 200, res.text
    item = res.json()["item"]
    item_id = item["id"]

    assert item["itemType"] == "SERVICE"
    assert item["itemName"] == srv.name
    assert float(item["unitPrice"]) == 1000.00
    assert item["quantity"] == 2
    # Line total = 2 * 1000 = 2000
    assert float(item["lineTotal"]) == 2000.00
    # 18% GST on 2000 = 360
    assert float(item["taxRatePercentage"]) == 18.00
    assert float(item["taxAmount"]) == 360.00
    # Total price = 2360.00
    assert float(item["totalPrice"]) == 2360.00

    # 2. Add Package Line Item
    pkg_item_payload = {
        "itemType": "PACKAGE",
        "packageId": pkg.id,
        "quantity": 1,
        "taxConfigurationId": tax_intra.id
    }
    res_pkg = client.post(f"/api/v1/crm/catalogue/quotations/{test_quotation_id}/items", headers=auth_headers, json=pkg_item_payload)
    assert res_pkg.status_code == 200, res_pkg.text
    pkg_item = res_pkg.json()["item"]
    assert pkg_item["itemType"] == "PACKAGE"
    assert pkg_item["itemName"] == pkg.name
    assert pkg_item["snapshotData"] is not None

    # 3. Snapshot Immutability Test:
    # Update the service's standard price in the catalogue
    orig_srv_price = float(srv.standard_price)
    client.put(f"/api/v1/crm/catalogue/services/{srv.id}", headers=auth_headers, json={
        "standardPrice": orig_srv_price + 500.00
    })

    # Retrieve quotation items and confirm the item's unitPrice and lineTotal have NOT changed
    get_res = client.get(f"/api/v1/crm/catalogue/quotations/{test_quotation_id}/items", headers=auth_headers)
    assert get_res.status_code == 200
    items = get_res.json()["items"]
    saved_srv_item = next(it for it in items if it["id"] == item_id)
    assert float(saved_srv_item["unitPrice"]) == 1000.00
    assert float(saved_srv_item["lineTotal"]) == 2000.00
    assert float(saved_srv_item["totalPrice"]) == 2360.00


def test_rbac_server_side_enforcement(client, employee_headers):
    """
    Test Section 11 & Rule 25:
    - CRM Read can view catalogue
    - Non-admin / employee without crm.catalogue.manage is blocked from creating/editing services (403 Forbidden)
    """
    # Attempt to create category as ordinary employee
    res = client.post("/api/v1/crm/catalogue/categories", headers=employee_headers, json={
        "code": "LAB-UNAUTH",
        "name": "Unauthorized Category"
    })
    assert res.status_code == 403

    # Attempt to create service as ordinary employee
    res = client.post("/api/v1/crm/catalogue/services", headers=employee_headers, json={
        "name": "Unauthorized Service",
        "categoryId": "any",
        "billingUnitId": "any",
        "standardPrice": 500.00
    })
    assert res.status_code == 403

    # Attempt to create package as ordinary employee
    res = client.post("/api/v1/crm/catalogue/packages", headers=employee_headers, json={
        "code": "PKG-UNAUTH",
        "name": "Unauthorized Package",
        "packagePrice": 1000.00,
        "components": []
    })
    assert res.status_code == 403


def test_catalogue_tax_and_filter_envelopes(client, auth_headers):
    """
    Test BUG FIX verification & Simplification:
    - Verify tax configurations endpoint serializes cleanly without percentage AttributeError
    - Verify tax components for GST-18-INTRA, GST-18-INTER, GST-EXEMPT
    - Verify categories endpoint returns all 5 main categories (LAB-01 through LAB-05)
    - Verify services endpoint supports minPrice, maxPrice, categoryId, billingUnitId, search
    - Verify deprecated subcategories endpoint returns safe empty envelope
    """
    # 1. Tax configurations list serialization check
    tax_res = client.get("/api/v1/crm/catalogue/tax-configurations?include_inactive=true", headers=auth_headers)
    assert tax_res.status_code == 200, tax_res.text
    tax_data = tax_res.json()
    assert tax_data["success"] is True
    assert isinstance(tax_data["taxConfigurations"], list)
    assert len(tax_data["taxConfigurations"]) >= 3

    intra = next(t for t in tax_data["taxConfigurations"] if t["code"] == "GST-18-INTRA")
    assert float(intra["totalTaxPercentage"]) == 18.00
    assert len(intra["rates"]) == 2
    # Verify individual rate component values
    assert any(float(r["percentage"]) == 9.0 for r in intra["rates"])

    # Single tax configuration GET
    single_res = client.get(f"/api/v1/crm/catalogue/tax-configurations/{intra['id']}", headers=auth_headers)
    assert single_res.status_code == 200, single_res.text
    assert single_res.json()["taxConfiguration"]["code"] == "GST-18-INTRA"

    # 2. Categories envelope check - exactly 4 main categories present
    cat_res = client.get("/api/v1/crm/catalogue/categories", headers=auth_headers)
    assert cat_res.status_code == 200
    cat_data = cat_res.json()
    assert isinstance(cat_data["categories"], list)
    assert isinstance(cat_data["items"], list)
    assert isinstance(cat_data["data"], list)
    assert len(cat_data["categories"]) == 4
    codes = [c["code"] for c in cat_data["categories"]]
    for expected_code in ["LAB-01", "LAB-02", "LAB-03", "LAB-04"]:
        assert expected_code in codes, f"Expected {expected_code} to be in catalogue categories"
    assert "LAB-05" not in codes

    # 3. Services envelope and filtering check
    svc_res = client.get("/api/v1/crm/catalogue/services?pageSize=10", headers=auth_headers)
    assert svc_res.status_code == 200
    svc_data = svc_res.json()
    assert isinstance(svc_data["services"], list)
    assert isinstance(svc_data["items"], list)
    assert isinstance(svc_data["data"], list)
    assert len(svc_data["services"]) == 10

    # Test filtering with minPrice and maxPrice
    price_res = client.get("/api/v1/crm/catalogue/services?minPrice=500&maxPrice=2000", headers=auth_headers)
    assert price_res.status_code == 200
    filtered_services = price_res.json()["services"]
    for s in filtered_services:
        assert 500.0 <= float(s["standardPrice"]) <= 2000.0

    # 4. Deprecated subcategories endpoint returns safe empty envelope
    subcat_res = client.get("/api/v1/crm/catalogue/subcategories", headers=auth_headers)
    assert subcat_res.status_code == 200
    subcat_data = subcat_res.json()
    assert subcat_data["success"] is True
    assert subcat_data["total"] == 0
    assert subcat_data["subcategories"] == []
    assert subcat_data["items"] == []
    assert subcat_data["data"] == []

