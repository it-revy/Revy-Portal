import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, date, timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_phase5a_env(setup_crm_stage4_environment):
    headers_mgr = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    headers_exec = get_token_headers("stg4_sales_exec", "Pass123!", "CRM_SALES_EXECUTIVE")
    headers_admin = get_token_headers("stg4_crm_admin", "Pass123!", "CRM_ADMIN")
    return {"mgr": headers_mgr, "exec": headers_exec, "admin": headers_admin}


def _create_test_opportunity(headers, suffix="", currency="INR", estimated_value=500000.0):
    uid = uuid.uuid4().hex[:8] + suffix
    clean_uid = uid.replace("_", "-")
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Phase 5A Corp {clean_uid}",
        "industry": "Renewable Energy",
        "website": f"https://phase5a-{clean_uid}.com"
    }, headers=headers)
    assert acc_res.status_code == 201, f"Account creation failed: {acc_res.text}"
    account = acc_res.json()["account"]

    # 2. Contact
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Priya Sharma {uid}",
        "email": f"priya_{uid}@cleantech.com",
        "accountId": account["id"]
    }, headers=headers)
    assert con_res.status_code == 201
    contact = con_res.json()["contact"]

    # 3. Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Phase 5A Opportunity {uid}",
        "companyName": f"Phase 5A Corp {uid}",
        "contactEmail": f"priya_{uid}@cleantech.com",
        "businessArea": "Biogas",
        "estimatedValue": estimated_value,
        "requirementTypes": ["Consulting", "Sample Testing"]
    }, headers=headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]

    # 4. Qualify Lead -> Creates Opportunity
    qual_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json={
        "account": {"action": "reuse", "accountId": account["id"]},
        "contact": {"action": "reuse", "contactId": contact["id"]},
        "opportunityName": f"Phase 5A Opp {uid}",
        "estimatedValue": estimated_value
    }, headers=headers)
    assert qual_res.status_code == 200, f"Qualify failed: {qual_res.text}"
    opp = qual_res.json()["opportunity"]

    # Update currency if different from INR
    if currency != "INR":
        upd = client.put(f"/api/v1/crm/opportunities/{opp['id']}", json={
            "currency": currency,
            "estimatedValue": estimated_value
        }, headers=headers)
        assert upd.status_code == 200
        opp = upd.json()["opportunity"]

    return opp


# ==============================================================================
# TEST 1: 6-Stage Opportunity Funnel & Outcome Rules
# ==============================================================================
def test_six_stage_funnel_and_outcome_rules(setup_phase5a_env):
    """
    Validates:
    - 6 canonical stages: Enquiry, Qualify, Develop, Propose/Offer, Negotiate, Close
    - Won restricted strictly to Close stage
    - Lost permitted from any stage with mandatory lossReason
    """
    headers = setup_phase5a_env["mgr"]
    opp = _create_test_opportunity(headers, "funnel")
    opp_id = opp["id"]

    # 1. Verify invalid stage is rejected
    inv_stage = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "InvalidStage"
    }, headers=headers)
    assert inv_stage.status_code == 400

    # 2. Advance to Enquiry
    stg_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Enquiry",
        "remarks": "Initial scoping discussions"
    }, headers=headers)
    assert stg_res.status_code == 200
    assert stg_res.json()["opportunity"]["stage"] == "Enquiry"

    # 3. Try to mark Won at Enquiry -> must fail
    won_fail = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Enquiry",
        "status": "Won"
    }, headers=headers)
    assert won_fail.status_code == 400
    assert "Close" in won_fail.text

    # 4. Advance through Develop, Propose/Offer and Negotiate
    for target in ["Develop", "Propose/Offer", "Negotiate"]:
        step = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
            "newStage": target
        }, headers=headers)
        assert step.status_code == 200
        assert step.json()["opportunity"]["stage"] == target

    # 4b. Advancing to Close while remaining Open is rejected per Spec Section 9
    close_open_fail = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Close",
        "status": "Open"
    }, headers=headers)
    assert close_open_fail.status_code == 400

    # 5. Mark Won at Close -> must succeed
    won_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Close",
        "status": "Won",
        "remarks": "Commercial PO Received"
    }, headers=headers)
    assert won_res.status_code == 200
    assert won_res.json()["opportunity"]["status"] == "Won"
    assert won_res.json()["opportunity"]["actualCloseDate"] is not None


def test_lost_outcome_requires_loss_reason(setup_phase5a_env):
    """
    Validates:
    - Marking Lost without lossReason fails with 400
    - Supplying non-empty lossReason succeeds
    """
    headers = setup_phase5a_env["mgr"]
    opp = _create_test_opportunity(headers, "lost_rule")
    opp_id = opp["id"]

    # Missing lossReason
    fail_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Negotiate",
        "status": "Lost"
    }, headers=headers)
    assert fail_res.status_code == 400
    assert "lossReason" in fail_res.text or "reason" in fail_res.text.lower()

    # Non-empty lossReason
    ok_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Negotiate",
        "status": "Lost",
        "lossReason": "Client deferred capital expenditure project"
    }, headers=headers)
    assert ok_res.status_code == 200
    assert ok_res.json()["opportunity"]["status"] == "Lost"
    assert ok_res.json()["opportunity"]["lossReason"] == "Client deferred capital expenditure project"


# ==============================================================================
# TEST 2: Opportunity Reopening Controls & Governance
# ==============================================================================
def test_opportunity_reopening_controls(setup_phase5a_env):
    """
    Validates Section 10 specification:
    - Closed deal (Won/Lost) can only be reopened by CRM_ADMIN (Sales Manager & Executive are forbidden)
    - Reopening requires a mandatory justification reason and target stage (cannot be Close)
    - Resets status to Open, clears actualCloseDate and lossReason
    """
    headers_mgr = setup_phase5a_env["mgr"]
    headers_exec = setup_phase5a_env["exec"]
    headers_admin = setup_phase5a_env["admin"]

    opp = _create_test_opportunity(headers_mgr, "reopen")
    opp_id = opp["id"]

    # Close as Won
    client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Close",
        "status": "Won"
    }, headers=headers_mgr)

    # 1. Executive attempts reopen -> 403 Forbidden
    exec_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reason": "Client wants to add equipment",
        "reopenStage": "Negotiate"
    }, headers=headers_exec)
    assert exec_res.status_code == 403

    # 2. Sales Manager attempts reopen -> 403 Forbidden (Only CRM Admin permitted per Section 10)
    mgr_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reason": "Sales manager wants to reopen",
        "reopenStage": "Negotiate"
    }, headers=headers_mgr)
    assert mgr_res.status_code == 403

    # 3. CRM Admin attempts reopen without reason -> 400 validation error
    no_reason = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reason": "   ",
        "reopenStage": "Negotiate"
    }, headers=headers_admin)
    assert no_reason.status_code in (400, 422)

    # 4. CRM Admin attempts reopen with target stage 'Close' -> 400 validation error
    invalid_stage = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reason": "Reopening to close stage is invalid",
        "reopenStage": "Close"
    }, headers=headers_admin)
    assert invalid_stage.status_code in (400, 422)

    # 5. CRM Admin reopens with valid reason and target stage -> 200 Succeeded
    reopen_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reason": "Client requested change of scope and revision of commercial terms",
        "reopenStage": "Negotiate"
    }, headers=headers_admin)
    assert reopen_res.status_code == 200
    data = reopen_res.json()
    assert data["success"] is True
    reopened = data["opportunity"]
    assert reopened["status"] == "Open"
    assert reopened["stage"] == "Negotiate"
    assert reopened["actualCloseDate"] is None
    assert reopened["lossReason"] is None


# ==============================================================================
# TEST 3: Commercial Value Tracking & Currency Validation
# ==============================================================================
def test_currency_validation_and_value_change_reason(setup_phase5a_env):
    """
    Validates:
    - Currencies must be one of: INR, USD, EUR, GBP, AED, SGD
    - Invalid currency is rejected
    - estimatedValueChangeReason is accepted and logged
    """
    headers = setup_phase5a_env["mgr"]
    opp = _create_test_opportunity(headers, "curr")
    opp_id = opp["id"]

    # Invalid currency
    bad_curr = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "currency": "BITCOIN",
        "estimatedValue": 100000.0
    }, headers=headers)
    assert bad_curr.status_code == 400

    # Valid USD update with reason
    ok_curr = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "currency": "USD",
        "estimatedValue": 25000.0,
        "estimatedValueChangeReason": "International quotation requested in USD"
    }, headers=headers)
    assert ok_curr.status_code == 200
    assert ok_curr.json()["opportunity"]["currency"] == "USD"
    assert ok_curr.json()["opportunity"]["estimatedValue"] == 25000.0


# ==============================================================================
# TEST 4: Quotation Management & Versioning Lifecycle
# ==============================================================================
def test_quotation_full_lifecycle_and_mismatch(setup_phase5a_env):
    """
    Validates:
    - Create Quotation (generates QT-XXXXX v1 Draft)
    - Value mismatch detection against opportunity estimatedValue
    - Submit for review -> status Under Review
    - Executive cannot approve; Manager can approve
    - Material edit on approved quotation invalidates approval (status -> Draft)
    - Re-approve and mark shared with client
    - Create revision -> v2 becomes active, v1 becomes inactive
    """
    headers_mgr = setup_phase5a_env["mgr"]
    headers_exec = setup_phase5a_env["exec"]

    # Opp estimated value = 600,000 INR
    opp = _create_test_opportunity(headers_mgr, "quote_life", "INR", 600000.0)
    opp_id = opp["id"]

    # 1. Create Quotation with amount = 750,000 (mismatch exists!)
    create_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations", json={
        "title": "Biogas Scrubbing System Proposal",
        "amount": 750000.0,
        "currency": "INR",
        "termsAndConditions": "30% advance, 70% on delivery",
        "notes": "Includes initial biological catalyst supply"
    }, headers=headers_exec)
    assert create_res.status_code == 201
    q_data = create_res.json()["quotation"]
    quote_id = q_data["id"]
    quote_num = q_data["quotationNumber"]

    assert quote_num.startswith("QT-")
    assert q_data["version"] == "v1"
    assert q_data["revisionNumber"] == 1
    assert q_data["status"] == "Draft"
    assert q_data["isActive"] is True

    # Check opportunity reflects quotation count and mismatch
    opp_check = client.get(f"/api/v1/crm/opportunities/{opp_id}", headers=headers_exec).json()["opportunity"]
    assert opp_check["quotationCount"] == 1
    assert opp_check["hasQuotationMismatch"] is True
    assert opp_check["activeQuotationAmount"] == 750000.0

    # 2. Submit quotation for review
    sub_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/submit", headers=headers_exec)
    assert sub_res.status_code == 200
    assert sub_res.json()["quotation"]["status"] == "Under Review"

    # 3. Try to mark shared before approval -> must fail
    early_share = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/share", json={
        "sentMethod": "Email",
        "sentTo": "client@example.com"
    }, headers=headers_exec)
    assert early_share.status_code == 400

    # 4. Executive tries to approve -> Forbidden
    exec_appr = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/approve", json={
        "action": "approve"
    }, headers=headers_exec)
    assert exec_appr.status_code == 403

    # 4b. CRM_ADMIN tries to approve without Sales Manager role -> Forbidden
    admin_appr = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/approve", json={
        "action": "approve"
    }, headers=setup_phase5a_env["admin"])
    assert admin_appr.status_code == 403

    # 4c. Rejection requires non-empty reason
    rej_no_reason = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/approve", json={
        "action": "reject",
        "reason": "   "
    }, headers=headers_mgr)
    assert rej_no_reason.status_code == 400

    # 5. Manager approves -> Succeeded
    mgr_appr = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/approve", json={
        "action": "approve"
    }, headers=headers_mgr)
    assert mgr_appr.status_code == 200
    approved_q = mgr_appr.json()["quotation"]
    assert approved_q["status"] == "Approved"
    assert approved_q["approvedAt"] is not None

    # 6. Material edit on approved quotation -> reverts status to Draft!
    mat_edit = client.put(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}", json={
        "amount": 720000.0,
        "currency": "INR"
    }, headers=headers_exec)
    assert mat_edit.status_code == 200
    reverted_q = mat_edit.json()["quotation"]
    assert reverted_q["status"] == "Draft"
    assert reverted_q["approvedAt"] is None

    # 7. Submit and Re-approve
    client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/submit", headers=headers_exec)
    client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/approve", json={"action": "approve"}, headers=headers_mgr)

    # 8. Mark quotation shared with client
    share_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/share", json={
        "sentMethod": "Email",
        "sentTo": "procurement@biogascorp.in",
        "sendingEvidence": "Sent via Outlook from sales@revy.com with quotation PDF"
    }, headers=headers_exec)
    assert share_res.status_code == 200
    shared_q = share_res.json()["quotation"]
    assert shared_q["status"] == "Shared"
    assert shared_q["sentMethod"] == "Email"
    assert shared_q["sentTo"] == "procurement@biogascorp.in"

    # 9. Create revision -> generates v2
    rev_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}/revise", json={
        "title": "Biogas Scrubbing System Proposal - Rev 2",
        "amount": 600000.0,
        "currency": "INR",
        "notes": "Discount applied to match client target budget"
    }, headers=headers_exec)
    assert rev_res.status_code == 201
    v2_q = rev_res.json()["quotation"]
    assert v2_q["quotationNumber"] == quote_num
    assert v2_q["version"] == "v2"
    assert v2_q["revisionNumber"] == 2
    assert v2_q["isActive"] is True
    assert v2_q["status"] == "Draft"

    # 10. Verify v1 is now isActive = False
    v1_check = client.get(f"/api/v1/crm/opportunities/{opp_id}/quotations/{quote_id}", headers=headers_exec).json()["quotation"]
    assert v1_check["isActive"] is False

    # 11. Now active quotation matches estimatedValue (600,000 INR) -> mismatch resolved!
    opp_check2 = client.get(f"/api/v1/crm/opportunities/{opp_id}", headers=headers_exec).json()["opportunity"]
    assert opp_check2["quotationCount"] == 2
    assert opp_check2["hasQuotationMismatch"] is False


# ==============================================================================
# TEST 5: Currency-Grouped Revenue Metrics Endpoint
# ==============================================================================
def test_revenue_metrics_currency_grouping(setup_phase5a_env):
    """
    Validates GET /crm/analytics/revenue-metrics returns:
    - byCurrency breakdown (openPipelineValue, wonValue, lostValue)
    - totalOpenOpportunities, totalWonOpportunities, totalLostOpportunities
    - Stage breakdowns
    """
    headers = setup_phase5a_env["mgr"]
    # Create an opportunity in USD and an opportunity in EUR
    _ = _create_test_opportunity(headers, "usd_rev", "USD", 15000.0)
    _ = _create_test_opportunity(headers, "eur_rev", "EUR", 20000.0)

    res = client.get("/api/v1/crm/analytics/revenue-metrics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "openPipelineValueByCurrency" in data
    assert "USD" in data["openPipelineValueByCurrency"]
    assert "EUR" in data["openPipelineValueByCurrency"]
    assert data["openPipelineValueByCurrency"]["USD"] >= 15000.0
    assert data["openPipelineValueByCurrency"]["EUR"] >= 20000.0
    assert "byStage" in data
    assert len(data["byStage"]) == 6


# ==============================================================================
# TEST 6: Composite Unique Constraint & Concurrency Safety
# ==============================================================================
def test_quotation_composite_unique_constraint(setup_phase5a_env):
    """
    Validates:
    - Attempting to insert a duplicate (quotation_number, revision_number)
      violates composite unique constraint uq_crm_opportunity_quotations_num_rev
      raising IntegrityError.
    """
    headers = setup_phase5a_env["mgr"]
    opp = _create_test_opportunity(headers, "uniq_test")
    opp_id = opp["id"]

    # 1. Create quote
    q_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/quotations", json={
        "title": "Uniqueness Test Quotation",
        "amount": 250000.0,
        "currency": "INR"
    }, headers=headers)
    assert q_res.status_code == 201
    q = q_res.json()["quotation"]

    # 2. Direct database insert with identical (quotation_number, revision_number)
    from sqlalchemy.exc import IntegrityError
    from app.crm.model import OpportunityQuotation
    db = SessionLocal()
    try:
        dup = OpportunityQuotation(
            quotation_number=q["quotationNumber"],
            opportunity_id=opp_id,
            revision_number=q["revisionNumber"],
            version=q["version"],
            is_active=False,
            title="Duplicate Quote Attempt",
            status="Draft",
            amount=100000.0,
            currency="INR"
        )
        db.add(dup)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()
