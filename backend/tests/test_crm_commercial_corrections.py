import os
import json
import uuid
import pytest
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Ensure testing mode is on
os.environ["TESTING"] = "1"

from app.core.database import SessionLocal, init_db
from app.core.exceptions import ValidationError
from app.crm.financial_service import FinancialCalculator, format_inr, format_qty
from app.crm.permissions import (
    is_crm_admin_or_manager,
    is_crm_user,
    require_crm_read,
    require_crm_write,
)
from app.crm.catalogue_service import CatalogueService
from app.crm.catalogue_seed import seed_catalogue_data
from app.crm.catalogue_schema import QuotationItemInput
from app.crm.invoice_service import ProformaInvoiceService, get_financial_year
from app.crm.invoice_schema import (
    ProformaInvoiceCreate,
    ProformaInvoiceUpdate,
    ProformaInvoiceItemInput,
    ProformaInvoicePreviewRequest,
)
from app.crm.catalogue_model import (
    Service,
    ServiceCategory,
    Package,
    PackageVersion,
    PackageComponent,
    PackageAddOnConfiguration,
    BillingUnit,
    Currency,
    TaxConfiguration,
)
from app.crm.model import (
    Account,
    Contact,
    Opportunity,
    OpportunityQuotation,
    OpportunityQuotationItem,
    ProformaInvoice,
    ProformaInvoiceItem,
)
from app.audit.model import AuditLog


class MockActor:
    id = "test-admin-id"
    username = "admin"
    name = "Admin"
    roles = ["CRM_ADMIN"]
    is_global_admin = True
    active_role = "CRM_ADMIN"
    modules = ["CRM"]


@pytest.fixture(scope="module")
def db():
    init_db()
    session = SessionLocal()
    try:
        seed_catalogue_data(session)
    except Exception:
        pass
    yield session
    session.close()


# =============================================================================
# 1. FINANCIAL CALCULATION ENGINE & ACCEPTANCE FIXTURE
# =============================================================================

def test_financial_calculator_acceptance_fixture():
    """
    Acceptance test fixture from requirement:
    - 1 line item: Quantity = 10, Unit Price = 1,000, Discount = 500
    - Gross subtotal = 10 * 1,000 = 10,000
    - Discount = 500
    - Taxable amount = 10,000 - 500 = 9,500
    - GST 18% Intra-State:
      * CGST (9%) = 855.00
      * SGST (9%) = 855.00
      * Total Tax = 1,710.00
      * Grand Total = 11,210.00
    """
    items = [
        {
            "quantity": 10,
            "unit_price": Decimal("1000.00"),
            "discount_amount": Decimal("500.00")
        }
    ]

    calc = FinancialCalculator.calculate_commercial_totals(
        items=items,
        tax_type="INTRA_STATE",
        cgst_rate=Decimal("9.00"),
        sgst_rate=Decimal("9.00"),
        igst_rate=Decimal("18.00"),
    )

    assert calc.gross_subtotal == Decimal("10000.00")
    assert calc.total_discount == Decimal("500.00")
    assert calc.taxable_amount == Decimal("9500.00")
    assert calc.cgst_amount == Decimal("855.00")
    assert calc.sgst_amount == Decimal("855.00")
    assert calc.igst_amount == Decimal("0.00")
    assert calc.total_tax == Decimal("1710.00")
    assert calc.grand_total == Decimal("11210.00")

    # Also test INTER_STATE for same fixture
    calc_inter = FinancialCalculator.calculate_commercial_totals(
        items=items,
        tax_type="INTER_STATE",
        cgst_rate=Decimal("9.00"),
        sgst_rate=Decimal("9.00"),
        igst_rate=Decimal("18.00"),
    )
    assert calc_inter.gross_subtotal == Decimal("10000.00")
    assert calc_inter.total_discount == Decimal("500.00")
    assert calc_inter.taxable_amount == Decimal("9500.00")
    assert calc_inter.cgst_amount == Decimal("0.00")
    assert calc_inter.sgst_amount == Decimal("0.00")
    assert calc_inter.igst_amount == Decimal("1710.00")
    assert calc_inter.total_tax == Decimal("1710.00")
    assert calc_inter.grand_total == Decimal("11210.00")


def test_financial_calculator_half_up_paise_rounding():
    """
    Test half-up paise rounding for commercial financial accuracy.
    """
    # 1. Fractional CGST: 1,234.55 * 0.09 = 111.1095 -> 111.11
    item1 = [{"quantity": 1, "unit_price": Decimal("1234.55"), "discount_amount": Decimal("0.00")}]
    calc1 = FinancialCalculator.calculate_commercial_totals(
        items=item1,
        tax_type="INTRA_STATE",
        cgst_rate=Decimal("9.00"),
        sgst_rate=Decimal("9.00")
    )
    assert calc1.cgst_amount == Decimal("111.11")
    assert calc1.sgst_amount == Decimal("111.11")
    assert calc1.total_tax == Decimal("222.22")
    assert calc1.grand_total == Decimal("1456.77")

    # 2. Exact half: 1,234.50 * 0.09 = 111.105 -> 111.11 (ROUND_HALF_UP)
    item2 = [{"quantity": 1, "unit_price": Decimal("1234.50"), "discount_amount": Decimal("0.00")}]
    calc2 = FinancialCalculator.calculate_commercial_totals(
        items=item2,
        tax_type="INTRA_STATE",
        cgst_rate=Decimal("9.00"),
        sgst_rate=Decimal("9.00")
    )
    assert calc2.cgst_amount == Decimal("111.11")

    # 3. Below half: 1,234.49 * 0.09 = 111.1041 -> 111.10
    item3 = [{"quantity": 1, "unit_price": Decimal("1234.49"), "discount_amount": Decimal("0.00")}]
    calc3 = FinancialCalculator.calculate_commercial_totals(
        items=item3,
        tax_type="INTRA_STATE",
        cgst_rate=Decimal("9.00"),
        sgst_rate=Decimal("9.00")
    )
    assert calc3.cgst_amount == Decimal("111.10")


def test_discount_validation():
    """
    Discount cannot be negative and cannot exceed gross line amount.
    """
    # Negative discount
    with pytest.raises((ValueError, ValidationError)):
        FinancialCalculator.calculate_commercial_totals(
            items=[{"quantity": 2, "unit_price": Decimal("500.00"), "discount_amount": Decimal("-50.00")}],
            tax_type="INTRA_STATE"
        )

    # Discount exceeding gross
    with pytest.raises((ValueError, ValidationError)):
        FinancialCalculator.calculate_commercial_totals(
            items=[{"quantity": 2, "unit_price": Decimal("500.00"), "discount_amount": Decimal("1001.00")}],
            tax_type="INTRA_STATE"
        )


# =============================================================================
# 2. USER PERMISSIONS / RBAC MATRIX
# =============================================================================

def test_rbac_user_permissions_matrix():
    """
    Verify RBAC Matrix:
    - View quotations/PI: CRM Admin, CRM Manager, Other CRM users (Yes)
    - Create/Edit quotation: CRM Admin (Yes), CRM Manager (Yes), Other CRM users (No - 403 Forbidden)
    - Generate/Edit PI: CRM Admin (Yes), CRM Manager (Yes), Other CRM users (No - 403 Forbidden)
    """
    class MockUser:
        def __init__(self, roles):
            self.roles = roles

    admin_user = MockUser(["CRM_ADMIN"])
    manager_user = MockUser(["CRM_MANAGER"])
    it_admin_user = MockUser(["IT_ADMIN"])
    rep_user = MockUser(["CRM_EXECUTIVE"])
    other_user = MockUser(["EMPLOYEE"])
    unrelated_user = MockUser(["GUEST"])

    # 1. is_crm_admin_or_manager
    assert is_crm_admin_or_manager(admin_user) is True
    assert is_crm_admin_or_manager(manager_user) is True
    assert is_crm_admin_or_manager(it_admin_user) is True
    assert is_crm_admin_or_manager(rep_user) is False
    assert is_crm_admin_or_manager(other_user) is False

    # 2. is_crm_user
    assert is_crm_user(admin_user) is True
    assert is_crm_user(manager_user) is True
    assert is_crm_user(rep_user) is True
    assert is_crm_user(unrelated_user) is False

    # 3. require_crm_write: allows Admin/Manager, rejects rep_user with 403
    assert require_crm_write(admin_user) == admin_user
    assert require_crm_write(manager_user) == manager_user
    with pytest.raises(HTTPException) as exc_info:
        require_crm_write(rep_user)
    assert exc_info.value.status_code == 403
    assert "CRM Admin and CRM Manager" in exc_info.value.detail

    # 4. require_crm_read: allows both Admin/Manager and regular CRM users (rep_user)
    assert require_crm_read(admin_user) == admin_user
    assert require_crm_read(rep_user) == rep_user
    with pytest.raises(HTTPException) as exc_read:
        require_crm_read(unrelated_user)
    assert exc_read.value.status_code == 403


# =============================================================================
# 3. PACKAGE AND ADD-ON VALIDATION
# =============================================================================

def test_package_addon_eligibility_and_overrides(db: Session):
    """
    Verify PackageAddOnConfiguration enforcement:
    - Addon must be attached to a package in the same quotation
    - Addon must be configured in PackageAddOnConfiguration
    - Overridden price and default quantity are applied
    - Disallows invalid or unconfigured add-ons
    """
    cat_service = CatalogueService(db)
    actor = MockActor()

    # Find the seeded package PKG-001 (Sludge Analysis Package) and configured add-on C/N Ratio
    package = db.query(Package).filter(Package.package_code == "PKG-001").first()
    assert package is not None, "PKG-001 must be present from seed"

    srv_addon = db.query(Service).filter(Service.name.like("%C/N Ratio%")).first()
    assert srv_addon is not None, "C/N Ratio must be present from seed"

    # Find an active service that is NOT configured as add-on for PKG-001
    srv_unconfigured = db.query(Service).filter(
        Service.id != srv_addon.id,
        Service.is_active == True
    ).first()
    assert srv_unconfigured is not None

    # Create account, opportunity, quotation
    acc_id = f"ACC-{uuid.uuid4().hex[:6]}"
    account = Account(account_id=acc_id, name="GreenTech Solutions")
    db.add(account)
    db.flush()

    opp = Opportunity(
        opportunity_id=f"OPP-{uuid.uuid4().hex[:6]}",
        name="Biogas Feasibility Study",
        account_id=account.id,
        stage="Offer"
    )
    db.add(opp)
    db.flush()

    quote = OpportunityQuotation(
        opportunity_id=opp.id,
        quotation_number=f"QT-{uuid.uuid4().hex[:6]}",
        version="R1",
        revision_number=1,
        is_active=True,
        amount=Decimal("0.00"),
        subtotal=Decimal("0.00"),
        currency="INR",
        tax_type="INTRA_STATE",
    )
    db.add(quote)
    db.flush()

    # Add Package item to quotation
    pkg_item = cat_service.add_item_to_quotation(
        actor=actor,
        quotation_id=quote.id,
        payload=QuotationItemInput(
            itemType="PACKAGE",
            packageId=package.id,
            quantity=1,
        )
    )
    assert pkg_item.total_price == Decimal("2200.00")

    # 1. Add configured Addon item with parentItemId
    addon_item = cat_service.add_item_to_quotation(
        actor=actor,
        quotation_id=quote.id,
        payload=QuotationItemInput(
            itemType="ADDON",
            serviceId=srv_addon.id,
            parentItemId=pkg_item.id,
        )
    )
    # Seeded override price is ₹300.00 (overridden from standard price ₹600.00)
    assert addon_item.unit_price == Decimal("300.00")
    assert addon_item.total_price == Decimal("300.00")

    # 2. Reject Addon without parentItemId
    with pytest.raises((ValidationError, HTTPException)):
        cat_service.add_item_to_quotation(
            actor=actor,
            quotation_id=quote.id,
            payload=QuotationItemInput(
                itemType="ADDON",
                serviceId=srv_addon.id,
            )
        )

    # 3. Reject Addon not configured for the package version
    with pytest.raises((ValidationError, HTTPException)):
        cat_service.add_item_to_quotation(
            actor=actor,
            quotation_id=quote.id,
            payload=QuotationItemInput(
                itemType="ADDON",
                serviceId=srv_unconfigured.id,
                parentItemId=pkg_item.id,
            )
        )


# =============================================================================
# 4. QUOTATION REVISIONS: R1 -> R2 PRESERVATION
# =============================================================================

def test_quotation_automatic_revision_flow(db: Session):
    """
    Quotation revisions flow:
    - R1 is created
    - Non-material changes (e.g. notes) update in place without incrementing revision
    - Material change (modifying items, prices, discounts) preserves R1 (marked Superseded),
      and creates active revision R2 with copied line items.
    """
    cat_service = CatalogueService(db)
    actor = MockActor()

    acc_id = f"ACC-{uuid.uuid4().hex[:6]}"
    account = Account(account_id=acc_id, name="EcoBio Ltd")
    db.add(account)
    db.flush()

    opp = Opportunity(
        opportunity_id=f"OPP-{uuid.uuid4().hex[:6]}",
        name="ETP Revamp",
        account_id=account.id,
        stage="Offer"
    )
    db.add(opp)
    db.flush()

    srv = db.query(Service).filter(Service.is_active == True).first()
    assert srv is not None

    # Initial save: creates R1
    payload_r1 = {
        "title": "Initial Quotation",
        "taxType": "INTRA_STATE",
        "notes": "First draft",
        "items": [
            {
                "itemType": "SERVICE",
                "serviceId": srv.id,
                "itemName": srv.name,
                "quantity": 5,
                "unitPrice": 1000.0,
                "discountAmount": 200.0,
            }
        ]
    }
    quote_r1 = cat_service.save_current_quotation(
        actor=actor,
        opp_id=opp.id,
        payload=payload_r1
    )
    assert quote_r1.revision_number == 1
    assert quote_r1.version == "R1"
    assert quote_r1.is_active is True
    assert quote_r1.status in ("Draft", "Active")
    quote_r1_id = quote_r1.id

    # 1. Non-material update (notes change only) -> stays R1, same ID
    payload_non_material = {
        "title": "Initial Quotation",
        "taxType": "INTRA_STATE",
        "notes": "Updated notes without price alteration",
        "items": payload_r1["items"]
    }
    res_non_material = cat_service.save_current_quotation(
        actor=actor,
        opp_id=opp.id,
        payload=payload_non_material
    )
    assert res_non_material.id == quote_r1_id
    assert res_non_material.revision_number == 1

    # 2. Material update (quantity changed from 5 to 10 and discount changed)
    payload_r2 = {
        "title": "Revised Commercial Proposal",
        "taxType": "INTRA_STATE",
        "notes": "Revised with volume discount",
        "items": [
            {
                "itemType": "SERVICE",
                "serviceId": srv.id,
                "itemName": srv.name,
                "quantity": 10,
                "unitPrice": 1000.0,
                "discountAmount": 500.0,
            }
        ]
    }
    quote_r2 = cat_service.save_current_quotation(
        actor=actor,
        opp_id=opp.id,
        payload=payload_r2
    )

    # R2 created!
    assert quote_r2.revision_number == 2
    assert quote_r2.version == "R2"
    assert quote_r2.is_active is True
    assert quote_r2.status in ("Draft", "Active")
    assert quote_r2.id != quote_r1_id

    # Verify R1 is preserved in DB as Superseded
    r1_db = db.query(OpportunityQuotation).filter(OpportunityQuotation.id == quote_r1_id).first()
    assert r1_db is not None
    assert r1_db.is_active is False
    assert r1_db.status == "Superseded"
    assert len(r1_db.items) == 1
    assert r1_db.items[0].quantity == Decimal("5.0000")  # Original R1 item preserved!


# =============================================================================
# 5. CONCURRENCY-SAFE SEQUENCE GENERATION & PI WORKFLOW
# =============================================================================

def test_concurrency_safe_pi_numbering(db: Session):
    """
    Test concurrency-safe sequence generation with FY prefix.
    """
    inv_service = ProformaInvoiceService(db)

    pi_no_1, fy1 = inv_service.get_next_pi_number()
    pi_no_2, fy2 = inv_service.get_next_pi_number()

    assert pi_no_1.startswith(f"REVY/PI/{fy1}/")
    assert pi_no_2.startswith(f"REVY/PI/{fy2}/")

    seq1 = int(pi_no_1.split("/")[-1])
    seq2 = int(pi_no_2.split("/")[-1])
    assert seq2 == seq1 + 1


# =============================================================================
# 6. DIRECT PROFORMA INVOICE EDITING & AUDIT TRAIL
# =============================================================================

def test_proforma_invoice_direct_editing_with_audit_trail(db: Session):
    """
    Verify direct editing of issued PI:
    - Recalculates subtotal, discounts, GST, and grand total
    - Requires mandatory overrideReason
    - Creates AuditLog entry with action 'CRM_PROFORMA_INVOICE_EDITED' and diffs
    """
    inv_service = ProformaInvoiceService(db)
    cat_service = CatalogueService(db)
    actor = MockActor()

    acc_id = f"ACC-{uuid.uuid4().hex[:6]}"
    account = Account(account_id=acc_id, name="Zenith Biotech")
    db.add(account)
    db.flush()

    opp = Opportunity(
        opportunity_id=f"OPP-{uuid.uuid4().hex[:6]}",
        name="Biomass Evaluation",
        account_id=account.id,
        stage="Offer"
    )
    db.add(opp)
    db.flush()

    srv = db.query(Service).filter(Service.is_active == True).first()
    quote_res = cat_service.save_current_quotation(
        actor=actor,
        opp_id=opp.id,
        payload={
            "title": "Proposal for Zenith",
            "taxType": "INTRA_STATE",
            "items": [
                {"itemType": "SERVICE", "serviceId": srv.id, "itemName": srv.name, "quantity": 10, "unitPrice": 1000.0, "discountAmount": 500.0}
            ]
        }
    )
    quote_id = quote_res.id

    # Issue initial PI
    pi_create = ProformaInvoiceCreate(
        opportunity_id=opp.id,
        quotation_id=quote_id,
        tax_type="INTRA_STATE",
        items=[
            ProformaInvoiceItemInput(
                sr_no=1,
                name="BOD/COD Profile",
                quantity=10,
                unit="Test",
                rate=1000.0,
                discount_amount=500.0
            )
        ]
    )
    pi = inv_service.create_proforma_invoice(actor=actor, payload=pi_create)
    assert pi.total_amount == Decimal("11210.00")  # Acceptance fixture total!
    assert pi.discount_amount == Decimal("500.00")

    # 1. Reject edit without overrideReason
    with pytest.raises((ValueError, HTTPException)):
        inv_service.update_proforma_invoice(
            actor=actor,
            pi_id=pi.id,
            payload=ProformaInvoiceUpdate(
                overrideReason="",
                tax_type="INTRA_STATE",
                items=[
                    ProformaInvoiceItemInput(
                        sr_no=1,
                        name="BOD/COD Profile",
                        quantity=10,
                        unit="Test",
                        rate=900.0,
                        discount_amount=0.0
                    )
                ]
            )
        )

    # 2. Successful direct edit with overrideReason
    updated_pi = inv_service.update_proforma_invoice(
        actor=actor,
        pi_id=pi.id,
        payload=ProformaInvoiceUpdate(
            overrideReason="Approved 10% unit price discount instead of flat discount",
            tax_type="INTRA_STATE",
            items=[
                ProformaInvoiceItemInput(
                    sr_no=1,
                    name="BOD/COD Profile",
                    quantity=10,
                    unit="Test",
                    rate=900.0,
                    discount_amount=0.0
                )
            ]
        )
    )

    # 10 * 900 = 9,000 + 18% GST (1,620) = 10,620.00
    assert updated_pi.total_amount == Decimal("10620.00")
    assert updated_pi.subtotal_amount == Decimal("9000.00")

    # 3. Verify AuditLog record was created
    audit = db.query(AuditLog).filter(
        AuditLog.target_record_id == pi.id,
        AuditLog.action == "CRM_PROFORMA_INVOICE_EDITED"
    ).first()
    assert audit is not None
    assert audit.before_state["grand_total"] == 11210.00
    assert audit.after_state["grand_total"] == 10620.00
    details_obj = json.loads(audit.details) if audit.details else {}
    assert details_obj.get("override_reason") == "Approved 10% unit price discount instead of flat discount"


# =============================================================================
# 7. HTML PRINT / PDF OUTPUT STYLING
# =============================================================================

def test_proforma_invoice_html_print_styling(db: Session):
    """
    Verify HTML output includes:
    - -webkit-print-color-adjust: exact !important
    - print-color-adjust: exact !important
    - break-inside: avoid / page-break-inside: avoid
    - Gross subtotal, discount, taxable amount, and GST formatting when discount > 0
    """
    inv_service = ProformaInvoiceService(db)
    cat_service = CatalogueService(db)
    actor = MockActor()

    acc_id = f"ACC-{uuid.uuid4().hex[:6]}"
    account = Account(account_id=acc_id, name="Apex Biosystems", gst_number="24AAACA1234A1Z5")
    db.add(account)
    db.flush()

    opp = Opportunity(
        opportunity_id=f"OPP-{uuid.uuid4().hex[:6]}",
        name="Commercial Trial",
        account_id=account.id,
        stage="Offer"
    )
    db.add(opp)
    db.flush()

    srv = db.query(Service).filter(Service.is_active == True).first()
    quote_res = cat_service.save_current_quotation(
        actor=actor,
        opp_id=opp.id,
        payload={
            "title": "Apex Trial Proposal",
            "taxType": "INTRA_STATE",
            "items": [
                {"itemType": "SERVICE", "serviceId": srv.id, "itemName": srv.name, "quantity": 10, "unitPrice": 1000.0, "discountAmount": 500.0}
            ]
        }
    )
    quote_id = quote_res.id

    pi = inv_service.create_proforma_invoice(
        actor=actor,
        payload=ProformaInvoiceCreate(
            opportunity_id=opp.id,
            quotation_id=quote_id,
            tax_type="INTRA_STATE",
            items=[
                ProformaInvoiceItemInput(
                    sr_no=1,
                    name="Apex Microbial Assay",
                    quantity=10,
                    unit="Test",
                    rate=1000.0,
                    discount_amount=500.0
                )
            ]
        )
    )

    html = inv_service.render_invoice_html(pi.id)

    # 1. Print color adjust
    assert "-webkit-print-color-adjust: exact" in html
    assert "print-color-adjust: exact" in html

    # 2. Page break protection
    assert "page-break-inside: avoid" in html or "break-inside: avoid" in html

    # 3. Totals Breakdown with Discount and GST
    assert "Gross Subtotal" in html
    assert "Discount" in html
    assert "Taxable Amount" in html
    assert "CGST" in html
    assert "SGST" in html
    assert "Grand Total" in html

    # Check exact fixture numbers formatted
    assert "10,000.00" in html  # Gross
    assert "500.00" in html     # Discount
    assert "9,500.00" in html   # Taxable
    assert "855.00" in html     # CGST / SGST
    assert "11,210.00" in html  # Grand Total


def test_pi_preview_tax_configuration_resolution_and_preview_tab(db: Session):
    """
    Test that Proforma Invoice Preview handles tax configurations robustly:
    1. Intra-State with mismatched tax configuration ID auto-heals to active Intra-State config without 400 error.
    2. Inter-State with mismatched tax configuration ID auto-heals to active Inter-State config.
    3. Exempt tax regime calculates 0 tax.
    4. Full HTML preview is rendered with valid financial summary and print styles.
    """
    seed_catalogue_data(db)
    cat_service = CatalogueService(db)
    inv_service = ProformaInvoiceService(db)

    actor = MockActor()

    acc_id = f"ACC-{uuid.uuid4().hex[:6]}"
    acc = Account(
        account_id=acc_id,
        name="Tax Preview Validation Industry",
        state="Gujarat",
        gst_number="24AAACR1234M1Z5"
    )
    db.add(acc)
    db.flush()

    opp = Opportunity(
        opportunity_id=f"OPP-{uuid.uuid4().hex[:6]}",
        name="Tax Regime Testing Opportunity",
        account_id=acc.id,
        stage="Offer",
        estimated_value=Decimal("40000.00")
    )
    db.add(opp)
    db.flush()

    services_tuple = cat_service.list_services(limit=2)
    services = services_tuple[0] if isinstance(services_tuple, tuple) else services_tuple
    s1, s2 = services[0], services[1]

    quote_res = cat_service.save_current_quotation(
        actor=actor,
        opp_id=opp.id,
        payload={
            "title": "Tax Auto-Resolution Quotation",
            "taxType": "INTRA_STATE",
            "items": [
                {"itemType": "SERVICE", "serviceId": s1.id, "itemName": s1.name, "quantity": 1, "unitPrice": 25000.0, "discountAmount": 0.0},
                {"itemType": "SERVICE", "serviceId": s2.id, "itemName": s2.name, "quantity": 1, "unitPrice": 15000.0, "discountAmount": 0.0}
            ]
        }
    )

    # Fetch tax configurations from db
    intra_cfg = db.query(TaxConfiguration).filter(TaxConfiguration.tax_type == "INTRA_STATE").first()
    inter_cfg = db.query(TaxConfiguration).filter(TaxConfiguration.tax_type == "INTER_STATE").first()

    assert intra_cfg is not None
    assert inter_cfg is not None

    # Test 1: Intra-state preview with DELIBERATELY mismatched Inter-state configuration ID
    # This previously failed with 400: "Intra-state tax configuration must define active CGST and SGST rates."
    preview_req_intra = ProformaInvoicePreviewRequest(
        opportunity_id=opp.id,
        quotation_id=quote_res.id,
        tax_type="INTRA_STATE",
        tax_configuration_id=inter_cfg.id,  # Mismatched ID!
        items=[
            ProformaInvoiceItemInput(sr_no=1, service_id=s1.id, name=s1.name, quantity=1, unit="Test", rate=25000.0, discount_amount=0.0),
            ProformaInvoiceItemInput(sr_no=2, service_id=s2.id, name=s2.name, quantity=1, unit="Test", rate=15000.0, discount_amount=0.0)
        ]
    )
    preview_intra = inv_service.preview_proforma_invoice(actor, preview_req_intra)
    assert preview_intra["success"] is True
    assert preview_intra["totals"]["tax_type"] == "INTRA_STATE"
    assert preview_intra["totals"]["gross_subtotal"] == Decimal("40000.00")
    assert preview_intra["totals"]["taxable_subtotal"] == Decimal("40000.00")
    assert preview_intra["totals"]["cgst_amount"] == Decimal("3600.00")
    assert preview_intra["totals"]["sgst_amount"] == Decimal("3600.00")
    assert preview_intra["totals"]["igst_amount"] == Decimal("0.00")
    assert preview_intra["totals"]["grand_total"] == Decimal("47200.00")
    assert "Tax Preview Validation Industry" in preview_intra["html"]
    assert "47,200.00" in preview_intra["html"]

    # Test 2: Inter-state preview with DELIBERATELY mismatched Intra-state configuration ID
    preview_req_inter = ProformaInvoicePreviewRequest(
        opportunity_id=opp.id,
        quotation_id=quote_res.id,
        tax_type="INTER_STATE",
        tax_configuration_id=intra_cfg.id,  # Mismatched ID!
        items=[
            ProformaInvoiceItemInput(sr_no=1, service_id=s1.id, name=s1.name, quantity=1, unit="Test", rate=25000.0, discount_amount=0.0),
            ProformaInvoiceItemInput(sr_no=2, service_id=s2.id, name=s2.name, quantity=1, unit="Test", rate=15000.0, discount_amount=0.0)
        ]
    )
    preview_inter = inv_service.preview_proforma_invoice(actor, preview_req_inter)
    assert preview_inter["success"] is True
    assert preview_inter["totals"]["tax_type"] == "INTER_STATE"
    assert preview_inter["totals"]["taxable_subtotal"] == Decimal("40000.00")
    assert preview_inter["totals"]["igst_amount"] == Decimal("7200.00")
    assert preview_inter["totals"]["grand_total"] == Decimal("47200.00")
    assert "7,200.00" in preview_inter["html"]

    # Test 3: Exempt preview
    preview_req_exempt = ProformaInvoicePreviewRequest(
        opportunity_id=opp.id,
        quotation_id=quote_res.id,
        tax_type="EXEMPT",
        items=[
            ProformaInvoiceItemInput(sr_no=1, service_id=s1.id, name=s1.name, quantity=1, unit="Test", rate=25000.0, discount_amount=0.0)
        ]
    )
    preview_exempt = inv_service.preview_proforma_invoice(actor, preview_req_exempt)
    assert preview_exempt["success"] is True
    assert preview_exempt["totals"]["tax_type"] == "EXEMPT"
    assert preview_exempt["totals"]["taxable_subtotal"] == Decimal("25000.00")
    assert preview_exempt["totals"]["total_tax"] == Decimal("0.00")
    assert preview_exempt["totals"]["grand_total"] == Decimal("25000.00")
