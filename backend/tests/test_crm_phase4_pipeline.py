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
def setup_phase4_env(setup_crm_stage4_environment):
    headers_mgr = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    headers_exec = get_token_headers("stg4_sales_exec", "Pass123!", "CRM_SALES_EXECUTIVE")
    return {"mgr": headers_mgr, "exec": headers_exec}


def _create_test_opportunity(headers, suffix=""):
    uid = uuid.uuid4().hex[:8] + suffix
    # 1. Account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Pipeline Test Corp {uid}",
        "industry": "Renewable Energy",
        "website": f"https://pipeline-{uid}.com"
    }, headers=headers)
    assert acc_res.status_code == 201
    account = acc_res.json()["account"]

    # 2. Contact
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Arun Kumar {uid}",
        "email": f"arun_{uid}@pipeline.com",
        "accountId": account["id"]
    }, headers=headers)
    assert con_res.status_code == 201
    contact = con_res.json()["contact"]

    # 3. Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Pipeline Biogas Expansion {uid}",
        "companyName": f"Pipeline Test Corp {uid}",
        "contactEmail": f"arun_{uid}@pipeline.com",
        "businessArea": "Biogas",
        "estimatedValue": 750000.0,
        "requirementTypes": ["Consulting", "Sample Testing"]
    }, headers=headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]

    # 4. Qualify Lead -> Creates Opportunity
    qual_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json={
        "account": {"action": "reuse", "accountId": account["id"]},
        "contact": {"action": "reuse", "contactId": contact["id"]},
        "opportunityName": f"Pipeline Opp {uid}",
        "estimatedValue": 750000.0
    }, headers=headers)
    assert qual_res.status_code == 200, f"Qualify failed: {qual_res.text}"
    return qual_res.json()["opportunity"]


def test_opportunity_initial_state_and_defaults(setup_phase4_env):
    """
    Verify newly qualified Opportunity starts at stage='Qualify', status='Open',
    with accurate businessArea, estimatedValue, and zero lossReason.
    """
    headers = setup_phase4_env["mgr"]
    opp = _create_test_opportunity(headers, "init")

    assert opp["stage"] == "Qualify"
    assert opp["status"] == "Open"
    assert opp["lossReason"] is None
    assert opp["estimatedValue"] == 750000.0
    assert opp["currency"] == "INR"
    assert opp["businessArea"] == "Biogas"
    assert opp["milestoneCount"] == 0
    assert opp["workstreamCount"] == 0


def test_pipeline_summary_endpoint(setup_phase4_env):
    """
    Verify /crm/opportunities/pipeline-summary returns authoritative stage metrics
    and status breakdowns.
    """
    headers = setup_phase4_env["mgr"]
    _ = _create_test_opportunity(headers, "sum")

    res = client.get("/api/v1/crm/opportunities/pipeline-summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["totalCount"] >= 1
    assert data["totalOpenValue"] >= 750000.0
    assert "byStage" in data
    assert len(data["byStage"]) == 6

    stages = [item["stage"] for item in data["byStage"]]
    assert stages == ["Enquiry", "Qualify", "Develop", "Propose/Offer", "Negotiate", "Close"]

    assert "byStatus" in data
    assert "Open" in data["byStatus"]
    assert "Won" in data["byStatus"]
    assert "Lost" in data["byStatus"]


def test_opportunity_stage_progression(setup_phase4_env):
    """
    Verify stage progression: Qualify -> Develop -> Propose/Offer -> Negotiate -> Close.
    """
    headers = setup_phase4_env["mgr"]
    opp = _create_test_opportunity(headers, "prog")
    opp_id = opp["id"]

    # 1. Qualify -> Develop
    res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Develop",
        "remarks": "Feasibility confirmed, advancing to develop"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["opportunity"]["stage"] == "Develop"
    assert res.json()["opportunity"]["status"] == "Open"

    # 2. Develop -> Propose/Offer
    res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Propose/Offer",
        "remarks": "Proposal delivered to client"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["opportunity"]["stage"] == "Propose/Offer"

    # 3. Propose/Offer -> Negotiate
    res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Negotiate",
        "remarks": "Commercial negotiations active"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["opportunity"]["stage"] == "Negotiate"

    # 4. Negotiate -> Close (Attempting Close + Open must be rejected per Section 9)
    res_open = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Close",
        "status": "Open",
        "remarks": "Contract finalized"
    }, headers=headers)
    assert res_open.status_code == 400

    # 4b. Advancing to Close with valid outcome Won succeeds
    res_won = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Close",
        "status": "Won",
        "remarks": "Contract signed and won"
    }, headers=headers)
    assert res_won.status_code == 200
    assert res_won.json()["opportunity"]["stage"] == "Close"
    assert res_won.json()["opportunity"]["status"] == "Won"


def test_opportunity_won_outcome(setup_phase4_env):
    """
    Verify Opportunity can be marked as Won when in Close stage.
    Verify marking Won when NOT in Close stage is rejected.
    """
    headers = setup_phase4_env["mgr"]
    opp = _create_test_opportunity(headers, "won")
    opp_id = opp["id"]

    # Try marking Won while in Qualify stage -> should fail
    fail_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Qualify",
        "status": "Won"
    }, headers=headers)
    assert fail_res.status_code == 422 or fail_res.status_code == 400

    # Advance to Close and mark Won
    won_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Close",
        "status": "Won",
        "remarks": "Client signed MSA"
    }, headers=headers)
    assert won_res.status_code == 200
    won_data = won_res.json()["opportunity"]
    assert won_data["stage"] == "Close"
    assert won_data["status"] == "Won"
    assert won_data["actualCloseDate"] is not None
    assert won_data["lossReason"] is None


def test_opportunity_lost_outcome_requires_loss_reason(setup_phase4_env):
    """
    Verify Opportunity marked as Lost requires a non-empty lossReason.
    """
    headers = setup_phase4_env["mgr"]
    opp = _create_test_opportunity(headers, "lost")
    opp_id = opp["id"]

    # Try marking Lost without lossReason -> must fail
    fail_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Develop",
        "status": "Lost"
    }, headers=headers)
    assert fail_res.status_code == 422 or fail_res.status_code == 400

    # Supply lossReason -> must succeed
    lost_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Develop",
        "status": "Lost",
        "lossReason": "Client chose in-house biological treatment instead"
    }, headers=headers)
    assert lost_res.status_code == 200
    lost_data = lost_res.json()["opportunity"]
    assert lost_data["status"] == "Lost"
    assert lost_data["lossReason"] == "Client chose in-house biological treatment instead"
    assert lost_data["actualCloseDate"] is not None

    # Reopening back to Open clears lossReason
    reopen_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={
        "newStage": "Qualify",
        "status": "Open",
        "remarks": "Client requested re-evaluation"
    }, headers=headers)
    assert reopen_res.status_code == 200
    reopen_data = reopen_res.json()["opportunity"]
    assert reopen_data["status"] == "Open"
    assert reopen_data["lossReason"] is None
    assert reopen_data["actualCloseDate"] is None


def test_opportunity_update_fields(setup_phase4_env):
    """
    Verify PUT /crm/opportunities/{id} updates fields:
    name, estimatedValue, expectedCloseDate, businessArea, description.
    """
    headers = setup_phase4_env["mgr"]
    opp = _create_test_opportunity(headers, "upd")
    opp_id = opp["id"]

    close_date = (date.today() + timedelta(days=60)).isoformat()
    update_res = client.put(f"/api/v1/crm/opportunities/{opp_id}", json={
        "name": "Updated Strategic Opportunity Name",
        "estimatedValue": 1250000.0,
        "expectedCloseDate": close_date,
        "businessArea": "Wastewater Treatment (WWT)",
        "description": "Expanded scope to include anaerobic sludge testing"
    }, headers=headers)
    assert update_res.status_code == 200
    updated = update_res.json()["opportunity"]
    assert updated["name"] == "Updated Strategic Opportunity Name"
    assert updated["estimatedValue"] == 1250000.0
    assert updated["expectedCloseDate"] == close_date
    assert updated["businessArea"] == "Wastewater Treatment (WWT)"
    assert updated["description"] == "Expanded scope to include anaerobic sludge testing"


def test_opportunity_list_filtering_and_views(setup_phase4_env):
    """
    Verify GET /crm/opportunities supports filtering by stage, status, view, search, and returns totalCount.
    """
    headers = setup_phase4_env["mgr"]
    opp = _create_test_opportunity(headers, "list")

    # Search by opportunity ID
    res = client.get(f"/api/v1/crm/opportunities?search={opp['opportunityId']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["totalCount"] >= 1
    assert any(o["id"] == opp["id"] for o in res.json()["opportunities"])

    # Filter by stage
    stage_res = client.get("/api/v1/crm/opportunities?stage=Qualify", headers=headers)
    assert stage_res.status_code == 200
    assert all(o["stage"] == "Qualify" for o in stage_res.json()["opportunities"])

    # Filter by view=open
    view_res = client.get("/api/v1/crm/opportunities?view=open", headers=headers)
    assert view_res.status_code == 200
    assert all(o["status"] == "Open" for o in view_res.json()["opportunities"])
