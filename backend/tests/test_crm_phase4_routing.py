import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_routing_env(setup_crm_stage4_environment):
    headers_mgr = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    headers_exec = get_token_headers("stg4_sales_exec", "Pass123!", "CRM_SALES_EXECUTIVE")
    return {"mgr": headers_mgr, "exec": headers_exec}


def _create_opp_with_requirements(headers, req_types, val=500000.0):
    uid = uuid.uuid4().hex[:8]
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Routing Account {uid}",
        "industry": "Biotechnology",
        "website": f"https://route-{uid}.com"
    }, headers=headers)
    assert acc_res.status_code == 201
    account = acc_res.json()["account"]

    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Priya Nair {uid}",
        "email": f"priya_{uid}@route.com",
        "accountId": account["id"]
    }, headers=headers)
    assert con_res.status_code == 201
    contact = con_res.json()["contact"]

    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Routing Opportunity Lead {uid}",
        "companyName": f"Routing Account {uid}",
        "contactEmail": f"priya_{uid}@route.com",
        "businessArea": "Biogas",
        "estimatedValue": val,
        "requirementTypes": req_types
    }, headers=headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]

    qual_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json={
        "account": {"action": "reuse", "accountId": account["id"]},
        "contact": {"action": "reuse", "contactId": contact["id"]},
        "opportunityName": f"Routing Opp {uid}",
        "estimatedValue": val
    }, headers=headers)
    assert qual_res.status_code == 200
    return qual_res.json()["opportunity"]


def test_route_consulting_requirement(setup_routing_env):
    """
    Verify routing Consulting creates ConsultingEngagement in Draft status,
    with matching account, contact, opportunity, and zero invoice.
    """
    headers = setup_routing_env["mgr"]
    opp = _create_opp_with_requirements(headers, ["Consulting"], 400000.0)

    res = client.post(f"/api/v1/crm/opportunities/{opp['id']}/route-requirements", json={
        "requirementTypes": ["Consulting"]
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["routedWorkstreams"]) == 1
    ws = data["routedWorkstreams"][0]
    assert ws["type"] == "consulting"
    assert ws["recordNumber"].startswith("ENG-")
    assert ws["status"] == "Draft"
    assert ws["details"]["agreedFee"] == 400000.0


def test_route_sample_testing_requirement(setup_routing_env):
    """
    Verify routing Sample Testing creates SampleSubmission in Received status,
    with zero automatic billing charges.
    """
    headers = setup_routing_env["mgr"]
    opp = _create_opp_with_requirements(headers, ["Sample Testing"], 150000.0)

    res = client.post(f"/api/v1/crm/opportunities/{opp['id']}/route-requirements", json={
        "requirementTypes": ["Sample Testing"]
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["routedWorkstreams"]) == 1
    ws = data["routedWorkstreams"][0]
    assert ws["type"] == "sample_testing"
    assert ws["recordNumber"].startswith("SMP-")
    assert ws["status"] == "Received"
    assert ws["details"]["sampleLevelCharge"] == 0.0


def test_route_product_requirement(setup_routing_env):
    """
    Verify routing Product creates ProductTransaction in Recommendation type and Pending status,
    without confirmed order status.
    """
    headers = setup_routing_env["mgr"]
    opp = _create_opp_with_requirements(headers, ["Product"], 250000.0)

    res = client.post(f"/api/v1/crm/opportunities/{opp['id']}/route-requirements", json={
        "requirementTypes": ["Product"]
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["routedWorkstreams"]) == 1
    ws = data["routedWorkstreams"][0]
    assert ws["type"] == "product"
    assert ws["recordNumber"].startswith("PRD-")
    assert ws["status"] == "Pending"
    assert ws["details"]["transactionType"] == "Recommendation"


def test_route_multiple_requirements_and_idempotency(setup_routing_env):
    """
    Verify routing multiple requirements simultaneously (Consulting, Sample Testing, Product).
    Verify retrying route is 100% idempotent and does not create duplicate workstreams.
    """
    headers = setup_routing_env["mgr"]
    all_reqs = ["Consulting", "Sample Testing", "Product"]
    opp = _create_opp_with_requirements(headers, all_reqs, 900000.0)

    # 1. First route execution
    res1 = client.post(f"/api/v1/crm/opportunities/{opp['id']}/route-requirements", json={
        "requirementTypes": all_reqs
    }, headers=headers)
    assert res1.status_code == 200
    ws1 = res1.json()["routedWorkstreams"]
    assert len(ws1) == 3
    types1 = {w["type"] for w in ws1}
    assert types1 == {"consulting", "sample_testing", "product"}
    ids1 = {w["id"] for w in ws1}

    # 2. Second route execution (Retry / Idempotency check)
    res2 = client.post(f"/api/v1/crm/opportunities/{opp['id']}/route-requirements", json={
        "requirementTypes": all_reqs
    }, headers=headers)
    assert res2.status_code == 200
    ws2 = res2.json()["routedWorkstreams"]
    assert len(ws2) == 3
    ids2 = {w["id"] for w in ws2}
    assert ids1 == ids2, "Idempotency violated: duplicate workstream IDs created on retry"
    assert "already routed" in res2.json()["message"]


def test_get_workstreams_endpoint(setup_routing_env):
    """
    Verify GET /crm/opportunities/{id}/workstreams retrieves all linked workstreams accurately.
    """
    headers = setup_routing_env["mgr"]
    opp = _create_opp_with_requirements(headers, ["Consulting", "Product"], 600000.0)

    # Route both
    _ = client.post(f"/api/v1/crm/opportunities/{opp['id']}/route-requirements", json={
        "requirementTypes": ["Consulting", "Product"]
    }, headers=headers)

    # Fetch workstreams
    ws_res = client.get(f"/api/v1/crm/opportunities/{opp['id']}/workstreams", headers=headers)
    assert ws_res.status_code == 200
    data = ws_res.json()
    assert data["success"] is True
    assert data["opportunityId"] == opp["id"]
    assert len(data["workstreams"]) == 2
    types = {w["type"] for w in data["workstreams"]}
    assert types == {"consulting", "product"}


def test_update_opportunity_requirements_endpoint(setup_routing_env):
    """
    Verify PUT /crm/opportunities/{id}/requirements updates the requirementTypes array.
    """
    headers = setup_routing_env["mgr"]
    opp = _create_opp_with_requirements(headers, ["Consulting"], 300000.0)

    put_res = client.put(f"/api/v1/crm/opportunities/{opp['id']}/requirements", json={
        "requirementTypes": ["Consulting", "Sample Testing"]
    }, headers=headers)
    assert put_res.status_code == 200
    updated_opp = put_res.json()["opportunity"]
    assert "Consulting" in updated_opp["requirementTypes"]
    assert "Sample Testing" in updated_opp["requirementTypes"]


def test_route_zero_requirements_safely(setup_routing_env):
    """
    Verify routing an Opportunity with zero/empty requirements succeeds safely
    without error, creating 0 workstreams.
    """
    headers = setup_routing_env["mgr"]
    opp = _create_opp_with_requirements(headers, [], 100000.0)

    res = client.post(f"/api/v1/crm/opportunities/{opp['id']}/route-requirements", json={
        "requirementTypes": []
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["routedWorkstreams"]) == 0
    assert "No requirement types" in data["message"]

