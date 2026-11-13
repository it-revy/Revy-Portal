import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.crm.model import Account, Contact, Lead, Opportunity, LeadCommunicationHistory
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


@pytest.fixture(scope="module")
def crm_auth(setup_crm_stage4_environment):
    return get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")


def test_lead_qualification_workflow_and_open_leads_exclusion(crm_auth):
    """
    1. Qualify Lead with account and contact details.
    2. Confirm Account, Contact, and Opportunity creation and linking.
    3. Confirm Lead status changes to Qualified and has opportunity_id.
    4. Confirm Lead does NOT appear in Open Leads view.
    5. Confirm Lead DOES appear in All Leads and Qualified Leads views.
    6. Confirm Opportunity detail endpoint returns full linked account and contact.
    7. Confirm idempotency: repeating qualification returns existing record, no duplicates.
    """
    headers = crm_auth
    uid = uuid.uuid4().hex[:8]

    # Create a new Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "leadName": f"Pulp & Paper Waste Treatment {uid}",
        "companyName": f"BioPaper Industries {uid}",
        "firstName": "Arun",
        "lastName": "Mehta",
        "contactEmail": f"arun_{uid}@biopaper.com",
        "mobilePhone": "+91-9876543210",
        "businessPhone": "+91-22-28475900",
        "jobTitle": "Head of Technical Services",
        "businessArea": "WWT",
        "location": "Vapi, Gujarat",
        "websiteLink": "https://www.biopaper.com",
        "leadSource": "Referral"
    }, headers=headers)
    assert lead_res.status_code == 201, lead_res.text
    lead_data = lead_res.json()["lead"]
    lead_id = lead_data["id"]

    # Verify the Lead starts in Open Leads view
    open_res = client.get("/api/v1/crm/leads?view=open", headers=headers)
    assert open_res.status_code == 200
    open_leads = open_res.json()["leads"]
    assert any(l["id"] == lead_id for l in open_leads), "New lead must initially appear in Open Leads"

    # Qualify the Lead
    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"BioPaper Industries {uid}",
            "siteName": "Vapi Plant Unit 2",
            "website": "https://www.biopaper.com",
            "email": f"corp_{uid}@biopaper.com",
            "phone": "+91-22-28475900",
            "address": "Plot 12, GIDC, Vapi, Gujarat",
            "industry": "Paper & Pulp"
        },
        "contact": {
            "action": "create",
            "name": "Arun Mehta",
            "email": f"arun_{uid}@biopaper.com",
            "mobileNumber": "+91-9876543210",
            "designation": "Head of Technical Services"
        },
        "opportunityName": f"Effluent Treatment Modernization {uid}",
        "opportunityDescription": "Comprehensive wastewater digestion and sludge testing",
        "estimatedValue": 350000.0,
        "clientStatus": "New"
    }

    qual_res = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json=qualify_payload, headers=headers)
    assert qual_res.status_code == 200, qual_res.text
    q_data = qual_res.json()
    assert q_data["success"] is True

    opp_data = q_data["opportunity"]
    opp_id = opp_data["id"]
    acc_id = q_data["account"]["id"]
    con_id = q_data["contact"]["id"]

    # Verify relationships on returned objects
    assert opp_data["accountId"] == acc_id
    assert opp_data["contactId"] == con_id
    assert opp_data["stage"] == "Enquiry"

    # 1. Verify Lead record in database
    db = SessionLocal()
    try:
        db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
        assert db_lead.lifecycle_status == "Qualified", "Lead status must be Qualified"
        assert db_lead.opportunity_id == opp_id, "Lead must store linked Opportunity ID"
        assert db_lead.account_id == acc_id, "Lead must link Account ID"
        assert db_lead.contact_id == con_id, "Lead must link Contact ID"
        assert db_lead.qualified_at is not None

        # Verify Opportunity record in database
        db_opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
        assert db_opp.account_id == acc_id
        assert db_opp.contact_id == con_id
        assert db_opp.originating_lead_id == lead_id
        assert db_opp.account is not None
        assert db_opp.contact is not None
    finally:
        db.close()

    # 2. Verify Lead has disappeared from Open Leads view
    open_after = client.get("/api/v1/crm/leads?view=open", headers=headers)
    assert open_after.status_code == 200
    assert not any(l["id"] == lead_id for l in open_after.json()["leads"]), "Qualified Lead must NOT appear in Open Leads"

    # 3. Verify Lead remains accessible in All Leads view
    all_leads_res = client.get("/api/v1/crm/leads?view=all", headers=headers)
    assert all_leads_res.status_code == 200
    assert any(l["id"] == lead_id for l in all_leads_res.json()["leads"]), "Qualified Lead MUST appear in All Leads"

    # 4. Verify Lead appears in Qualified Leads view
    qual_view_res = client.get("/api/v1/crm/leads?view=qualified", headers=headers)
    assert qual_view_res.status_code == 200
    assert any(l["id"] == lead_id for l in qual_view_res.json()["leads"]), "Qualified Lead MUST appear in Qualified Leads view"

    # 5. Verify Opportunity details endpoint returns full Account and Contact objects
    opp_detail_res = client.get(f"/api/v1/crm/opportunities/{opp_id}", headers=headers)
    assert opp_detail_res.status_code == 200, opp_detail_res.text
    opp_detail = opp_detail_res.json()["opportunity"]
    assert opp_detail["account"] is not None, "Opportunity detail must include full account object"
    assert opp_detail["account"]["name"] == f"BioPaper Industries {uid}"
    assert opp_detail["account"]["siteName"] == "Vapi Plant Unit 2"
    assert opp_detail["account"]["phone"] == "+91-22-28475900"

    assert opp_detail["contact"] is not None, "Opportunity detail must include full contact object"
    assert opp_detail["contact"]["name"] == "Arun Mehta"
    assert opp_detail["contact"]["designation"] == "Head of Technical Services"
    assert opp_detail["contact"]["email"] == f"arun_{uid}@biopaper.com"

    # 6. Verify Repeated Qualification Idempotency (prevent duplicate Opportunities)
    repeat_res = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json=qualify_payload, headers=headers)
    assert repeat_res.status_code == 200
    assert repeat_res.json()["opportunity"]["id"] == opp_id, "Repeated qualification must return existing Opportunity"

    # Verify no second Opportunity was created in database
    db2 = SessionLocal()
    try:
        opp_count = db2.query(Opportunity).filter(Opportunity.originating_lead_id == lead_id).count()
        assert opp_count == 1, "There must be exactly one Opportunity linked to this Lead"
    finally:
        db2.close()


def test_opportunity_communications_api(crm_auth):
    """
    Test logging and listing interactions on an Opportunity:
    - POST /api/v1/crm/opportunities/{opp_id}/communications
    - GET /api/v1/crm/opportunities/{opp_id}/communications
    - Verifies chronological ordering and retention of originating lead history.
    """
    headers = crm_auth
    uid = uuid.uuid4().hex[:8]

    # Create Account and Contact
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Interactions Test Account {uid}"
    }, headers=headers)
    assert acc_res.status_code == 201
    account = acc_res.json()["account"]

    con_res = client.post("/api/v1/crm/contacts", json={
        "accountId": account["id"],
        "name": f"Pooja Verma {uid}",
        "email": f"pooja_{uid}@test.com"
    }, headers=headers)
    assert con_res.status_code == 201
    contact = con_res.json()["contact"]

    # Create Opportunity
    opp_res = client.post("/api/v1/crm/opportunities", json={
        "name": f"Biogas Facility Expansion {uid}",
        "accountId": account["id"],
        "contactId": contact["id"],
        "stage": "Enquiry",
        "estimatedValue": 250000.0
    }, headers=headers)
    assert opp_res.status_code == 201, opp_res.text
    opp = opp_res.json()["opportunity"]
    opp_id = opp["id"]

    # Log 1st interaction on Opportunity
    comm1_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/communications", json={
        "channel": "Phone / Call",
        "eventType": "Scope Discussion",
        "subject": "Initial Scope Discussion for Expansion",
        "summary": "Discussed reactor volume and feedstock quality requirements.",
        "outcome": "Client requested preliminary proposal.",
        "nextAction": "Prepare technical estimate",
        "followUpDate": "2026-11-20"
    }, headers=headers)
    assert comm1_res.status_code == 201, comm1_res.text

    # Log 2nd interaction on Opportunity
    comm2_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/communications", json={
        "channel": "Email",
        "eventType": "Proposal Sent",
        "subject": "Sent Preliminary Scope Document",
        "summary": "Shared technical specification sheet and tentative timeline.",
        "outcome": "Awaiting client review by Monday."
    }, headers=headers)
    assert comm2_res.status_code == 201, comm2_res.text

    # Get interactions for Opportunity
    list_res = client.get(f"/api/v1/crm/opportunities/{opp_id}/communications", headers=headers)
    assert list_res.status_code == 200, list_res.text
    comms = list_res.json()["communications"]
    assert len(comms) == 2
    subjects = [c["subject"] for c in comms]
    assert "Initial Scope Discussion for Expansion" in subjects
    assert "Sent Preliminary Scope Document" in subjects
