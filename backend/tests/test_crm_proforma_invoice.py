import pytest
from decimal import Decimal
from datetime import date, datetime
from app.core.database import SessionLocal
import app.models
from app.crm.model import Opportunity, OpportunityQuotation, Account, Contact
from app.crm.catalogue_model import ServiceCategory, Service, TaxConfiguration, TaxRate, BillingUnit
from app.crm.invoice_model import CrmCompanySettings, ProformaInvoice, ProformaInvoiceRevision, ProformaInvoiceItem
from app.crm.invoice_service import ProformaInvoiceService, format_inr, get_financial_year


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_crm_data(db_session):
    # Ensure Account
    account = db_session.query(Account).filter(Account.name == "ALCHEMY CLEANTECH TEST").first()
    if not account:
        account = Account(
            account_id="ACC-TEST-001",
            customer_id="TS-ACPL-OCT26",
            name="ALCHEMY CLEANTECH TEST",
            address="Plot 54A, Flat 102\nGyandeep CHS, Sector 14\nNavi Mumbai",
            billing_address="Plot 54A, Flat 102\nGyandeep CHS, Sector 14\nNavi Mumbai",
            gst_number="27ABBCA6948A1ZU",
            pan_number="ABBCA6948A",
            phone="+91-9876543210",
            email="contact@alchemycleantech.com"
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)

    # Ensure Contact
    contact = db_session.query(Contact).filter(Contact.account_id == account.id).first()
    if not contact:
        contact = Contact(
            contact_id="CON-TEST-001",
            account_id=account.id,
            name="Sharvil Shah",
            first_name="Sharvil",
            last_name="Shah",
            email="sharvil@alchemycleantech.com",
            mobile_number="+91-9876543210",
            is_primary=True
        )
        db_session.add(contact)
        db_session.commit()

    # Ensure Opportunity
    opp = db_session.query(Opportunity).filter(Opportunity.name == "Waste Water Characterization Test Opp").first()
    if not opp:
        opp = Opportunity(
            opportunity_id="OPP-TEST-001",
            account_id=account.id,
            name="Waste Water Characterization Test Opp",
            stage="Offer",
            estimated_value=50000.0,
            currency="INR"
        )
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

    # Clean existing test PIs and quotations for test isolation
    db_session.query(ProformaInvoice).filter(ProformaInvoice.opportunity_id == opp.id).delete()
    db_session.commit()

    # Ensure Category & Services
    cat = db_session.query(ServiceCategory).filter(ServiceCategory.code == "LAB-01").first()
    if not cat:
        cat = ServiceCategory(code="LAB-01", name="PHYSICAL CHARACTERISTICS", is_active=True)
        db_session.add(cat)
        db_session.commit()
        db_session.refresh(cat)

    unit = db_session.query(BillingUnit).filter(BillingUnit.code == "TEST").first()
    if not unit:
        unit = BillingUnit(code="TEST", name="Per Test", is_active=True)
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)

    svc_ph = db_session.query(Service).filter(Service.name == "pH").first()
    if not svc_ph:
        svc_ph = Service(
            service_code="LAB-02-002",
            name="pH",
            category_id=cat.id,
            billing_unit_id=unit.id,
            standard_price=Decimal("100.00"),
            is_active=True
        )
        db_session.add(svc_ph)

    svc_cod = db_session.query(Service).filter(Service.name == "COD mg/l").first()
    if not svc_cod:
        svc_cod = Service(
            service_code="LAB-02-005",
            name="COD mg/l",
            category_id=cat.id,
            billing_unit_id=unit.id,
            standard_price=Decimal("1000.00"),
            is_active=True
        )
        db_session.add(svc_cod)

    # Tax Config
    tax = db_session.query(TaxConfiguration).filter(TaxConfiguration.name == "GST 18%").first()
    if not tax:
        tax = TaxConfiguration(code="TAX-GST-18", name="GST 18%", tax_type="INTRA_STATE", is_active=True)
        db_session.add(tax)
        db_session.flush()
        r1 = TaxRate(configuration_id=tax.id, component_name="CGST", rate_percentage=Decimal("9.0"), is_active=True)
        r2 = TaxRate(configuration_id=tax.id, component_name="SGST", rate_percentage=Decimal("9.0"), is_active=True)
        db_session.add_all([r1, r2])

    db_session.commit()
    return {"account": account, "opportunity": opp, "services": [svc_ph, svc_cod], "tax": tax}


def test_company_settings_api(client, auth_headers):
    """Verify Company & Invoice Configuration GET and Admin PUT."""
    # 1. GET Settings
    res = client.get("/api/v1/crm/company-settings", headers=auth_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "REVY Environmental Solutions" in data["companyName"]
    assert data["bankName"] == "Bank Of Baroda, Alkapuri Branch"
    assert data["bankAccountNumber"] == "01880200001183"
    assert data["bankIfsc"] == "BARB0ALKAPU"

    # 2. PUT Settings (update signatory / terms)
    update_res = client.put("/api/v1/crm/company-settings", headers=auth_headers, json={
        "signatoryTitle": "Managing Director",
        "serviceDescription": "Advanced Waste Water & Bio-methanation Testing"
    })
    assert update_res.status_code == 200, update_res.text
    up_data = update_res.json()
    assert up_data["signatoryTitle"] == "Managing Director"
    assert up_data["serviceDescription"] == "Advanced Waste Water & Bio-methanation Testing"


def test_financial_year_pi_numbering(db_session):
    """Verify sequential PI numbering in REVY/PI/YYYY-YY/XXXX format."""
    inv_service = ProformaInvoiceService(db_session)

    # Test FY calculation
    assert get_financial_year(date(2026, 10, 29)) == "2026-27"
    assert get_financial_year(date(2027, 2, 15)) == "2026-27"
    assert get_financial_year(date(2027, 4, 1)) == "2027-28"

    # Test sequential generation
    num1, fy1 = inv_service.get_next_pi_number(date(2026, 10, 29), commit=True)
    assert num1.startswith("REVY/PI/2026-27/")
    num2, fy2 = inv_service.get_next_pi_number(date(2026, 11, 1), commit=True)
    assert num2.startswith("REVY/PI/2026-27/")

    seq1 = int(num1.split("/")[-1])
    seq2 = int(num2.split("/")[-1])
    assert seq2 == seq1 + 1


def test_quotation_save_single_current(client, auth_headers, sample_crm_data):
    """Verify saving a quotation maintains only a single current quotation and replaces items."""
    opp = sample_crm_data["opportunity"]
    svc1 = sample_crm_data["services"][0]
    svc2 = sample_crm_data["services"][1]

    # 1. Save quotation with 2 items
    payload = {
        "title": "Initial Quotation for Opp",
        "taxType": "INTRA_STATE",
        "items": [
            {
                "itemType": "SERVICE",
                "serviceId": svc1.id,
                "quantity": 8,
                "unitPrice": 100.0
            },
            {
                "itemType": "SERVICE",
                "serviceId": svc2.id,
                "quantity": 4,
                "unitPrice": 1000.0
            }
        ]
    }

    res = client.post(f"/api/v1/crm/opportunities/{opp.id}/quotations/save-current", headers=auth_headers, json=payload)
    assert res.status_code == 200, res.text
    q_data = res.json()["quotation"]
    assert q_data["quotationNumber"].startswith("QT-")
    assert len(q_data["items"]) == 2
    # 8*100 = 800; 4*1000 = 4000; subtotal = 4800
    assert q_data["subtotal"] == 4800.0
    # CGST 9% (432) + SGST 9% (432) = 864 tax
    assert q_data["totalTax"] == 864.0
    assert q_data["amount"] == 5664.0
    assert "QUOTATION DETAILS" in q_data["emailText"]

    quotation_id = q_data["id"]

    # 2. Re-save/update quotation with custom one-time item and negotiated price (replaces previous items)
    payload2 = {
        "title": "Negotiated Quotation for Opp",
        "taxType": "INTRA_STATE",
        "items": [
            {
                "itemType": "SERVICE",
                "serviceId": svc1.id,
                "quantity": 5,
                "unitPrice": 90.0  # Negotiated price
            },
            {
                "itemType": "CUSTOM_SERVICE",
                "itemName": "Special Bioassay Trial",
                "description": "Custom laboratory trial on industrial effluent",
                "billingUnit": "Trial",
                "quantity": 1,
                "unitPrice": 15000.0,
                "savePermanently": False
            }
        ]
    }

    res2 = client.post(f"/api/v1/crm/opportunities/{opp.id}/quotations/save-current", headers=auth_headers, json=payload2)
    assert res2.status_code == 200, res2.text
    q2_data = res2.json()["quotation"]
    # Same quotation ID, no new revision created
    assert q2_data["id"] == quotation_id
    assert len(q2_data["items"]) == 2
    # 5*90 = 450; 1*15000 = 15000; subtotal = 15450
    assert q2_data["subtotal"] == 15450.0
    assert q2_data["totalTax"] == 15450.0 * 0.18
    assert "Special Bioassay Trial" in q2_data["emailText"]


def test_proforma_invoice_preview_no_sequence_consumed(client, auth_headers, sample_crm_data):
    """Verify preview calculates totals and renders HTML without consuming sequential PI number."""
    opp = sample_crm_data["opportunity"]

    # Get current quotation
    q_res = client.get(f"/api/v1/crm/opportunities/{opp.id}/quotations/current", headers=auth_headers)
    assert q_res.status_code == 200
    q = q_res.json()["quotation"]

    preview_payload = {
        "opportunity_id": opp.id,
        "quotation_id": q["id"],
        "tax_type": "INTRA_STATE",
        "items": [
            {
                "name": "Analysis of pH",
                "quantity": 8,
                "rate": 100.0,
                "unit": "Test"
            },
            {
                "name": "COD mg/l",
                "quantity": 2,
                "rate": 1000.0,
                "unit": "Test"
            }
        ]
    }

    res = client.post("/api/v1/crm/proforma-invoices/preview", headers=auth_headers, json=preview_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["previewNumber"] == "DRAFT-PREVIEW"
    assert data["totals"]["subtotal"] == 2800.0
    assert "PROFORMA INVOICE" in data["html"]
    assert "DRAFT-PREVIEW" in data["html"]

    # Verify no PI was actually saved to database
    col_res = client.get("/api/v1/crm/collateral?view=invoices", headers=auth_headers)
    assert col_res.status_code == 200
    assert col_res.json()["totalCount"] == 0


def test_approve_quotation_and_create_invoice_flow(client, auth_headers, sample_crm_data):
    """Complete workflow: Approve Quotation & Create PI -> Sequential Number -> Revision 1 -> Revision 2."""
    opp = sample_crm_data["opportunity"]

    # 1. Fetch current quotation
    q_res = client.get(f"/api/v1/crm/opportunities/{opp.id}/quotations/current", headers=auth_headers)
    q = q_res.json()["quotation"]

    # 2. Confirm and Create PI
    create_payload = {
        "opportunity_id": opp.id,
        "quotation_id": q["id"],
        "tax_type": "INTRA_STATE",
        "reference_note": "Samples received from Vadodara site",
        "items": [
            {
                "sr_no": 1,
                "name": "Analysis of pH",
                "quantity": 8,
                "rate": 100.0,
                "unit": "Test"
            },
            {
                "sr_no": 2,
                "name": "Analysis of COD",
                "quantity": 4,
                "rate": 1000.0,
                "unit": "Test"
            }
        ]
    }

    create_res = client.post("/api/v1/crm/proforma-invoices", headers=auth_headers, json=create_payload)
    assert create_res.status_code == 200, create_res.text
    create_data = create_res.json()
    pi_id = create_data["proformaInvoiceId"]
    pi_number = create_data["piNumber"]
    assert pi_number.startswith("REVY/PI/")

    # 3. Verify PI details and Revision 1
    detail_res = client.get(f"/api/v1/crm/proforma-invoices/{pi_id}", headers=auth_headers)
    assert detail_res.status_code == 200, detail_res.text
    pi = detail_res.json()["proformaInvoice"]
    assert pi["currentRevisionNumber"] == 1
    assert len(pi["revisions"]) == 1
    rev1 = pi["currentRevision"]
    assert rev1["revisionNumber"] == 1
    assert rev1["subtotal"] == 4800.0
    assert rev1["grandTotal"] == 5664.0
    assert len(rev1["items"]) == 2

    # 4. Create Revision 2 (editing PI rates/quantities)
    rev2_payload = {
        "tax_type": "INTRA_STATE",
        "reference_note": "Revised quantities as per updated batch volume",
        "items": [
            {
                "sr_no": 1,
                "name": "Analysis of pH",
                "quantity": 10,  # increased from 8
                "rate": 100.0,
                "unit": "Test"
            },
            {
                "sr_no": 2,
                "name": "Analysis of COD",
                "quantity": 4,
                "rate": 1000.0,
                "unit": "Test"
            }
        ]
    }
    rev_res = client.post(f"/api/v1/crm/proforma-invoices/{pi_id}/revisions", headers=auth_headers, json=rev2_payload)
    assert rev_res.status_code == 200, rev_res.text
    assert rev_res.json()["revisionNumber"] == 2

    # 5. Verify Revision 2 is current and Revision 1 is immutably preserved
    detail2_res = client.get(f"/api/v1/crm/proforma-invoices/{pi_id}", headers=auth_headers)
    pi2 = detail2_res.json()["proformaInvoice"]
    assert pi2["currentRevisionNumber"] == 2
    assert len(pi2["revisions"]) == 2

    rev2 = pi2["currentRevision"]
    assert rev2["revisionNumber"] == 2
    assert rev2["subtotal"] == 5000.0  # 10*100 + 4*1000 = 5000
    assert rev2["grandTotal"] == 5900.0

    # Revision 1 still has subtotal 4800
    old_rev1 = next(r for r in pi2["revisions"] if r["revisionNumber"] == 1)
    assert old_rev1["subtotal"] == 4800.0

    # 6. Verify HTML output for both revisions
    html_rev2 = client.get(f"/api/v1/crm/proforma-invoices/{pi_id}/html", headers=auth_headers)
    assert html_rev2.status_code == 200
    assert "Rev 2" in html_rev2.text
    assert "5,900.00" in html_rev2.text

    html_rev1 = client.get(f"/api/v1/crm/proforma-invoices/{pi_id}/html?revision=1", headers=auth_headers)
    assert html_rev1.status_code == 200
    assert "5,664.00" in html_rev1.text

    # 7. Verify Collateral Summary lists this opportunity in both views
    col_q = client.get("/api/v1/crm/collateral?view=quotations", headers=auth_headers)
    assert col_q.status_code == 200
    assert any(item["opportunityId"] == opp.id for item in col_q.json()["items"])

    col_inv = client.get("/api/v1/crm/collateral?view=invoices", headers=auth_headers)
    assert col_inv.status_code == 200
    inv_item = next(item for item in col_inv.json()["items"] if item["opportunityId"] == opp.id)
    assert inv_item["piNumber"] == pi_number
    assert inv_item["piRevisionNumber"] == 2
