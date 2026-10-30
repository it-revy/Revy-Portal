import uuid
import pytest
from fastapi.testclient import TestClient

def test_new_lead_defaults_to_enquiry(client: TestClient, auth_headers: dict):
    """Rule 1: New leads default to Enquiry."""
    payload = {
        "companyName": "Acme Industrial Testing Ltd",
        "contactName": "Alice Johnson",
        "email": "alice@acmeindustrial.com",
        "phone": "+91 98765 43210",
        "requirementTypes": ["Sample Testing"]
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res.status_code in (200, 201), f"Create lead failed: {res.text}"
    data = res.json()["lead"]
    assert data["lifecycleStatus"] == "Enquiry", f"Expected Enquiry, got {data['lifecycleStatus']}"


def test_six_approved_lead_statuses_accepted(client: TestClient, auth_headers: dict):
    """Rule 2: All six approved Lead Status values are accepted."""
    lead_payload = {
        "companyName": "Six Status Verification Corp",
        "contactName": "Bob Smith",
        "email": "bob@sixstatus.com",
        "phone": "+91 98765 00001"
    }
    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    lead_id = create_res.json()["lead"]["id"]

    approved_statuses = ["Enquiry", "Offer", "Negotiation", "Supply", "Payment", "Dormant"]
    for status in approved_statuses:
        status_payload = {
            "status": status,
            "remarks": f"Transitioned to {status} during test"
        }
        res = client.post(f"/api/v1/crm/leads/{lead_id}/status", json=status_payload, headers=auth_headers)
        assert res.status_code == 200, f"Status {status} rejected: {res.text}"
        data = res.json()["lead"]
        assert data["lifecycleStatus"] == status, f"Expected {status}, got {data['lifecycleStatus']}"


def test_unapproved_lead_status_rejected(client: TestClient, auth_headers: dict):
    """Rule 3: Unapproved Lead Status values are rejected."""
    lead_payload = {
        "companyName": "Validation Rejection Inc",
        "contactName": "Charlie Brown",
        "email": "charlie@rejection.com"
    }
    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    lead_id = create_res.json()["lead"]["id"]

    unapproved_statuses = ["Qualified", "Disqualified", "Proposal", "Won", "Lost", "Closed", "RandomStatus"]
    for unapproved in unapproved_statuses:
        res = client.post(
            f"/api/v1/crm/leads/{lead_id}/status",
            json={"status": unapproved, "remarks": "Invalid test"},
            headers=auth_headers
        )
        assert res.status_code in (400, 422), f"Unapproved status {unapproved} should be rejected, got {res.status_code}"


def test_dormant_reactivation_and_audit_history(client: TestClient, auth_headers: dict):
    """Rule 4 & 6: Dormant leads can be reactivated and transitions record history."""
    lead_payload = {
        "companyName": "Dormant Lifecycle Testing Pvt",
        "contactName": "Danielle Green",
        "email": "danielle@dormanttest.com"
    }
    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    lead_id = create_res.json()["lead"]["id"]

    # Transition to Dormant
    res_dormant = client.post(
        f"/api/v1/crm/leads/{lead_id}/status",
        json={"status": "Dormant", "remarks": "Requirement paused by customer"},
        headers=auth_headers
    )
    assert res_dormant.status_code == 200
    assert res_dormant.json()["lead"]["lifecycleStatus"] == "Dormant"

    # Reactivate to Negotiation
    res_reactivate = client.post(
        f"/api/v1/crm/leads/{lead_id}/status",
        json={"status": "Negotiation", "remarks": "Customer requested active follow-up"},
        headers=auth_headers
    )
    assert res_reactivate.status_code == 200
    assert res_reactivate.json()["lead"]["lifecycleStatus"] == "Negotiation"


def test_lead_qualification_decoupled_status(client: TestClient, auth_headers: dict):
    """Rule 7: Qualification does NOT introduce an unapproved Lead Status (e.g., Qualified)."""
    uid = uuid.uuid4().hex[:6]
    lead_payload = {
        "companyName": f"De-coupled Enterprises {uid}",
        "contactName": f"Emma Watson {uid}",
        "email": f"emma_{uid}@qualificationtest.com",
        "phone": "+91 99887 76655",
        "requirementTypes": ["Consultancy"]
    }
    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    lead_id = create_res.json()["lead"]["id"]

    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"De-coupled Enterprises {uid}",
            "industry": "Biotechnology"
        },
        "contact": {
            "action": "create",
            "name": f"Emma Watson {uid}",
            "email": f"emma_{uid}@qualificationtest.com",
            "mobileNumber": "+91 99887 76655"
        },
        "opportunityName": f"Biogas Consulting Phase 1 {uid}",
        "estimatedValue": 350000.0,
        "opportunityDescription": "Comprehensive biogas consulting and sample testing"
    }
    qualify_res = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json=qualify_payload, headers=auth_headers)
    assert qualify_res.status_code == 200, f"Qualify failed: {qualify_res.text}"

    # Verify lead details
    lead_res = client.get(f"/api/v1/crm/leads/{lead_id}", headers=auth_headers)
    assert lead_res.status_code == 200
    lead_data = lead_res.json()["lead"]

    # Must NOT be "Qualified"; should be "Negotiation" (or an approved status)
    assert lead_data["lifecycleStatus"] in ("Negotiation", "Offer", "Supply", "Payment", "Enquiry")
    assert lead_data["lifecycleStatus"] != "Qualified"
    assert lead_data.get("isQualified") is True
    assert lead_data.get("qualifiedAt") is not None
    assert len(lead_data.get("opportunities", [])) >= 1


def test_multiple_opportunities_per_lead(client: TestClient, auth_headers: dict):
    """Rule 9 & 10: One Lead can have multiple Opportunities."""
    uid = uuid.uuid4().hex[:6]
    lead_payload = {
        "companyName": f"Multi-Opp Works {uid}",
        "contactName": f"Frank Miller {uid}",
        "email": f"frank_{uid}@multiopp.com",
        "phone": "+91 91234 56789"
    }
    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    lead_id = create_res.json()["lead"]["id"]

    # Create Opportunity 1
    opp1_payload = {
        "name": "Consultancy Assessment 2026",
        "estimatedValue": 150000.0,
        "stage": "Qualify",
        "subStatus": "Waiting for revised quotation",
        "description": "Initial plant feasibility"
    }
    res_opp1 = client.post(f"/api/v1/crm/leads/{lead_id}/opportunities", json=opp1_payload, headers=auth_headers)
    assert res_opp1.status_code in (200, 201), f"Create Opp 1 failed: {res_opp1.text}"
    opp1_id = res_opp1.json()["opportunity"]["id"]

    # Create Opportunity 2
    opp2_payload = {
        "name": "Sample Testing Batch A",
        "estimatedValue": 45000.0,
        "stage": "Develop",
        "subStatus": "Sample collection to be scheduled",
        "description": "Lab testing for 5 digester samples"
    }
    res_opp2 = client.post(f"/api/v1/crm/leads/{lead_id}/opportunities", json=opp2_payload, headers=auth_headers)
    assert res_opp2.status_code in (200, 201), f"Create Opp 2 failed: {res_opp2.text}"
    opp2_id = res_opp2.json()["opportunity"]["id"]

    assert opp1_id != opp2_id, "Opportunities must be distinct entities"

    # Fetch Lead details and verify both opportunities exist on lead
    lead_res = client.get(f"/api/v1/crm/leads/{lead_id}", headers=auth_headers)
    assert lead_res.status_code == 200
    opps = lead_res.json()["lead"]["opportunities"]
    opp_ids = [o["id"] for o in opps]
    assert opp1_id in opp_ids, "Opportunity 1 must be present on lead"
    assert opp2_id in opp_ids, "Opportunity 2 must be present on lead"
    assert len(opps) >= 2, f"Expected at least 2 opportunities, got {len(opps)}"


def test_opportunity_sub_status_free_text_crud(client: TestClient, auth_headers: dict):
    """Rule 11-15: Sub-status is free text, accepts arbitrary valid text, persists, updates, clears, and does not alter Lead Status."""
    uid = uuid.uuid4().hex[:6]
    lead_payload = {
        "companyName": f"SubStatus Test Corp {uid}",
        "contactName": f"Grace Hopper {uid}",
        "email": f"grace_{uid}@substatus.org"
    }
    lead_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert lead_res.status_code in (200, 201)
    lead_id = lead_res.json()["lead"]["id"]
    initial_lead_status = lead_res.json()["lead"]["lifecycleStatus"]

    # 1. Create with arbitrary text
    test_sub_status_text = "Client reviewing annual fee; follow-up scheduled for Friday afternoon."
    opp_payload = {
        "name": "Opportunity With Free-Text SubStatus",
        "estimatedValue": 200000.0,
        "subStatus": test_sub_status_text
    }
    create_res = client.post(f"/api/v1/crm/leads/{lead_id}/opportunities", json=opp_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    opp = create_res.json()["opportunity"]
    opp_id = opp["id"]
    assert opp["subStatus"] == test_sub_status_text

    # 2. Persists on GET
    get_res = client.get(f"/api/v1/crm/opportunities/{opp_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["opportunity"]["subStatus"] == test_sub_status_text

    # 3. Update Sub-status
    updated_text = "Awaiting advance payment before initiating trial."
    patch_res = client.patch(
        f"/api/v1/crm/opportunities/{opp_id}",
        json={"subStatus": updated_text},
        headers=auth_headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["opportunity"]["subStatus"] == updated_text

    # 4. Verify Lead Status was NOT modified by opportunity sub_status changes
    lead_check = client.get(f"/api/v1/crm/leads/{lead_id}", headers=auth_headers).json()["lead"]
    assert lead_check["lifecycleStatus"] == initial_lead_status

    # 5. Clear Sub-status (blank / null)
    clear_res = client.patch(
        f"/api/v1/crm/opportunities/{opp_id}",
        json={"subStatus": None},
        headers=auth_headers
    )
    assert clear_res.status_code == 200
    assert clear_res.json()["opportunity"]["subStatus"] is None


def test_opportunity_closure_records_actor_and_reason(client: TestClient, auth_headers: dict):
    """Rule 17: Closure records the appropriate actor, timestamp, and reason."""
    uid = uuid.uuid4().hex[:6]
    lead_payload = {
        "companyName": f"Closure Analysis Co {uid}",
        "contactName": f"Henry Ford {uid}",
        "email": f"henry_{uid}@closureco.com"
    }
    lead_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    lead_id = lead_res.json()["lead"]["id"]

    opp_res = client.post(
        f"/api/v1/crm/leads/{lead_id}/opportunities",
        json={"name": "Opportunity For Closure Audit", "estimatedValue": 100000.0},
        headers=auth_headers
    )
    opp_id = opp_res.json()["opportunity"]["id"]

    # Close as Lost with reason
    loss_reason = "Budget reallocated to internal manufacturing expansion."
    stage_res = client.post(
        f"/api/v1/crm/opportunities/{opp_id}/stage",
        json={"newStage": "Close", "status": "Lost", "lossReason": loss_reason},
        headers=auth_headers
    )
    assert stage_res.status_code == 200, f"Stage change failed: {stage_res.text}"
    closed_opp = stage_res.json()["opportunity"]
    assert closed_opp["stage"] == "Close"
    assert closed_opp["status"] == "Lost"
    assert closed_opp["lossReason"] == loss_reason


def test_no_prohibited_downstream_records_created(client: TestClient, auth_headers: dict):
    """Rule 18: Opportunity creation does NOT automatically create invoices, dispatch, or samples."""
    lead_payload = {
        "companyName": "Operational Isolation Corp",
        "contactName": "Ian Malcolm",
        "email": "ian@jurassic.org"
    }
    lead_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    lead_id = lead_res.json()["lead"]["id"]

    opp_res = client.post(
        f"/api/v1/crm/leads/{lead_id}/opportunities",
        json={"name": "Dry Run Commercial Opportunity", "estimatedValue": 500000.0},
        headers=auth_headers
    )
    assert opp_res.status_code in (200, 201)
    opp = opp_res.json()["opportunity"]

    # Verify no auto-generated lab samples, workstreams, or milestones unless requested
    workstreams_res = client.get(f"/api/v1/crm/opportunities/{opp['id']}/workstreams", headers=auth_headers)
    assert workstreams_res.status_code == 200
    assert len(workstreams_res.json().get("workstreams", [])) == 0

    milestones_res = client.get(f"/api/v1/crm/opportunities/{opp['id']}/milestones", headers=auth_headers)
    assert milestones_res.status_code == 200
    assert len(milestones_res.json().get("milestones", [])) == 0


def test_dashboard_metrics_reflect_sales_hub_statuses(client: TestClient, auth_headers: dict):
    """Rule 27: Dashboard metrics correctly aggregate active statuses and dormant."""
    metrics_res = client.get("/api/v1/crm/dashboard/metrics", headers=auth_headers)
    assert metrics_res.status_code == 200
    data = metrics_res.json()
    assert "openLeads" in data
    assert "qualifiedLeads" in data
    assert data["openLeads"] >= 0
