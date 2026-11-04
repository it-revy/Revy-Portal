"""
REVY CRM - Automated Test Suite for Lead Creation Timeout & Activity ID Repair
Tests:
1. ClientRequestId Idempotency - Submitting identical clientRequestId returns existing Lead without duplicate.
2. 90-Second Deduplication Protection - Submitting identical company name & email within 90s returns existing Lead safely.
3. Activity ID with 'act_' prefix - POST .../activities/act_{uuid}/complete succeeds without 404.
4. Activity ID with 'act_' prefix in reschedule and skip workflows.
5. Unified timeline item has canonical activityId and activityCode.
"""
import pytest
from datetime import date, timedelta
import uuid


def test_lead_creation_idempotency_with_client_request_id(client, auth_headers):
    """
    Issue A Test: Verify clientRequestId guarantees idempotency.
    Retrying with the same clientRequestId returns the exact same Lead,
    preventing duplicate records when retrying after a timeout.
    """
    req_id = str(uuid.uuid4())
    payload = {
        "clientRequestId": req_id,
        "leadName": "GreenTech Bio Solutions",
        "companyName": f"GreenTech {uuid.uuid4().hex[:6]} Ltd",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01",
        "contactEmail": f"contact_{uuid.uuid4().hex[:6]}@greentech.test"
    }

    # First submission
    res1 = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res1.status_code in (200, 201), f"First submission failed: {res1.text}"
    lead1 = res1.json()["lead"]
    lead1_id = lead1["id"]
    lead1_code = lead1["leadId"]

    # Simulated retry after network timeout with exact same clientRequestId
    res2 = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res2.status_code in (200, 201), f"Retry submission failed: {res2.text}"
    lead2 = res2.json()["lead"]
    assert lead2["id"] == lead1_id, "Idempotent retry returned different lead UUID!"
    assert lead2["leadId"] == lead1_code, "Idempotent retry generated a duplicate lead code!"


def test_legitimate_separate_leads_with_same_company_allowed(client, auth_headers):
    """
    Production Hardening Spec: Do not reject legitimate separate Leads merely because
    company name and contact email match. Only identical clientRequestId triggers idempotency.
    """
    unique_company = f"Adani BioPower {uuid.uuid4().hex[:6]}"
    unique_email = f"info_{uuid.uuid4().hex[:6]}@adani.test"

    payload1 = {
        "clientRequestId": str(uuid.uuid4()),
        "companyName": unique_company,
        "contactEmail": unique_email,
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01"
    }
    res1 = client.post("/api/v1/crm/leads", json=payload1, headers=auth_headers)
    assert res1.status_code in (200, 201)
    lead1_id = res1.json()["lead"]["id"]

    # Separate legitimate second submission with distinct clientRequestId
    payload2 = {
        "clientRequestId": str(uuid.uuid4()),
        "companyName": unique_company,
        "contactEmail": unique_email,
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01"
    }
    res2 = client.post("/api/v1/crm/leads", json=payload2, headers=auth_headers)
    assert res2.status_code in (200, 201)
    lead2_id = res2.json()["lead"]["id"]
    assert lead2_id != lead1_id, "Legitimate separate lead was improperly rejected or collapsed!"


def test_complete_nurturing_activity_with_act_prefix(client, auth_headers):
    """
    Issue B Test: Completing an activity using the DOM/timeline key 'act_{uuid}'
    must resolve properly and return 200 rather than 404 Not Found.
    """
    # 1. Create a fresh Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "companyName": f"Asmita Agrikulture Test {uuid.uuid4().hex[:6]}",
        "contactEmail": f"contact_{uuid.uuid4().hex[:6]}@asmita.test",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    assert lead_res.status_code in (200, 201)
    lead = lead_res.json()["lead"]
    lead_id = lead["id"]

    # 2. Get timeline to retrieve timeline item with 'id': 'act_{uuid}'
    tl_res = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers)
    assert tl_res.status_code == 200
    timeline = tl_res.json()["timeline"]
    assert len(timeline) >= 1
    act_item = timeline[0]
    dom_id = act_item["id"]  # 'act_732e2d74-...'
    raw_id = act_item["rawId"]  # '732e2d74-...'
    assert dom_id.startswith("act_")
    assert act_item.get("activityId") == raw_id

    # 3. Call complete endpoint with the 'act_{uuid}' prefix (reproducing the exact bug)
    comp_res = client.post(
        f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{dom_id}/complete",
        json={
            "notes": "Sent introductory capabilities deck via email.",
            "outcome": "Email Delivered"
        },
        headers=auth_headers
    )
    assert comp_res.status_code == 200, f"Expected 200 OK for 'act_' prefixed ID, got: {comp_res.status_code} {comp_res.text}"
    nurturing = comp_res.json()["nurturing"]
    assert nurturing["currentStage"] == 3  # Stage 1 complete -> stage 2 waiting buffer -> stage 3 active
    assert any(a["status"] == "Completed" for a in nurturing["activities"])


def test_reschedule_and_skip_activity_with_act_prefix(client, auth_headers):
    """
    Issue B Test: Reschedule and skip endpoints also accept 'act_{uuid}' seamlessly.
    """
    lead_res = client.post("/api/v1/crm/leads", json={
        "companyName": f"Reschedule Test {uuid.uuid4().hex[:6]}",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    assert lead_res.status_code in (200, 201)
    lead_id = lead_res.json()["lead"]["id"]

    tl_res = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers)
    act_item = tl_res.json()["timeline"][0]
    dom_id = act_item["id"]

    # Test Reschedule with act_ prefix
    new_due = (date.today() + timedelta(days=7)).isoformat()
    reschedule_res = client.post(
        f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{dom_id}/reschedule",
        json={
            "newDueDate": new_due,
            "reason": "Client requested call next week after board review."
        },
        headers=auth_headers
    )
    assert reschedule_res.status_code == 200, f"Reschedule with act_ prefix failed: {reschedule_res.text}"

    # Test Skip with act_ prefix
    skip_res = client.post(
        f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{dom_id}/skip",
        json={
            "reason": "Client already has introductory information."
        },
        headers=auth_headers
    )
    assert skip_res.status_code == 200, f"Skip with act_ prefix failed: {skip_res.text}"
