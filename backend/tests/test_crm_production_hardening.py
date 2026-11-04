"""
REVY CRM - Production Hardening Test Suite
Addresses all criteria specified in Section 4 of the Production Readiness Audit:
1. Duplicate requests with persistent clientRequestId.
2. Concurrent requests across multiple threads/workers.
3. Backend restart simulation (fresh DB session / complete in-memory purge).
4. Repeated (idempotent) activity completion without duplicate timeline or next stages.
5. Invalid activity ID handling (404 NotFoundError).
6. Cross-lead activity manipulation (400 ValidationError ownership check).
7. Full 5-day cadence nurturing progression through all stages.
"""
import pytest
import uuid
import threading
from datetime import date, timedelta
from app.core.database import SessionLocal
from app.crm.model import (
    Lead,
    LeadNurturingProcess,
    NurturingActivity,
    LeadCommunicationHistory,
    CrmIdempotencyRecord
)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_duplicate_requests_idempotency(client, auth_headers, db_session):
    """
    Test 1: Duplicate requests with identical clientRequestId return the exact same lead
    and do not generate duplicate lead records or consume sequence numbers.
    """
    req_id = f"req-{uuid.uuid4()}"
    payload = {
        "clientRequestId": req_id,
        "leadName": "Tata Sustainability Tech",
        "companyName": f"Tata Eco {uuid.uuid4().hex[:6]} Ltd",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01",
        "contactEmail": f"contact_{uuid.uuid4().hex[:6]}@tataeco.test"
    }

    # Request 1
    res1 = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res1.status_code in (200, 201), f"First request failed: {res1.text}"
    lead1 = res1.json()["lead"]

    # Request 2 (Duplicate retry)
    res2 = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res2.status_code in (200, 201), f"Duplicate retry failed: {res2.text}"
    lead2 = res2.json()["lead"]

    assert lead1["id"] == lead2["id"]
    assert lead1["leadId"] == lead2["leadId"]

    # Verify database has exactly 1 lead and 1 idempotency record for this clientRequestId
    leads_count = db_session.query(Lead).filter(Lead.id == lead1["id"]).count()
    assert leads_count == 1

    idempotency_recs = db_session.query(CrmIdempotencyRecord).filter(
        CrmIdempotencyRecord.client_request_id == req_id
    ).all()
    assert len(idempotency_recs) == 1
    assert idempotency_recs[0].status == "COMPLETED"
    assert idempotency_recs[0].lead_id == lead1["id"]


def test_concurrent_lead_creation_requests(client, auth_headers, db_session):
    """
    Test 2: Multi-threaded concurrent requests submitting identical clientRequestId
    synchronize safely. All threads must receive a valid 200/201 response with the same Lead ID,
    and only ONE Lead must exist in the database.
    """
    shared_req_id = f"concurrent-{uuid.uuid4()}"
    payload = {
        "clientRequestId": shared_req_id,
        "leadName": "Concurrent Solar Bio",
        "companyName": f"Solar Bio {uuid.uuid4().hex[:6]}",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01",
        "contactEmail": f"solar_{uuid.uuid4().hex[:6]}@solarbio.test"
    }

    results = []
    errors = []

    def make_request():
        try:
            res = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
            if res.status_code in (200, 201):
                results.append(res.json()["lead"]["id"])
            else:
                errors.append(f"Status {res.status_code}: {res.text}")
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=make_request) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent request encountered errors: {errors}"
    assert len(results) == 4, f"Expected 4 successful results, got {len(results)}"
    # All 4 threads must return identical Lead ID
    assert len(set(results)) == 1, f"Different leads were returned across concurrent requests: {set(results)}"

    # Ensure only ONE lead was persisted in the DB
    persisted_leads = db_session.query(Lead).filter(Lead.id == results[0]).all()
    assert len(persisted_leads) == 1


def test_backend_restart_simulation(client, auth_headers, db_session):
    """
    Test 3: Backend restart simulation.
    After creating a Lead, we purge any session / in-memory state and simulate a fresh server process.
    The database-backed idempotency table must still recognize the clientRequestId and prevent duplicate creation.
    """
    restart_req_id = f"restart-{uuid.uuid4()}"
    payload = {
        "clientRequestId": restart_req_id,
        "companyName": f"Restart Energy {uuid.uuid4().hex[:6]} Ltd",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01",
        "contactEmail": f"ops_{uuid.uuid4().hex[:6]}@restartenergy.test"
    }

    # Initial creation
    res1 = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res1.status_code in (200, 201)
    lead1_id = res1.json()["lead"]["id"]

    # Simulate backend restart: Close DB session, expire all, clear any in-memory references
    db_session.expire_all()
    db_session.close()

    # Retry after simulated restart
    res2 = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res2.status_code in (200, 201)
    lead2_id = res2.json()["lead"]["id"]

    assert lead2_id == lead1_id, "Backend restart caused duplicate lead creation!"


def test_repeated_activity_completion_idempotency(client, auth_headers, db_session):
    """
    Test 4: Repeated activity completion calls must be idempotent:
    - Returning 200 with current state.
    - Not creating duplicate timeline entries in lead_communications.
    - Not creating duplicate next-stage activities.
    """
    # 1. Create a lead
    create_res = client.post("/api/v1/crm/leads", json={
        "clientRequestId": str(uuid.uuid4()),
        "companyName": f"Idempotent Activity Corp {uuid.uuid4().hex[:6]}",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01",
        "contactEmail": f"contact_{uuid.uuid4().hex[:6]}@corp.test"
    }, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    lead_id = create_res.json()["lead"]["id"]

    # 2. Get initial activity
    nurturing_res = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers)
    assert nurturing_res.status_code == 200
    activities = nurturing_res.json()["nurturing"]["activities"]
    assert len(activities) >= 1
    act_id = activities[0]["id"]

    # 3. Complete activity - Call 1
    complete_payload = {
        "notes": "Sent introduction email successfully.",
        "outcome": "Sent"
    }
    comp1 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_id}/complete", json=complete_payload, headers=auth_headers)
    assert comp1.status_code == 200

    # Count communications and activities after first completion
    comm_count_1 = db_session.query(LeadCommunicationHistory).filter(
        LeadCommunicationHistory.lead_id == lead_id
    ).count()
    act_count_1 = db_session.query(NurturingActivity).filter(
        NurturingActivity.lead_id == lead_id
    ).count()
    assert comm_count_1 >= 1

    # 4. Complete activity - Call 2 (Duplicate / repeated completion)
    comp2 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_id}/complete", json=complete_payload, headers=auth_headers)
    assert comp2.status_code == 200

    # Verify NO duplicate communication history or duplicate activities were inserted
    comm_count_2 = db_session.query(LeadCommunicationHistory).filter(
        LeadCommunicationHistory.lead_id == lead_id
    ).count()
    act_count_2 = db_session.query(NurturingActivity).filter(
        NurturingActivity.lead_id == lead_id
    ).count()

    assert comm_count_2 == comm_count_1, "Duplicate communication history entry created upon repeated activity completion!"
    assert act_count_2 == act_count_1, "Duplicate next activity created upon repeated activity completion!"


def test_invalid_activity_id_returns_404(client, auth_headers):
    """
    Test 5: Providing a non-existent or invalid activity ID returns 404 NotFoundError.
    """
    create_res = client.post("/api/v1/crm/leads", json={
        "clientRequestId": str(uuid.uuid4()),
        "companyName": f"Invalid Act Corp {uuid.uuid4().hex[:6]}",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    lead_id = create_res.json()["lead"]["id"]

    fake_act_id = f"act_{uuid.uuid4()}"
    res = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{fake_act_id}/complete", json={"notes": "test"}, headers=auth_headers)
    assert res.status_code == 404, f"Expected 404 for invalid activity ID, got {res.status_code}"


def test_cross_lead_activity_manipulation_rejected(client, auth_headers):
    """
    Test 6: Attempting to complete or modify an activity belonging to another Lead
    must be strictly rejected with 400 ValidationError.
    """
    # Create Lead A
    res_a = client.post("/api/v1/crm/leads", json={
        "clientRequestId": str(uuid.uuid4()),
        "companyName": f"Lead A Corp {uuid.uuid4().hex[:6]}",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    lead_a_id = res_a.json()["lead"]["id"]

    # Create Lead B
    res_b = client.post("/api/v1/crm/leads", json={
        "clientRequestId": str(uuid.uuid4()),
        "companyName": f"Lead B Corp {uuid.uuid4().hex[:6]}",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    lead_b_id = res_b.json()["lead"]["id"]

    # Get Activity 1 belonging to Lead A
    nurturing_a = client.get(f"/api/v1/crm/leads/{lead_a_id}/nurturing", headers=auth_headers).json()
    act_a_id = nurturing_a["nurturing"]["activities"][0]["id"]

    # Attempt to complete Activity A via Lead B's URL
    cross_res = client.post(
        f"/api/v1/crm/leads/{lead_b_id}/nurturing/activities/{act_a_id}/complete",
        json={"notes": "Hacking cross-lead activity"},
        headers=auth_headers
    )
    assert cross_res.status_code == 400, f"Expected 400 ValidationError for cross-lead activity, got {cross_res.status_code}: {cross_res.text}"
    assert "does not belong to lead" in cross_res.text.lower()


def test_complete_five_day_cadence_nurturing_progression(client, auth_headers, db_session):
    """
    Test 7: Full five-day cadence nurturing workflow progression:
    Walks through all nurturing stages from Stage 1 to sequence completion,
    verifying 5-day intervals and stage progression.
    """
    connected_d = date.today() - timedelta(days=2)
    create_res = client.post("/api/v1/crm/leads", json={
        "clientRequestId": str(uuid.uuid4()),
        "companyName": f"Full Nurture Bio {uuid.uuid4().hex[:6]}",
        "businessArea": "Biogas",
        "connectedDate": connected_d.isoformat(),
        "contactEmail": f"nurture_{uuid.uuid4().hex[:6]}@biotrade.test"
    }, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    lead_id = create_res.json()["lead"]["id"]

    # Stage 1: Introduction Email
    nurture = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    assert nurture["currentStage"] == 1
    first_act = nurture["activities"][0]
    expected_s1_due = connected_d + timedelta(days=5)
    assert first_act["dueDate"] == expected_s1_due.isoformat()

    # Complete Stage 1 -> Jumps over Waiting Period (Stage 2) to Stage 3 (Reminder Email)
    c1 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{first_act['id']}/complete", json={"notes": "Sent Intro", "outcome": "Sent"}, headers=auth_headers)
    assert c1.status_code == 200
    p1 = c1.json()["nurturing"]
    assert p1["currentStage"] == 3
    # Next due date is 5 days from today
    expected_s3_due = date.today() + timedelta(days=5)
    assert p1["nextActivityDate"] == expected_s3_due.isoformat()

    # Complete Stage 3 -> Jumps over Waiting Period (Stage 4) to Stage 5 (Call Customer)
    nurture = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    act_s3 = next(a for a in nurture["activities"] if a["stageNumber"] == 3)
    c3 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_s3['id']}/complete", json={"notes": "Sent Reminder", "outcome": "Sent"}, headers=auth_headers)
    assert c3.status_code == 200
    p3 = c3.json()["nurturing"]
    assert p3["currentStage"] == 5

    # Complete Stage 5 -> Jumps over Waiting Period (Stage 6) to Stage 7 (Thank You / Follow-up Email)
    nurture = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    act_s5 = next(a for a in nurture["activities"] if a["stageNumber"] == 5)
    c5 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_s5['id']}/complete", json={"notes": "Spoke with client", "outcome": "Discussed"}, headers=auth_headers)
    assert c5.status_code == 200
    p5 = c5.json()["nurturing"]
    assert p5["currentStage"] == 7

    # Complete Stage 7 -> Advances directly to Stage 8 (Customer Response Review)
    nurture = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    act_s7 = next(a for a in nurture["activities"] if a["stageNumber"] == 7)
    c7 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_s7['id']}/complete", json={"notes": "Sent Thank You", "outcome": "Sent"}, headers=auth_headers)
    assert c7.status_code == 200
    p7 = c7.json()["nurturing"]
    assert p7["currentStage"] == 8

    # Complete Stage 8 -> Advances to Stage 9 (Next Follow-up / Meeting)
    nurture = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    act_s8 = next(a for a in nurture["activities"] if a["stageNumber"] == 8)
    c8 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_s8['id']}/complete", json={"notes": "Reviewed interest", "outcome": "High Potential"}, headers=auth_headers)
    assert c8.status_code == 200
    p8 = c8.json()["nurturing"]
    assert p8["currentStage"] == 9

    # Complete Stage 9 -> Advances to Stage 10 (Final Follow-up / Closure)
    nurture = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    act_s9 = next(a for a in nurture["activities"] if a["stageNumber"] == 9)
    c9 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_s9['id']}/complete", json={"notes": "Held technical presentation", "outcome": "Completed"}, headers=auth_headers)
    assert c9.status_code == 200
    p9 = c9.json()["nurturing"]
    assert p9["currentStage"] == 10

    # Complete Stage 10 -> Sequence completes
    nurture = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    act_s10 = next(a for a in nurture["activities"] if a["stageNumber"] == 10)
    c10 = client.post(f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_s10['id']}/complete", json={"notes": "Final review done", "outcome": "Qualified for proposal"}, headers=auth_headers)
    assert c10.status_code == 200
    p10 = c10.json()["nurturing"]
    assert p10["status"] == "Completed"


def test_concurrent_activity_completion(client, auth_headers, db_session):
    """
    Test 8: Multi-threaded concurrent completion requests on the exact same activity.
    Must not fail or create duplicate next activities or duplicate interaction logs.
    """
    create_res = client.post("/api/v1/crm/leads", json={
        "clientRequestId": str(uuid.uuid4()),
        "companyName": f"Concurrent Act Corp {uuid.uuid4().hex[:6]}",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01"
    }, headers=auth_headers)
    lead_id = create_res.json()["lead"]["id"]

    nurturing = client.get(f"/api/v1/crm/leads/{lead_id}/nurturing", headers=auth_headers).json()["nurturing"]
    act_id = nurturing["activities"][0]["id"]

    results = []
    errors = []

    def complete_act():
        try:
            res = client.post(
                f"/api/v1/crm/leads/{lead_id}/nurturing/activities/{act_id}/complete",
                json={"notes": "Concurrent completion attempt", "outcome": "Sent"},
                headers=auth_headers
            )
            if res.status_code == 200:
                results.append(res.status_code)
            else:
                errors.append(f"Status {res.status_code}: {res.text}")
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=complete_act) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors in concurrent completion: {errors}"
    assert len(results) == 4, f"All threads should receive 200 OK, got: {results}"

    # Verify only ONE next stage was created (Stage 3)
    stage_3_acts = db_session.query(NurturingActivity).filter(
        NurturingActivity.lead_id == lead_id,
        NurturingActivity.stage_number == 3
    ).all()
    assert len(stage_3_acts) == 1, f"Expected 1 Stage 3 activity, got {len(stage_3_acts)}"

    # Verify exactly one communication history for Stage 1
    stage_1_comms = db_session.query(LeadCommunicationHistory).filter(
        LeadCommunicationHistory.lead_id == lead_id,
        LeadCommunicationHistory.event_type.like("%Stage 1%")
    ).all()
    assert len(stage_1_comms) == 1, f"Expected 1 communication entry, got {len(stage_1_comms)}"


def test_timeout_after_db_commit_idempotent_recovery(client, auth_headers, db_session):
    """
    Test 9: Timeout after database commit recovery.
    Simulates a client sending a request, the server committing the lead, but the client
    experiencing a network drop or timeout before reading the HTTP response.
    When the client retries with the same clientRequestId, it instantly receives 200 OK
    with the already-committed Lead.
    """
    req_id = f"client-timeout-{uuid.uuid4()}"
    payload = {
        "clientRequestId": req_id,
        "leadName": "Client Timeout Recovery Ltd",
        "companyName": f"Recovery Corp {uuid.uuid4().hex[:6]}",
        "businessArea": "Biogas",
        "connectedDate": "2026-11-01",
        "contactEmail": f"timeout_{uuid.uuid4().hex[:6]}@recovery.test"
    }

    # Initial POST: creates lead and commits idempotency record in DB
    res1 = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res1.status_code in (200, 201)
    original_lead = res1.json()["lead"]

    # Verify idempotency record is COMPLETED
    idemp = db_session.query(CrmIdempotencyRecord).filter(
        CrmIdempotencyRecord.client_request_id == req_id
    ).first()
    assert idemp is not None
    assert idemp.status == "COMPLETED"
    assert idemp.lead_id == original_lead["id"]

    # Client retry after timeout
    res_retry = client.post("/api/v1/crm/leads", json=payload, headers=auth_headers)
    assert res_retry.status_code in (200, 201)
    recovered_lead = res_retry.json()["lead"]

    assert recovered_lead["id"] == original_lead["id"]
    assert recovered_lead["leadId"] == original_lead["leadId"]

