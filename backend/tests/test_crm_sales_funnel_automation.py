import os
import uuid
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta

os.environ["TESTING"] = "1"

import app.models
from app.core.database import SessionLocal
from app.core.dependencies import CurrentUser
from app.core.exceptions import ValidationError
from app.users.model import User
from app.crm.model import (
    Lead,
    Account,
    Contact,
    Opportunity,
    OpportunityQuotation,
    OpportunityStageHistory
)
from app.crm.catalogue_model import Service, ServiceCategory, TaxConfiguration, TaxRate, OpportunityQuotationItem
from app.crm.invoice_model import CrmCompanySettings, ProformaInvoice, ProformaInvoiceRevision, ProformaInvoiceItem
from app.crm.service import CrmService, record_opportunity_stage_transition
from app.crm.catalogue_service import CatalogueService
from app.crm.invoice_service import ProformaInvoiceService


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_actor(db_session):
    user = db_session.query(User).filter(User.username == "admin_funnel_test").first()
    if not user:
        user = User(
            username="admin_funnel_test",
            name="Funnel Test Admin",
            email="admin_funnel_test@revyenvironmental.com",
            password_hash="test_hash_pw",
            status="Active"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    return CurrentUser(
        user=user,
        active_role="CRM_ADMIN",
        roles=["CRM_ADMIN", "IT_ADMIN", "DIRECTOR"],
        permissions=["*"],
        all_permissions=["*"],
        permissions_by_role={"CRM_ADMIN": ["*"]},
        modules=["CRM", "USERS", "BMS"],
        module_roles={"CRM": ["CRM_ADMIN"]},
        is_global_admin=True
    )


@pytest.fixture
def test_context(db_session, test_actor):
    ts = int(datetime.now().timestamp() * 1000)
    # Ensure Account & Contact
    account = Account(
        account_id=f"ACC-AUTO-{ts}",
        name=f"Automation Test Account {ts}",
        address="Test Road, Vadodara",
        is_active=True
    )
    db_session.add(account)
    db_session.flush()

    contact = Contact(
        contact_id=f"CON-AUTO-{ts}",
        account_id=account.id,
        name="Auto Test Contact",
        mobile_number="+91-9999900000",
        is_primary=True,
        is_active=True
    )
    db_session.add(contact)
    db_session.flush()

    # Ensure Catalogue service
    svc = db_session.query(Service).filter(Service.is_active == True).first()
    if not svc:
        cat = db_session.query(ServiceCategory).first()
        if not cat:
            cat = ServiceCategory(name="Test Category", code="TC_CAT", prefix="TC", is_active=True)
            db_session.add(cat)
            db_session.flush()
        svc = Service(name="Test Service", service_code="TC_SRV", category_id=cat.id, standard_price=Decimal("1000.00"), is_active=True)
        db_session.add(svc)
        db_session.flush()

    # Ensure Tax config
    tax_cfg = db_session.query(TaxConfiguration).filter(TaxConfiguration.is_active == True).first()
    if not tax_cfg:
        tax_cfg = TaxConfiguration(name="TEST_GST_18", tax_type="INTRA_STATE", is_active=True)
        db_session.add(tax_cfg)
        db_session.flush()

    # Ensure Company Settings
    cs = db_session.query(CrmCompanySettings).first()
    if not cs:
        cs = CrmCompanySettings(
            legal_name="REVY Environmental Solutions Private Limited",
            trade_name="REVY Solutions",
            gstin="24AABCR1234F1Z5",
            pan="AABCR1234F",
            address_line1="B-101, Test Tech Park",
            city="Vadodara",
            state="Gujarat",
            pincode="390001",
            state_code="24",
            bank_name="Test Bank Ltd",
            bank_account_number="987654321012",
            bank_ifsc="TEST0001234"
        )
        db_session.add(cs)
        db_session.flush()

    db_session.commit()

    account_id_val = str(account.id)
    contact_id_val = str(contact.id)

    created_opp_ids = []
    created_lead_ids = []

    yield {
        "account": account,
        "contact": contact,
        "service": svc,
        "tax_config": tax_cfg,
        "created_opp_ids": created_opp_ids,
        "created_lead_ids": created_lead_ids
    }

    # Cleanup test-created records cleanly
    try:
        db_session.rollback()
        for opp_id in created_opp_ids:
            db_session.query(OpportunityStageHistory).filter(OpportunityStageHistory.opportunity_id == opp_id).delete(synchronize_session=False)
            pis = db_session.query(ProformaInvoice).filter(ProformaInvoice.opportunity_id == opp_id).all()
            for pi in pis:
                revs = db_session.query(ProformaInvoiceRevision).filter(ProformaInvoiceRevision.proforma_invoice_id == pi.id).all()
                for r in revs:
                    db_session.query(ProformaInvoiceItem).filter(ProformaInvoiceItem.revision_id == r.id).delete(synchronize_session=False)
                    db_session.delete(r)
                db_session.delete(pi)
            quotes = db_session.query(OpportunityQuotation).filter(OpportunityQuotation.opportunity_id == opp_id).all()
            for q in quotes:
                db_session.query(OpportunityQuotationItem).filter(OpportunityQuotationItem.quotation_id == q.id).delete(synchronize_session=False)
                db_session.delete(q)
            opp = db_session.query(Opportunity).filter(Opportunity.id == opp_id).first()
            if opp:
                db_session.delete(opp)

        for l_id in created_lead_ids:
            db_session.query(Lead).filter(Lead.id == l_id).delete(synchronize_session=False)

        db_session.query(Contact).filter(Contact.id == contact_id_val).delete(synchronize_session=False)
        db_session.query(Account).filter(Account.id == account_id_val).delete(synchronize_session=False)
        db_session.commit()
    except Exception:
        db_session.rollback()


# ============================================================================
# 1. FUNNEL REPORTING: Validates 50 Leads, 30 Qualified, 15 Quotes, 5 PIs
# ============================================================================
def test_seeded_funnel_metrics_and_ratios(db_session, test_actor):
    crm_service = CrmService(db_session)
    metrics = crm_service.get_dashboard_metrics(test_actor)

    # Cumulative funnel milestones
    assert metrics["totalLeads"] == 50, f"Expected 50 Total Leads, got {metrics['totalLeads']}"
    assert metrics["qualifiedLeads"] == 30, f"Expected 30 Qualified Leads, got {metrics['qualifiedLeads']}"
    assert metrics["quotationsCreated"] == 15, f"Expected 15 Quotations Created, got {metrics['quotationsCreated']}"
    assert metrics["pisCreated"] == 5, f"Expected 5 PIs Created, got {metrics['pisCreated']}"

    # Conversion rates
    assert metrics["leadToQualificationRate"] == 60.0
    assert metrics["qualificationToQuotationRate"] == 50.0
    assert metrics["quotationToPiRate"] == 33.3
    assert metrics["overallLeadToPiRate"] == 10.0

    # 7-stage distribution
    stages = metrics["opportunityCountByStage"]
    assert "PI Issued" in stages, "Stages distribution must include 'PI Issued'"
    assert stages["Enquiry"] == 13
    assert stages["Offer"] == 5
    assert stages["Negotiation"] == 4
    assert stages["PI Issued"] == 2
    assert stages["Supply"] == 2
    assert stages["Payment"] == 1
    assert stages["Dormant"] == 3


# ============================================================================
# 2. LEAD CREATION SAFEGUARD: No Opportunity premature creation
# ============================================================================
def test_lead_creation_no_opportunity_prematurely(db_session, test_actor, test_context):
    lead = Lead(
        lead_id="LEAD-TEST-PREMATURE",
        lead_name="Pristine Water Corp Automated",
        company_name="Pristine Water Corp",
        first_name="Ramesh",
        last_name="Sharma",
        mobile_phone="+91-9876500001",
        contact_email="ramesh@pristinewater.test",
        lead_source="Inbound Call",
        business_area="Wastewater Treatment (WWT)",
        lifecycle_status="New",
        remarks="Test lead for stage automation validation"
    )
    db_session.add(lead)
    db_session.commit()
    test_context["created_lead_ids"].append(lead.id)

    # Verify no opportunity created
    opp_count = db_session.query(Opportunity).filter(Opportunity.originating_lead_id == lead.id).count()
    assert opp_count == 0, "Lead creation must never create an opportunity prematurely"


# ============================================================================
# 3. LEAD QUALIFICATION: Automatically enters Enquiry stage with history
# ============================================================================
def test_lead_qualification_creates_enquiry_opportunity(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    lead = Lead(
        lead_id="LEAD-TEST-QUAL",
        lead_name="EcoGreen Distilleries Automation",
        company_name="EcoGreen Distilleries Ltd",
        first_name="Arun",
        last_name="Patel",
        mobile_phone="+91-9876500002",
        contact_email="arun@ecogreen.test",
        lead_source="Website Form",
        business_area="Biogas",
        lifecycle_status="New",
        remarks="Qualify lead test"
    )
    db_session.add(lead)
    db_session.commit()
    test_context["created_lead_ids"].append(lead.id)

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Opportunity - EcoGreen Distilleries Ltd",
        account_id=account.id,
        contact_id=contact.id,
        originating_lead_id=lead.id,
        status="Open",
        stage="Enquiry",
        business_area="Biogas",
        currency="INR",
        estimated_value=Decimal("450000.00"),
        description="Qualified lead opportunity"
    )
    db_session.add(opp)
    db_session.flush()
    test_context["created_opp_ids"].append(opp.id)

    record_opportunity_stage_transition(
        db=db_session,
        opp=opp,
        new_stage="Enquiry",
        triggering_event="LEAD_QUALIFIED",
        actor=test_actor,
        remarks=f"Lead {lead.lead_id} qualified",
        commit=True
    )

    lead.lifecycle_status = "Qualified"
    db_session.commit()

    # Assertions
    refreshed_opp = db_session.query(Opportunity).filter(Opportunity.id == opp.id).first()
    assert refreshed_opp.stage == "Enquiry"

    history = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id
    ).all()
    assert len(history) == 1
    assert history[0].new_stage == "Enquiry"
    assert history[0].triggering_event == "LEAD_QUALIFIED"


# ============================================================================
# 4. FIRST QUOTATION: Automatically moves opportunity to Offer stage
# ============================================================================
def test_first_quotation_moves_opportunity_to_offer(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]
    svc = test_context["service"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Quotation Stage Test Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="Enquiry",
        currency="INR",
        estimated_value=Decimal("200000.00")
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    quotation = OpportunityQuotation(
        quotation_number="QUOT-TEST-OFFER",
        opportunity_id=opp.id,
        revision_number=1,
        version="R1",
        is_active=True,
        title="Quotation R1 for Stage Test",
        status="Draft",
        amount=Decimal("11800.00"),
        subtotal=Decimal("10000.00"),
        total_tax=Decimal("1800.00"),
        currency="INR",
        quotation_date=date.today(),
        valid_until_date=date.today() + timedelta(days=30)
    )
    db_session.add(quotation)
    db_session.flush()

    item = OpportunityQuotationItem(
        quotation_id=quotation.id,
        item_type="SERVICE",
        service_id=svc.id,
        item_code=svc.service_code,
        item_name=svc.name,
        billing_unit="Per Test",
        quantity=2,
        unit_price=Decimal("5000.00"),
        standard_price=Decimal("5000.00"),
        taxable_amount=Decimal("10000.00"),
        total_tax=Decimal("1800.00"),
        final_total=Decimal("11800.00"),
        currency="INR"
    )
    db_session.add(item)

    record_opportunity_stage_transition(
        db=db_session,
        opp=opp,
        new_stage="Offer",
        triggering_event="FIRST_QUOTATION_CREATED",
        actor=test_actor,
        remarks=f"First quotation created: {quotation.quotation_number}",
        commit=True
    )

    db_session.refresh(opp)
    assert opp.stage == "Offer", "First quotation must transition opportunity to Offer stage"

    hist = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id,
        OpportunityStageHistory.new_stage == "Offer"
    ).first()
    assert hist is not None
    assert hist.previous_stage == "Enquiry"
    assert hist.triggering_event == "FIRST_QUOTATION_CREATED"


# ============================================================================
# 5. COMMERCIAL QUOTATION REVISION: Automatically moves to Negotiation stage
# ============================================================================
def test_commercial_quotation_revision_moves_to_negotiation(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Negotiation Revision Test Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="Offer",
        currency="INR",
        estimated_value=Decimal("200000.00")
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    # Commercial revision with price negotiation
    record_opportunity_stage_transition(
        db=db_session,
        opp=opp,
        new_stage="Negotiation",
        triggering_event="COMMERCIAL_QUOTATION_REVISED",
        actor=test_actor,
        remarks="Quotation revised with 10% discount",
        commit=True
    )

    db_session.refresh(opp)
    assert opp.stage == "Negotiation", "Material commercial revision must move opportunity to Negotiation"

    hist = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id,
        OpportunityStageHistory.new_stage == "Negotiation"
    ).first()
    assert hist is not None
    assert hist.previous_stage == "Offer"
    assert hist.triggering_event == "COMMERCIAL_QUOTATION_REVISED"


# ============================================================================
# 6. SAFEGUARD: Non-commercial edits do not trigger Negotiation or downgrade
# ============================================================================
def test_non_commercial_quotation_edit_does_not_trigger_negotiation(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Non Commercial Edit Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="Offer",
        currency="INR"
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    quotation = OpportunityQuotation(
        quotation_number="QUOT-TEST-NONCOMM",
        opportunity_id=opp.id,
        revision_number=1,
        version="R1",
        is_active=True,
        title="Original Title",
        status="Draft",
        amount=Decimal("10000.00"),
        subtotal=Decimal("10000.00"),
        currency="INR",
        quotation_date=date.today(),
        terms_and_conditions="Payment within 30 days"
    )
    db_session.add(quotation)
    db_session.commit()

    # Non-commercial edit: update terms and title only
    quotation.terms_and_conditions = "Payment within 45 days. Net terms apply."
    quotation.title = "Updated Title with Better Description"
    db_session.commit()

    # Verify stage remained 'Offer' without any transition to Negotiation
    db_session.refresh(opp)
    assert opp.stage == "Offer"
    hist_count = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id,
        OpportunityStageHistory.triggering_event == "COMMERCIAL_QUOTATION_REVISED"
    ).count()
    assert hist_count == 0, "Non-commercial quotation edits must not trigger stage change"


# ============================================================================
# 7. PROFORMA INVOICE CREATION: Automatically moves opportunity to PI Issued
# ============================================================================
def test_proforma_invoice_generation_moves_to_pi_issued(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="PI Issued Test Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="Negotiation",
        currency="INR"
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    quotation = OpportunityQuotation(
        quotation_number=f"QUOT-T-{uuid.uuid4().hex[:8]}",
        opportunity_id=opp.id,
        revision_number=1,
        version="R1",
        is_active=True,
        title="Quotation for PI",
        status="Approved",
        amount=Decimal("23600.00"),
        subtotal=Decimal("20000.00"),
        total_tax=Decimal("3600.00"),
        currency="INR",
        quotation_date=date.today()
    )
    db_session.add(quotation)
    db_session.commit()

    from app.crm.invoice_schema import ProformaInvoiceCreate, ProformaInvoiceItemInput
    inv_service = ProformaInvoiceService(db_session)
    payload = ProformaInvoiceCreate(
        opportunityId=opp.id,
        quotationId=quotation.id,
        taxType="INTRA_STATE",
        items=[
            ProformaInvoiceItemInput(
                srNo=1,
                itemType="SERVICE",
                itemCode="PHY-001",
                name="Colour Test",
                quantity=Decimal("2"),
                rate=Decimal("10000.00")
            )
        ]
    )
    pi = inv_service.create_proforma_invoice(actor=test_actor, payload=payload)

    db_session.refresh(opp)
    assert opp.stage == "PI Issued", "PI creation must automatically transition opportunity to PI Issued"

    hist = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id,
        OpportunityStageHistory.new_stage == "PI Issued"
    ).first()
    assert hist is not None
    assert hist.previous_stage == "Negotiation"
    assert hist.triggering_event == "PI_GENERATED"


# ============================================================================
# 8. SAFEGUARD: PI Revision does not reset or downgrade stage
# ============================================================================
def test_proforma_invoice_revision_does_not_downgrade_stage(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="PI Revision Test Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="Supply",  # Already advanced to Supply
        currency="INR"
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    quotation = OpportunityQuotation(
        quotation_number=f"QUOT-T-{uuid.uuid4().hex[:8]}",
        opportunity_id=opp.id,
        revision_number=1,
        version="R1",
        is_active=True,
        title="Quotation for PI Revision",
        status="Approved",
        amount=Decimal("23600.00"),
        subtotal=Decimal("20000.00"),
        total_tax=Decimal("3600.00"),
        currency="INR",
        quotation_date=date.today()
    )
    db_session.add(quotation)
    db_session.commit()

    from app.crm.invoice_schema import ProformaInvoiceCreate, ProformaInvoiceRevisionCreate, ProformaInvoiceItemInput
    inv_service = ProformaInvoiceService(db_session)
    create_payload = ProformaInvoiceCreate(
        opportunityId=opp.id,
        quotationId=quotation.id,
        taxType="INTRA_STATE",
        items=[
            ProformaInvoiceItemInput(
                srNo=1,
                itemType="SERVICE",
                itemCode="PHY-001",
                name="Colour Test",
                quantity=Decimal("2"),
                rate=Decimal("10000.00")
            )
        ]
    )
    pi = inv_service.create_proforma_invoice(actor=test_actor, payload=create_payload)

    # Re-set stage to Supply to test downgrade protection
    opp.stage = "Supply"
    db_session.commit()

    rev_payload = ProformaInvoiceRevisionCreate(
        notes="Customer requested revision",
        taxType="INTRA_STATE",
        items=[
            ProformaInvoiceItemInput(
                srNo=1,
                itemType="SERVICE",
                itemCode="PHY-001",
                name="Colour Test",
                quantity=Decimal("2"),
                rate=Decimal("10000.00")
            )
        ]
    )
    rev = inv_service.create_invoice_revision(actor=test_actor, pi_id=pi.id, payload=rev_payload)

    db_session.refresh(opp)
    assert opp.stage == "Supply", "PI revision must never downgrade stage from Supply to PI Issued"


# ============================================================================
# 9. ORDER CONFIRMATION & SUPPLY EXECUTION: Moves to Supply stage
# ============================================================================
def test_confirm_order_and_start_supply(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Order Confirmation Test Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="PI Issued",
        currency="INR"
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    crm_service = CrmService(db_session)
    crm_service.confirm_order_and_start_supply(
        actor=test_actor,
        opp_id=opp.id,
        notes="Client sent Purchase Order PO-9876. Pilot dispatched."
    )

    db_session.refresh(opp)
    assert opp.stage == "Supply"

    hist = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id,
        OpportunityStageHistory.new_stage == "Supply"
    ).first()
    assert hist is not None
    assert hist.previous_stage == "PI Issued"
    assert hist.triggering_event == "ORDER_CONFIRMED_SUPPLY_STARTED"


# ============================================================================
# 10. PAYMENT TRACKING: Moves to Payment stage
# ============================================================================
def test_start_payment_tracking(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Payment Tracking Test Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="Supply",
        currency="INR"
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    crm_service = CrmService(db_session)
    crm_service.start_payment_tracking(
        actor=test_actor,
        opp_id=opp.id,
        notes="Partial advance 50% received; tracking milestone 2 balance"
    )

    db_session.refresh(opp)
    assert opp.stage == "Payment"

    hist = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id,
        OpportunityStageHistory.new_stage == "Payment"
    ).first()
    assert hist is not None
    assert hist.previous_stage == "Supply"
    assert hist.triggering_event == "PAYMENT_TRACKING_STARTED"


# ============================================================================
# 11. DORMANT & REACTIVATION: Explicit business events
# ============================================================================
def test_mark_dormant_and_reactivate(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Dormant Inactivity Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="Negotiation",
        currency="INR"
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    crm_service = CrmService(db_session)
    crm_service.mark_opportunity_dormant(
        actor=test_actor,
        opp_id=opp.id,
        dormancy_reason="Client funding delayed until next fiscal quarter"
    )

    db_session.refresh(opp)
    assert opp.stage == "Dormant"

    hist_dormant = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id,
        OpportunityStageHistory.new_stage == "Dormant"
    ).first()
    assert hist_dormant is not None
    assert hist_dormant.previous_stage == "Negotiation"
    assert hist_dormant.triggering_event == "OPPORTUNITY_MARKED_DORMANT"

    # Reactivate
    crm_service.reactivate_opportunity(actor=test_actor, opp_id=opp.id)
    db_session.refresh(opp)
    assert opp.stage == "Enquiry"

    hist_reactivate = db_session.query(OpportunityStageHistory).filter(
        OpportunityStageHistory.opportunity_id == opp.id,
        OpportunityStageHistory.triggering_event == "OPPORTUNITY_REACTIVATED"
    ).first()
    assert hist_reactivate is not None
    assert hist_reactivate.new_stage == "Enquiry"


# ============================================================================
# 12. MANUAL STAGE EDITS BLOCKED: Backend enforces single source of truth
# ============================================================================
def test_manual_stage_updates_are_blocked(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Manual Block Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="Enquiry",
        currency="INR"
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    crm_service = CrmService(db_session)

    # 1. Attempt manual transition via transition_opportunity_stage
    from app.crm.schema import OpportunityStageTransitionRequest, OpportunityUpdateRequest
    req = OpportunityStageTransitionRequest(newStage="Offer", status="Open", remarks="Trying to skip")
    with pytest.raises(ValidationError) as exc1:
        crm_service.transition_opportunity_stage(actor=test_actor, opp_id=opp.id, payload=req)
    assert "Direct manual stage transitions are disabled" in str(exc1.value)

    # 2. Attempt manual update via update_opportunity
    update_req = OpportunityUpdateRequest(stage="Supply")
    with pytest.raises(ValidationError) as exc2:
        crm_service.update_opportunity(actor=test_actor, opp_id=opp.id, payload=update_req)
    assert "Opportunity stages are fully automated" in str(exc2.value)


# ============================================================================
# 13. FINANCIAL SNAPSHOT INTEGRITY: Quotation & PI numbers remain exact
# ============================================================================
def test_historical_quotation_and_pi_snapshots_remain_intact(db_session, test_actor, test_context):
    account = test_context["account"]
    contact = test_context["contact"]

    opp = Opportunity(
        opportunity_id=f"OPP-T-{uuid.uuid4().hex[:8]}",
        name="Financial Snapshot Opp",
        account_id=account.id,
        contact_id=contact.id,
        status="Open",
        stage="PI Issued",
        currency="INR"
    )
    db_session.add(opp)
    db_session.commit()
    test_context["created_opp_ids"].append(opp.id)

    expected_subtotal = Decimal("150000.00")
    expected_tax = Decimal("27000.00")
    expected_grand_total = Decimal("177000.00")

    quotation = OpportunityQuotation(
        quotation_number="QUOT-TEST-SNAPSHOT",
        opportunity_id=opp.id,
        revision_number=1,
        version="R1",
        is_active=True,
        title="Quotation Snapshot Test",
        status="Approved",
        amount=expected_grand_total,
        subtotal=expected_subtotal,
        total_tax=expected_tax,
        currency="INR",
        quotation_date=date.today()
    )
    db_session.add(quotation)
    db_session.commit()

    # Progress through Supply and Payment
    crm_service = CrmService(db_session)
    crm_service.confirm_order_and_start_supply(actor=test_actor, opp_id=opp.id, notes="Supplied equipment")
    crm_service.start_payment_tracking(actor=test_actor, opp_id=opp.id, notes="Collected invoice payment")

    # Verify financial snapshot on quotation has not mutated
    db_session.refresh(quotation)
    assert quotation.subtotal == expected_subtotal
    assert quotation.total_tax == expected_tax
    assert quotation.amount == expected_grand_total
