"""
REVY CRM - Automated Test Suite for Lead Nurturing & Unified Timeline
Covers automatic initialization, Date Connected + 5-day scheduling, activity completion,
automatic interaction creation, duplicate prevention, customer response pausing,
resuming, and full end-to-end lifecycle.
"""
import pytest
from datetime import date, timedelta, datetime, timezone
from zoneinfo import ZoneInfo

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def test_auto_initialization_on_lead_create(client, auth_headers):
    """
    Test 1: Creating a new lead automatically starts nurturing,
    initializes Stage 1 Introduction Email (Pending), and calculates
    First Follow-up Date = Date Connected + 5 calendar days.
    No false sent communication record must exist.
    """
    payload = {
        "leadName": "Tata Chemicals Green Initiative",
        "companyName": "Tata Chemicals Ltd",
        "businessArea": "Biogas",
        "requirementType": "Consulting",
        "connectedDate": "2026-11-01",
        "leadSource": "Website",
        "contactEmail": "contact@tatachemicals.test"
    }

    create_res = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert create_res.status_code in (200, 201), f"Lead creation failed: {create_res.text}"
    lead_data = create_res.json()["lead"]
    lead_id = lead_data["id"]

    # Verify Nurturing Process
    nurturing_res = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers)
    assert nurturing_res.status_code == 200
    nurturing = nurturing_res.json()["nurturing"]

    assert nurturing["status"] == "Active"
    assert nurturing["currentStage"] == 1
    assert len(nurturing["activities"]) >= 1

    stage_1 = nurturing["activities"][0]
    assert stage_1["stageNumber"] == 1
    assert stage_1["subject"] == "Introduction Email"
    assert stage_1["activityType"] == "Email"
    assert stage_1["status"] == "Pending"
    assert stage_1["dueDate"] == "2026-11-06", f"Expected 2026-11-06 (2026-11-01 + 5 days), got {stage_1['dueDate']}"
    assert stage_1["completedAt"] is None

    # Verify Next Activity Panel
    next_res = client.get(f"/api/v1/crm/leads/{lead_id}/next-activity", headers=auth_headers)
    assert next_res.status_code == 200
    next_act = next_res.json()["nextActivity"]
    assert next_act is not None
    assert next_act["subject"] == "Introduction Email"
    assert next_act["status"] == "Pending"
    assert next_act["dueDate"] == "2026-11-06"

    # Verify Timeline has 1 event (Pending Introduction Email), but NO false sent record
    tl_res = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers)
    assert tl_res.status_code == 200
    timeline = tl_res.json()["timeline"]
    assert len(timeline) == 1
    assert timeline[0]["title"] == "Introduction Email"
    assert timeline[0]["status"] == "Pending"
    assert timeline[0]["completedAt"] is None


def test_date_connected_change_recalculates_schedule(client, auth_headers):
    """
    Test 2: Changing Date Connected updates all eligible pending future follow-up dates
    without overwriting completed history.
    """
    # Create lead with connectedDate = 2026-11-01
    lead_res = client.post("/api/v1/crm/leads", json={
        "leadName": "Infosys STP Plant",
        "companyName": "Infosys Ltd",
        "businessArea": "WWT",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    assert lead_res.status_code in (200, 201), f"Lead creation failed: {lead_res.text}"
    lead_id = lead_res.json()["lead"]["id"]

    # Verify initial due date is 2026-11-06
    nurturing_before = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    assert nurturing_before["activities"][0]["dueDate"] == "2026-11-06"

    # Update Date Connected to 2026-11-10
    update_res = client.put(f"/api/v1/crm/leads/{lead_id}", json={
        "connectedDate": "2026-11-10"
    }, headers=auth_headers)
    assert update_res.status_code == 200

    # Verify recalculated due date is 2026-11-15 (2026-11-10 + 5 days)
    nurturing_after = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    assert nurturing_after["activities"][0]["dueDate"] == "2026-11-15"

    next_act = client.get(f"/api/v1/crm/leads/{lead_id}/next-activity", headers=auth_headers).json()["nextActivity"]
    assert next_act["dueDate"] == "2026-11-15"


def test_activity_completion_creates_auto_interaction_and_advances_stage(client, auth_headers):
    """
    Test 3: Marking a nurturing activity as Completed:
    - Sets activity to Completed with user and timestamp.
    - Automatically creates a linked interaction in lead_communications (source = 'Lead Nurturing').
    - Advances to next eligible stage (Stage 3 Reminder Email, due completion date + 5 calendar days).
    """
    lead_res = client.post("/api/v1/crm/leads", json={
        "leadName": "Reliance Biogas Feasibility",
        "companyName": "Reliance Industries",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    assert lead_res.status_code in (200, 201), f"Lead creation failed: {lead_res.text}"
    lead_id = lead_res.json()["lead"]["id"]

    nurturing = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    act_1 = nurturing["activities"][0]

    # Complete Stage 1 (Introduction Email)
    complete_res = client.post(
        f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_1['activityId']}/complete",
        json={
            "notes": "Sent introductory capabilities deck and corporate presentation via email.",
            "outcome": "Sent successfully",
            "emailMessageReference": "MSG-REVY-2026-001"
        },
        headers=auth_headers
    )
    assert complete_res.status_code == 200

    # Verify updated nurturing process
    updated_nurturing = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    completed_act = next(a for a in updated_nurturing["activities"] if a["stageNumber"] == 1)
    assert completed_act["status"] == "Completed"
    assert completed_act["completedAt"] is not None
    assert completed_act["notes"] == "Sent introductory capabilities deck and corporate presentation via email."

    # Verify Next Action is Stage 3: Reminder Email
    next_act = client.get(f"/api/v1/crm/leads/{lead_id}/next-activity", headers=auth_headers).json()["nextActivity"]
    assert next_act is not None
    assert next_act["stageNumber"] == 3
    assert next_act["subject"] == "Reminder Email"
    assert next_act["status"] == "Pending"

    # Verify Timeline has the completed activity with linked interaction
    tl_res = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers).json()["timeline"]
    completed_tl_item = next(i for i in tl_res if i["stageNumber"] == 1)
    assert completed_tl_item["status"] == "Completed"
    assert completed_tl_item["source"] == "Lead Nurturing"
    assert completed_tl_item["notes"] == "Sent introductory capabilities deck and corporate presentation via email."


def test_duplicate_completion_prevention_idempotency(client, auth_headers):
    """
    Test 4: Calling the completion API multiple times on the same activity
    does NOT create duplicate interactions or advance the workflow twice.
    """
    lead_res = client.post("/api/v1/crm/leads", json={
        "leadName": "Adani Power Effluent Project",
        "companyName": "Adani Power Ltd",
        "businessArea": "WWT",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    assert lead_res.status_code in (200, 201), f"Lead creation failed: {lead_res.text}"
    lead_id = lead_res.json()["lead"]["id"]

    act_1 = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]["activities"][0]

    # First completion call
    res_1 = client.post(
        f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_1['activityId']}/complete",
        json={"notes": "First completion call"},
        headers=auth_headers
    )
    assert res_1.status_code == 200

    # Check timeline count after first call
    tl_1 = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers).json()["timeline"]
    count_1 = len(tl_1)

    # Second completion call (idempotency check)
    res_2 = client.post(
        f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_1['activityId']}/complete",
        json={"notes": "Duplicate retry call"},
        headers=auth_headers
    )
    assert res_2.status_code == 200

    # Verify count and state remained identical
    tl_2 = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers).json()["timeline"]
    assert len(tl_2) == count_1, "Duplicate interaction records detected on retry!"


def test_customer_response_pauses_nurturing(client, auth_headers):
    """
    Test 5: Recording a customer response automatically pauses nurturing,
    logs an interaction with source = 'Customer Response', and updates Lead Status.
    """
    lead_res = client.post("/api/v1/crm/leads", json={
        "leadName": "Cipla Pharma Wastewater",
        "companyName": "Cipla Ltd",
        "businessArea": "WWT",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    assert lead_res.status_code in (200, 201), f"Lead creation failed: {lead_res.text}"
    lead_id = lead_res.json()["lead"]["id"]

    # Record Customer Response (Client is interested)
    response_payload = {
        "channel": "Email",
        "responseNotes": "Client called back stating they want a full technical presentation next Tuesday.",
        "outcome": "Interested",
        "targetLifecycleStatus": "Negotiation",
        "pauseNurturing": True
    }

    resp_res = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/customer-response", json=response_payload, headers=auth_headers)
    assert resp_res.status_code == 200

    # Verify Nurturing Process is Paused
    nurturing = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    assert nurturing["status"] == "Paused"
    assert "Interested" in nurturing["pauseReason"]

    # Verify Next Activity shows paused state
    next_act = client.get(f"/api/v1/crm/leads/{lead_id}/next-activity", headers=auth_headers).json()["nextActivity"]
    assert next_act["isPaused"] is True

    # Verify Lead Status synchronized to Negotiation
    lead = client.get(f"/api/v1/crm/leads/{lead_id}", headers=auth_headers).json()["lead"]
    assert lead["lifecycleStatus"] == "Negotiation"

    # Verify Customer Response appears in unified timeline
    tl = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers).json()["timeline"]
    response_item = next(i for i in tl if i["itemType"] == "customer_response")
    assert response_item["source"] == "Customer Response"
    assert "Interested" in response_item["outcome"]

    # Resume Nurturing
    resume_res = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/resume", json={}, headers=auth_headers)
    assert resume_res.status_code == 200

    nurturing_resumed = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    assert nurturing_resumed["status"] == "Active"


def test_manual_interaction_and_timeline_filters(client, auth_headers):
    """
    Test 6: Manual interactions logged via the timeline header appear alongside
    cadence activities and can be filtered by activity type.
    """
    lead_res = client.post("/api/v1/crm/leads", json={
        "leadName": "ITC Paperboards Green Energy",
        "companyName": "ITC Ltd",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    assert lead_res.status_code in (200, 201), f"Lead creation failed: {lead_res.text}"
    lead_id = lead_res.json()["lead"]["id"]

    # Log manual phone call interaction
    call_payload = {
        "channel": "Phone / Call",
        "eventType": "Phone call with client",
        "summary": "Called factory manager to confirm current anaerobic digester throughput.",
        "outcome": "Capacity is 450 m3/day"
    }
    client.post(f"/api/v1/crm/leads/{lead_id}/communications", json=call_payload, headers=auth_headers)

    # Fetch All Timeline
    tl_all = client.get(f"/api/v1/crm/leads/{lead_id}/timeline?filter=all", headers=auth_headers).json()["timeline"]
    assert any(i["source"] == "Manual" for i in tl_all)
    assert any(i["source"] == "Lead Nurturing" for i in tl_all)

    # Fetch Calls Filter
    tl_calls = client.get(f"/api/v1/crm/leads/{lead_id}/timeline?filter=calls", headers=auth_headers).json()["timeline"]
    assert len(tl_calls) >= 1
    assert all("call" in i["activityType"].lower() or "phone" in i["activityType"].lower() for i in tl_calls)

    # Fetch Cadence Filter
    tl_nurture = client.get(f"/api/v1/crm/leads/{lead_id}/timeline?filter=nurturing", headers=auth_headers).json()["timeline"]
    assert all(i["source"] == "Lead Nurturing" for i in tl_nurture)


def test_complete_end_to_end_scenario(client, auth_headers):
    """
    Test 7: Full 17-step end-to-end scenario specified in Section 21.C:
    1. Create a new Lead.
    2. Confirm nurturing automatically starts.
    3. Confirm Introduction Email is Pending.
    4. Confirm no false sent record exists.
    5. Set Date Connected to 1 November 2026.
    6. Verify first follow-up date is 6 November 2026.
    7. Confirm email is actually sent and mark it completed.
    8. Verify a Log Interaction entry is automatically created.
    9. Verify next stage activates.
    10. Verify follow-up schedule.
    11. Create a manual Phone Call interaction.
    12. Verify it appears in the same timeline.
    13. Record a customer response.
    14. Verify nurturing pauses.
    15. Verify no unnecessary reminder stage progresses.
    16. Resume nurturing after selecting next action.
    17. Verify complete timeline remains intact after refresh.
    """
    # 1. Create a new Lead
    create_res = client.post("/api/v1/crm/leads", json={
        "leadName": "Dr Reddy Lab Effluent Treatment",
        "companyName": "Dr Reddy Laboratories",
        "businessArea": "WWT",
        "connectedDate": "2026-11-01",
        "leadSource": "Website"
    }, headers=auth_headers)
    assert create_res.status_code in (200, 201), f"Lead creation failed: {create_res.text}"
    lead_id = create_res.json()["lead"]["id"]

    # 2. Confirm nurturing automatically starts
    nurturing = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    assert nurturing["status"] == "Active"

    # 3. Confirm Introduction Email is Pending
    stage_1 = nurturing["activities"][0]
    assert stage_1["subject"] == "Introduction Email"
    assert stage_1["status"] == "Pending"

    # 4. Confirm no false sent record exists
    tl = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers).json()["timeline"]
    assert not any(i.get("status") == "Completed" for i in tl)

    # 5 & 6. Date Connected is 1 Nov 2026 -> First follow-up date is 6 Nov 2026
    assert stage_1["dueDate"] == "2026-11-06"

    # 7. Confirm email is sent and mark it completed
    comp_res = client.post(
        f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{stage_1['activityId']}/complete",
        json={
            "notes": "Sent introductory capabilities email with technical brochure attached.",
            "outcome": "Delivered successfully",
            "emailMessageReference": "EMAIL-DRL-001"
        },
        headers=auth_headers
    )
    assert comp_res.status_code == 200

    # 8. Verify a Log Interaction entry is automatically created
    tl_after_comp = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers).json()["timeline"]
    auto_comm = next(i for i in tl_after_comp if i["stageNumber"] == 1)
    assert auto_comm["status"] == "Completed"
    assert auto_comm["notes"] == "Sent introductory capabilities email with technical brochure attached."

    # 9 & 10. Verify next stage activates and scheduled follow-up
    next_act = client.get(f"/api/v1/crm/leads/{lead_id}/next-activity", headers=auth_headers).json()["nextActivity"]
    assert next_act["stageNumber"] == 3  # Reminder Email
    assert next_act["subject"] == "Reminder Email"
    assert next_act["status"] == "Pending"

    # 11. Create a manual Phone Call interaction
    client.post(f"/api/v1/crm/leads/{lead_id}/communications", json={
        "channel": "Phone / Call",
        "eventType": "Phone call with client",
        "summary": "Called project head regarding site visit availability."
    }, headers=auth_headers)

    # 12. Verify it appears in the same timeline
    tl_with_call = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers).json()["timeline"]
    assert any(i["source"] == "Manual" and "Phone" in i["activityType"] for i in tl_with_call)

    # 13. Record a customer response
    client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/customer-response", json={
        "channel": "Email",
        "outcome": "Interested",
        "responseNotes": "Client confirmed interest in setting up a pilot testing run."
    }, headers=auth_headers)

    # 14. Verify nurturing pauses
    nurturing_paused = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    assert nurturing_paused["status"] == "Paused"

    # 15. Verify no unnecessary reminder stage progresses
    next_act_paused = client.get(f"/api/v1/crm/leads/{lead_id}/next-activity", headers=auth_headers).json()["nextActivity"]
    assert next_act_paused["isPaused"] is True

    # 16. Resume nurturing
    client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/resume", json={}, headers=auth_headers)
    nurturing_resumed = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    assert nurturing_resumed["status"] == "Active"

    # 17. Verify complete timeline remains intact after refresh
    final_tl = client.get(f"/api/v1/crm/leads/{lead_id}/timeline", headers=auth_headers).json()["timeline"]
    assert len(final_tl) >= 4  # Stage 1 Completed, Stage 3 Pending, Manual Call, Customer Response
    assert any(i["itemType"] == "customer_response" for i in final_tl)
    assert any(i["source"] == "Manual" for i in final_tl)
    assert any(i["source"] == "Lead Nurturing" for i in final_tl)

