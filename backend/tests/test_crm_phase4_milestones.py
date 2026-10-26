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
def setup_milestone_env(setup_crm_stage4_environment):
    headers_mgr = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    headers_exec = get_token_headers("stg4_sales_exec", "Pass123!", "CRM_SALES_EXECUTIVE")
    return {"mgr": headers_mgr, "exec": headers_exec}


def _create_opp(headers):
    uid = uuid.uuid4().hex[:8]
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Milestone Account {uid}",
        "industry": "Industrial Bio",
        "website": f"https://ms-{uid}.com"
    }, headers=headers)
    assert acc_res.status_code == 201
    account = acc_res.json()["account"]

    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Ravi Varma {uid}",
        "email": f"ravi_{uid}@ms.com",
        "accountId": account["id"]
    }, headers=headers)
    assert con_res.status_code == 201
    contact = con_res.json()["contact"]

    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Milestone Lead {uid}",
        "companyName": f"Milestone Account {uid}",
        "contactEmail": f"ravi_{uid}@ms.com",
        "businessArea": "Biogas",
        "estimatedValue": 800000.0,
        "requirementTypes": ["Consulting"]
    }, headers=headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]

    qual_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json={
        "account": {"action": "reuse", "accountId": account["id"]},
        "contact": {"action": "reuse", "contactId": contact["id"]},
        "opportunityName": f"Milestone Opp {uid}",
        "estimatedValue": 800000.0
    }, headers=headers)
    assert qual_res.status_code == 200
    return qual_res.json()["opportunity"]


def test_create_and_list_milestone(setup_milestone_env):
    """
    Verify creating a Milestone for an Opportunity and listing it.
    """
    headers = setup_milestone_env["mgr"]
    opp = _create_opp(headers)
    opp_id = opp["id"]

    start = date.today().isoformat()
    due = (date.today() + timedelta(days=10)).isoformat()

    create_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/milestones", json={
        "title": "Site Inspection & Feedstock Sampling",
        "description": "Collect representative anaerobic digester slurry samples.",
        "workstreamType": "consulting",
        "plannedStartDate": start,
        "dueDate": due
    }, headers=headers)
    assert create_res.status_code == 201
    m = create_res.json()["milestone"]
    assert m["milestoneId"].startswith("MLS-")
    assert m["title"] == "Site Inspection & Feedstock Sampling"
    assert m["status"] == "Pending"
    assert m["dueDate"] == due
    assert m["isOverdue"] is False

    # List milestones for opportunity
    list_res = client.get(f"/api/v1/crm/opportunities/{opp_id}/milestones", headers=headers)
    assert list_res.status_code == 200
    m_list = list_res.json()["milestones"]
    assert len(m_list) == 1
    assert m_list[0]["id"] == m["id"]


def test_milestone_status_lifecycle(setup_milestone_env):
    """
    Verify status transition: Pending -> In Progress -> Completed -> Reopened.
    Verify completedAt timestamp is set on Completed and cleared on Reopen.
    """
    headers = setup_milestone_env["mgr"]
    opp = _create_opp(headers)
    opp_id = opp["id"]

    # 1. Create
    create_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/milestones", json={
        "title": "Anaerobic Digester Assessment",
        "dueDate": (date.today() + timedelta(days=7)).isoformat()
    }, headers=headers)
    m_id = create_res.json()["milestone"]["id"]

    # 2. Transition to In Progress
    prog_res = client.post(f"/api/v1/crm/milestones/{m_id}/status", json={
        "status": "In Progress"
    }, headers=headers)
    assert prog_res.status_code == 200
    assert prog_res.json()["milestone"]["status"] == "In Progress"
    assert prog_res.json()["milestone"]["completedAt"] is None

    # 3. Transition to Completed
    comp_res = client.post(f"/api/v1/crm/milestones/{m_id}/status", json={
        "status": "Completed",
        "completionNotes": "Digester assessment completed and signed off by Lead Scientist."
    }, headers=headers)
    assert comp_res.status_code == 200
    comp_m = comp_res.json()["milestone"]
    assert comp_m["status"] == "Completed"
    assert comp_m["completedAt"] is not None
    assert comp_m["completionNotes"] == "Digester assessment completed and signed off by Lead Scientist."

    # 4. Reopen back to In Progress
    reopen_res = client.post(f"/api/v1/crm/milestones/{m_id}/status", json={
        "status": "In Progress"
    }, headers=headers)
    assert reopen_res.status_code == 200
    assert reopen_res.json()["milestone"]["status"] == "In Progress"
    assert reopen_res.json()["milestone"]["completedAt"] is None


def test_milestone_overdue_flag_and_upcoming(setup_milestone_env):
    """
    Verify isOverdue=True when dueDate is in the past for active milestone.
    Verify upcoming milestones endpoint returns milestones within horizon.
    """
    headers = setup_milestone_env["mgr"]
    opp = _create_opp(headers)
    opp_id = opp["id"]

    past_date = (date.today() - timedelta(days=3)).isoformat()
    future_date = (date.today() + timedelta(days=5)).isoformat()

    # Overdue milestone
    overdue_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/milestones", json={
        "title": "Past Due Lab Analysis",
        "dueDate": past_date
    }, headers=headers)
    assert overdue_res.status_code == 201
    assert overdue_res.json()["milestone"]["isOverdue"] is True

    # Upcoming milestone
    future_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/milestones", json={
        "title": "Upcoming Pilot Trial",
        "dueDate": future_date
    }, headers=headers)
    assert future_res.status_code == 201
    assert future_res.json()["milestone"]["isOverdue"] is False

    # Check /crm/milestones/upcoming
    upcoming_res = client.get("/api/v1/crm/milestones/upcoming?days=14", headers=headers)
    assert upcoming_res.status_code == 200
    titles = [m["title"] for m in upcoming_res.json()["milestones"]]
    assert "Upcoming Pilot Trial" in titles


def test_milestone_update_and_delete(setup_milestone_env):
    """
    Verify updating milestone details and deleting milestone.
    """
    headers = setup_milestone_env["mgr"]
    opp = _create_opp(headers)
    opp_id = opp["id"]

    create_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/milestones", json={
        "title": "Initial Feasibility",
        "dueDate": (date.today() + timedelta(days=15)).isoformat()
    }, headers=headers)
    m_id = create_res.json()["milestone"]["id"]

    # Update
    new_due = (date.today() + timedelta(days=20)).isoformat()
    upd_res = client.put(f"/api/v1/crm/milestones/{m_id}", json={
        "title": "Revised Comprehensive Feasibility Study",
        "dueDate": new_due
    }, headers=headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["milestone"]["title"] == "Revised Comprehensive Feasibility Study"
    assert upd_res.json()["milestone"]["dueDate"] == new_due

    # Delete
    del_res = client.delete(f"/api/v1/crm/milestones/{m_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Confirm 404
    get_res = client.get(f"/api/v1/crm/milestones/{m_id}", headers=headers)
    assert get_res.status_code == 404
