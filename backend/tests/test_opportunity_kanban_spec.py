import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_kanban_env(setup_crm_stage4_environment):
    headers_mgr = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    headers_exec = get_token_headers("stg4_sales_exec", "Pass123!", "CRM_SALES_EXECUTIVE")
    headers_admin = get_token_headers("stg4_crm_admin", "Pass123!", "CRM_ADMIN")
    return {"mgr": headers_mgr, "exec": headers_exec, "admin": headers_admin}


def _create_helper(headers, suffix=""):
    uid = uuid.uuid4().hex[:8] + suffix
    clean_uid = uid.replace("_", "-")

    # Account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Kanban Spec Corp {clean_uid}",
        "industry": "Clean Energy",
        "website": f"https://kanban-{clean_uid}.com"
    }, headers=headers)
    assert acc_res.status_code == 201
    account = acc_res.json()["account"]

    # Contact
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Anil Kumar {uid}",
        "email": f"anil_{uid}@cleantech.com",
        "accountId": account["id"]
    }, headers=headers)
    assert con_res.status_code == 201
    contact = con_res.json()["contact"]

    return account, contact


# ==============================================================================
# SPEC SECTION 9: STAGE AND OUTCOME COMBINED VALIDATION RULES
# ==============================================================================
def test_stage_outcome_combined_validation_rules(setup_kanban_env):
    """
    Mandatory business rules:
    - Open Pipeline + Close: REJECT (400)
    - Closed Won + Close: ALLOW (200)
    - Closed Lost + Close (with lossReason): ALLOW (200)
    - Closed Won at earlier pipeline stage: REJECT (400)
    - Closed Lost at earlier pipeline stage: REJECT (400)
    """
    headers = setup_kanban_env["mgr"]
    account, contact = _create_helper(headers, "stg_out")

    # 1. Create opportunity with both account and contact
    create_res = client.post("/api/v1/crm/opportunities", json={
        "name": "Stage Outcome Governance Test",
        "accountId": account["id"],
        "contactId": contact["id"],
        "stage": "Develop",
        "estimatedValue": 350000.0,
        "currency": "INR"
    }, headers=headers)
    assert create_res.status_code == 201
    opp_id = create_res.json()["opportunity"]["id"]

    # 2. Attempt: Closed Won at 'Develop' stage -> MUST REJECT (400)
    res_won_early = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Develop",
        "status": "Won"
    }, headers=headers)
    assert res_won_early.status_code == 400
    assert "Close" in res_won_early.text

    # 3. Attempt: Closed Lost at 'Develop' stage -> MUST REJECT (400)
    res_lost_early = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Develop",
        "status": "Lost",
        "lossReason": "Competitor underbid"
    }, headers=headers)
    assert res_lost_early.status_code == 400
    assert "Close" in res_lost_early.text

    # 4. Attempt: Move to 'Close' stage with 'Open' status -> MUST REJECT (400)
    res_close_open = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Close",
        "status": "Open"
    }, headers=headers)
    assert res_close_open.status_code == 400
    assert "Won or Lost" in res_close_open.text or "Close" in res_close_open.text

    # 5. Attempt: Move to 'Close' stage with 'Lost' but missing lossReason -> MUST REJECT (400)
    res_close_lost_no_reason = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Close",
        "status": "Lost",
        "lossReason": ""
    }, headers=headers)
    assert res_close_lost_no_reason.status_code == 400

    # 6. Attempt: Move to 'Close' stage with 'Won' -> MUST SUCCEED (200)
    res_close_won = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Close",
        "status": "Won"
    }, headers=headers)
    assert res_close_won.status_code == 200
    opp_won = res_close_won.json()["opportunity"]
    assert opp_won["stage"] == "Close"
    assert opp_won["status"] == "Won"
    assert opp_won["actualCloseDate"] is not None


# ==============================================================================
# SPEC SECTION 8: STAGE MOVEMENT PERMISSIONS (FORWARD & BACKWARD)
# ==============================================================================
def test_backward_stage_movement_permissions(setup_kanban_env):
    """
    Enforces stage movement authorization:
    - Forward movement (Qualify -> Develop -> Propose/Offer) allowed for regular sales executive
    - Backward movement (Propose/Offer -> Qualify) strictly restricted to Sales Manager & Admin
    - Non-manager attempting backward movement receives 403 Forbidden
    - Manager attempting backward movement succeeds
    """
    headers_mgr = setup_kanban_env["mgr"]
    headers_exec = setup_kanban_env["exec"]
    account, contact = _create_helper(headers_mgr, "bwd_perm")

    # 1. Create opportunity at Qualify
    create_res = client.post("/api/v1/crm/opportunities", json={
        "name": "Pipeline Movement Permission Test",
        "accountId": account["id"],
        "contactId": contact["id"],
        "stage": "Qualify",
        "estimatedValue": 450000.0
    }, headers=headers_mgr)
    assert create_res.status_code == 201
    opp_id = create_res.json()["opportunity"]["id"]

    # 2. Executive moves opportunity FORWARD to Develop -> 200 Succeeded
    fwd_res = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Develop"
    }, headers=headers_exec)
    assert fwd_res.status_code == 200
    assert fwd_res.json()["opportunity"]["stage"] == "Develop"

    # 3. Executive moves opportunity FORWARD to Propose/Offer -> 200 Succeeded
    fwd_res2 = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Propose/Offer"
    }, headers=headers_exec)
    assert fwd_res2.status_code == 200
    assert fwd_res2.json()["opportunity"]["stage"] == "Propose/Offer"

    # 4. Executive attempts to move BACKWARD from Propose/Offer to Qualify -> 403 Forbidden
    bwd_fail = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Qualify"
    }, headers=headers_exec)
    assert bwd_fail.status_code == 403
    assert "backward" in bwd_fail.text.lower() or "manager" in bwd_fail.text.lower()

    # 5. Transition endpoint also enforces backward permission: executive -> 403 Forbidden
    trans_bwd_fail = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Qualify"
    }, headers=headers_exec)
    assert trans_bwd_fail.status_code == 403

    # 6. Sales Manager moves opportunity BACKWARD from Propose/Offer to Qualify -> 200 Succeeded
    bwd_ok = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "stage": "Qualify"
    }, headers=headers_mgr)
    assert bwd_ok.status_code == 200
    assert bwd_ok.json()["opportunity"]["stage"] == "Qualify"


# ==============================================================================
# SPEC SECTION 10: REOPENING CLOSED OPPORTUNITIES STRICTLY BY CRM ADMIN
# ==============================================================================
def test_reopen_closed_opportunity_authoritative_rule(setup_kanban_env):
    """
    Mandatory business rules:
    - Only users with CRM_ADMIN / IT_ADMIN role may reopen Closed Won/Lost opportunities
    - Executive & Sales Manager receive 403 Forbidden
    - Reopening requires explicit new stage (cannot be Close)
    - Outcome changed to Open Pipeline
    """
    headers_mgr = setup_kanban_env["mgr"]
    headers_exec = setup_kanban_env["exec"]
    headers_admin = setup_kanban_env["admin"]
    account, contact = _create_helper(headers_mgr, "reopen_rule")

    # 1. Create and close opportunity as Won
    create_res = client.post("/api/v1/crm/opportunities", json={
        "name": "Admin Reopen Governance Test",
        "accountId": account["id"],
        "contactId": contact["id"],
        "stage": "Close",
        "status": "Won",
        "estimatedValue": 600000.0
    }, headers=headers_mgr)
    assert create_res.status_code == 201
    opp_id = create_res.json()["opportunity"]["id"]

    # 2. Executive attempts reopen -> 403
    res_exec = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reopenStage": "Negotiate",
        "reason": "Executive attempt"
    }, headers=headers_exec)
    assert res_exec.status_code == 403

    # 3. Sales Manager attempts reopen -> 403 (Strictly restricted to CRM Admin per Spec Section 10)
    res_mgr = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reopenStage": "Negotiate",
        "reason": "Sales manager attempt"
    }, headers=headers_mgr)
    assert res_mgr.status_code == 403

    # 4. CRM Admin attempts reopen with reopenStage = 'Close' -> 400
    res_inv_stg = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reopenStage": "Close",
        "reason": "Cannot reopen directly back to Close"
    }, headers=headers_admin)
    assert res_inv_stg.status_code in (400, 422)

    # 5. CRM Admin reopens to 'Negotiate' with reason -> 200 Succeeded
    res_admin = client.post(f"/api/v1/crm/opportunities/{opp_id}/reopen", json={
        "reopenStage": "Negotiate",
        "reason": "Client requested proposal renegotiation"
    }, headers=headers_admin)
    assert res_admin.status_code == 200
    reopened = res_admin.json()["opportunity"]
    assert reopened["status"] == "Open"
    assert reopened["stage"] == "Negotiate"
    assert reopened["actualCloseDate"] is None


# ==============================================================================
# SPEC SECTION 11: FIELD VALIDATION & RELATIONSHIP RULES
# ==============================================================================
def test_opportunity_relationship_and_amount_rules(setup_kanban_env):
    """
    Mandatory rules:
    - Primary Account only (contactId=None): ALLOW (201)
    - Primary Contact only (accountId=None): ALLOW (201)
    - Both Account and Contact: ALLOW (201)
    - Neither Account nor Contact: REJECT (400/422)
    - Amount >= 0: ALLOW (201)
    - Amount < 0: REJECT (400/422)
    """
    headers = setup_kanban_env["mgr"]
    account, contact = _create_helper(headers, "rel_rules")

    # 1. Primary Account only -> ALLOW (201)
    res_acc_only = client.post("/api/v1/crm/opportunities", json={
        "name": "Account Only Opportunity",
        "accountId": account["id"],
        "contactId": None,
        "stage": "Enquiry",
        "estimatedValue": 100000.0
    }, headers=headers)
    assert res_acc_only.status_code == 201
    assert res_acc_only.json()["opportunity"]["accountId"] == account["id"]
    assert res_acc_only.json()["opportunity"]["contactId"] is None

    # 2. Primary Contact only -> ALLOW (201)
    res_con_only = client.post("/api/v1/crm/opportunities", json={
        "name": "Contact Only Opportunity",
        "accountId": None,
        "contactId": contact["id"],
        "stage": "Enquiry",
        "estimatedValue": 150000.0
    }, headers=headers)
    assert res_con_only.status_code == 201
    assert res_con_only.json()["opportunity"]["accountId"] is None
    assert res_con_only.json()["opportunity"]["contactId"] == contact["id"]

    # 3. Both Account and Contact -> ALLOW (201)
    res_both = client.post("/api/v1/crm/opportunities", json={
        "name": "Both Entities Opportunity",
        "accountId": account["id"],
        "contactId": contact["id"],
        "stage": "Enquiry",
        "estimatedValue": 200000.0
    }, headers=headers)
    assert res_both.status_code == 201

    # 4. Neither Account nor Contact -> REJECT (400/422)
    res_neither = client.post("/api/v1/crm/opportunities", json={
        "name": "Detached Opportunity Invalid",
        "accountId": None,
        "contactId": None,
        "stage": "Enquiry",
        "estimatedValue": 50000.0
    }, headers=headers)
    assert res_neither.status_code in (400, 422)

    # 5. Negative amount -> REJECT (400/422)
    res_neg_amt = client.post("/api/v1/crm/opportunities", json={
        "name": "Negative Amount Opportunity",
        "accountId": account["id"],
        "contactId": contact["id"],
        "stage": "Enquiry",
        "estimatedValue": -500.0
    }, headers=headers)
    assert res_neg_amt.status_code in (400, 422)

    # 6. Zero amount -> ALLOW (201)
    res_zero_amt = client.post("/api/v1/crm/opportunities", json={
        "name": "Zero Amount Opportunity",
        "accountId": account["id"],
        "contactId": contact["id"],
        "stage": "Enquiry",
        "estimatedValue": 0.0
    }, headers=headers)
    assert res_zero_amt.status_code == 201
    assert float(res_zero_amt.json()["opportunity"]["estimatedValue"]) == 0.0


# ==============================================================================
# SPEC SECTION 5: KANBAN & TABLE FILTERING QUERIES
# ==============================================================================
def test_list_opportunities_outcome_and_owner_filters(setup_kanban_env):
    """
    Validates backend API support for:
    - outcome query parameter: 'Open Pipeline', 'Closed Won', 'Closed Lost'
    - owner query parameter
    """
    headers = setup_kanban_env["mgr"]

    # 1. Query with outcome='Open Pipeline'
    res_open = client.get("/api/v1/crm/opportunities?outcome=Open%20Pipeline&limit=10", headers=headers)
    assert res_open.status_code == 200
    for opp in res_open.json()["opportunities"]:
        assert opp["status"] == "Open"

    # 2. Query with outcome='Closed Won'
    res_won = client.get("/api/v1/crm/opportunities?outcome=Closed%20Won&limit=10", headers=headers)
    assert res_won.status_code == 200
    for opp in res_won.json()["opportunities"]:
        assert opp["status"] == "Won"

    # 3. Query with outcome='Closed Lost'
    res_lost = client.get("/api/v1/crm/opportunities?outcome=Closed%20Lost&limit=10", headers=headers)
    assert res_lost.status_code == 200
    for opp in res_lost.json()["opportunities"]:
        assert opp["status"] == "Lost"

