import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, date
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.crm.model import Account, Contact, Lead, Opportunity
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_phase3_env(setup_crm_stage4_environment):
    return get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")


def test_1_and_6_qualification_existing_account_and_existing_contact(setup_phase3_env):
    """
    Test 1, 5, 6: Qualification using an existing Account and existing Contact.
    Verifies Opportunity creation, designated Primary Contact, and correct bidirectional relationships.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    # 1. Create Account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Reliance Bio Refining {uid}",
        "industry": "Biofuels",
        "website": f"https://www.reliance-bio-{uid}.com"
    }, headers=headers)
    assert acc_res.status_code == 201
    account = acc_res.json()["account"]

    # 2. Create Contact under Account
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Kailash Sharma {uid}",
        "email": f"kailash_{uid}@reliancebio.com",
        "mobileNumber": f"+9198{uuid.uuid4().int % 100000000:08d}",
        "designation": "VP Operations",
        "accountId": account["id"]
    }, headers=headers)
    assert con_res.status_code == 201
    contact = con_res.json()["contact"]

    # 3. Create Open Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Biofuel Refining Facility Phase 1 {uid}",
        "companyName": f"Reliance Bio Refining {uid}",
        "contactEmail": f"kailash_{uid}@reliancebio.com",
        "businessArea": "Biogas",
        "leadSource": "In-Person Meeting",
        "contactMethods": ["Meeting", "Email"]
    }, headers=headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]

    # 4. Qualify Lead reusing existing Account and Contact
    qualify_payload = {
        "account": {
            "action": "reuse",
            "accountId": account["id"]
        },
        "contact": {
            "action": "reuse",
            "contactId": contact["id"]
        },
        "opportunityName": f"Refinery Expansion OPP {uid}",
        "estimatedValue": 1250000.0,
        "opportunityDescription": "Installation of high-rate biomethanation digesters.",
        "clientStatus": "Existing"
    }
    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=headers)
    assert q_res.status_code == 200
    data = q_res.json()
    assert data["success"] is True

    # Validate resulting entities
    opp = data["opportunity"]
    assert opp["opportunityId"].startswith("OPP-")
    assert opp["name"] == f"Refinery Expansion OPP {uid}"
    assert opp["accountId"] == account["id"]
    assert opp["contactId"] == contact["id"]  # Designated Primary Contact
    assert opp["originatingLeadId"] == lead["id"]
    assert opp["estimatedValue"] == 1250000.0

    # Validate Lead lifecycle update
    q_lead = data["lead"]
    assert q_lead["lifecycleStatus"] == "Qualified"
    assert q_lead["opportunityId"] == opp["id"]
    assert q_lead["accountId"] == account["id"]
    assert q_lead["contactId"] == contact["id"]
    assert q_lead["clientStatus"] == "Existing"


def test_2_and_7_qualification_new_account_and_new_contact(setup_phase3_env):
    """
    Test 2 & 7: Qualification using a newly created Account and Contact.
    Verifies creation from prefilled Lead data and correct qualification metadata.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    # Create Lead with rich company and contact information
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Effluent Treatment Modernization {uid}",
        "companyName": f"Adani Port Utilities {uid}",
        "firstName": "Siddharth",
        "lastName": "Mehta",
        "jobTitle": "Chief Engineer",
        "contactEmail": f"siddharth_{uid}@adaniutilities.com",
        "mobilePhone": "+91 98234 56789",
        "websiteLink": f"https://www.adaniports-{uid}.com",
        "location": "Mundra, Gujarat",
        "industry": "Ports & SEZ",
        "businessArea": "WWT",
        "currency": "INR",
        "requirementTypes": ["Consulting", "Product"],
        "leadSource": "Referral"
    }, headers=headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]

    # Qualify creating both new Account and new Contact
    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"Adani Port Utilities Ltd {uid}",
            "industry": "Ports & Infrastructure",
            "website": f"https://www.adaniports-{uid}.com",
            "address": "Mundra, Gujarat"
        },
        "contact": {
            "action": "create",
            "name": "Siddharth Mehta",
            "email": f"siddharth_{uid}@adaniutilities.com",
            "mobileNumber": "+91 98234 56789",
            "designation": "Chief Engineer"
        },
        "opportunityName": f"Mundra WWT Upgrade {uid}",
        "estimatedValue": 3500000.0,
        "clientStatus": "New"
    }
    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=headers)
    assert q_res.status_code == 200
    data = q_res.json()

    # Verify newly created Account and Contact
    acc = data["account"]
    con = data["contact"]
    opp = data["opportunity"]
    assert acc["id"] is not None
    assert acc["accountId"].startswith("ACC-")
    assert acc["name"] == f"Adani Port Utilities Ltd {uid}"

    assert con["id"] is not None
    assert con["contactId"].startswith("CON-")
    assert con["name"] == "Siddharth Mehta"

    # Verify Opportunity is linked to new Account and Contact
    assert opp["accountId"] == acc["id"]
    assert opp["contactId"] == con["id"]

    # Verify Lead metadata
    q_lead = data["lead"]
    assert q_lead["lifecycleStatus"] == "Qualified"
    assert q_lead["qualifiedAt"] is not None
    assert q_lead["qualifiedById"] is not None


def test_3_qualification_existing_account_and_new_contact(setup_phase3_env):
    """
    Test 3: Qualification using an existing Account and a new Contact.
    Verifies that the new Contact is automatically associated with the selected Account.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    # Create Account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"JSW Green Energy {uid}",
        "industry": "Steel & Renewables"
    }, headers=headers)
    account = acc_res.json()["account"]

    # Create Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Steel Mill Sludge Bio Treatment {uid}",
        "companyName": account["name"],
        "firstName": "Pooja",
        "lastName": "Verma",
        "contactEmail": f"pooja_{uid}@jswgreen.in",
        "businessArea": "Biogas"
    }, headers=headers)
    lead = lead_res.json()["lead"]

    # Qualify: reuse Account, create new Contact
    qualify_payload = {
        "account": {
            "action": "reuse",
            "accountId": account["id"]
        },
        "contact": {
            "action": "create",
            "name": f"Pooja Verma {uid}",
            "email": f"pooja_{uid}@jswgreen.in",
            "mobileNumber": "+91 97111 22233",
            "designation": "Environmental Officer"
        },
        "opportunityName": f"JSW Sludge Project {uid}"
    }
    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=headers)
    assert q_res.status_code == 200
    data = q_res.json()
    con = data["contact"]
    assert con["contactId"].startswith("CON-")

    # Verify in DB that the new contact belongs to the existing account
    with SessionLocal() as db:
        saved_con = db.query(Contact).filter(Contact.id == con["id"]).first()
        assert saved_con.account_id == account["id"]


def test_4_qualification_new_account_and_unassigned_contact(setup_phase3_env):
    """
    Test 4: Qualification using a new Account and an existing unassigned Contact.
    Verifies that the unassigned Contact is linked to the newly created Account.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    # Create independent contact without account
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Independent Consultant {uid}",
        "email": f"consultant_{uid}@freelance.org",
        "mobileNumber": f"+9196{uuid.uuid4().int % 100000000:08d}"
    }, headers=headers)
    contact = con_res.json()["contact"]
    assert contact["accountId"] is None

    # Create Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"New Bio Facility {uid}",
        "companyName": f"Emerging CleanTech {uid}"
    }, headers=headers)
    lead = lead_res.json()["lead"]

    # Qualify: create new Account, reuse existing Contact
    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"Emerging CleanTech Corp {uid}"
        },
        "contact": {
            "action": "reuse",
            "contactId": contact["id"]
        },
        "opportunityName": f"Emerging Tech Bio Project {uid}"
    }
    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=headers)
    assert q_res.status_code == 200
    data = q_res.json()
    new_acc = data["account"]

    # Verify that contact is now linked to the newly created account
    with SessionLocal() as db:
        updated_con = db.query(Contact).filter(Contact.id == contact["id"]).first()
        assert updated_con.account_id == new_acc["id"]


def test_8_preservation_of_lead_enquiry_details_and_communication_history(setup_phase3_env):
    """
    Test 8: Preserves original Lead enquiry details, requirement types, and communication history.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    # Create lead with detailed specifications
    lead_payload = {
        "topic": f"High COD Distillery Wastewater {uid}",
        "firstName": "Arun",
        "lastName": "Joshi",
        "companyName": f"Joshi Distilleries {uid}",
        "contactEmail": f"arun_{uid}@joshidistill.com",
        "mobilePhone": "+91 99880 11223",
        "websiteLink": f"https://www.joshidistill-{uid}.com",
        "description": "Distillery with 80,000 ppm COD requiring UASB biomethanation.",
        "businessArea": "Biogas",
        "leadSource": "Trade Show / Expo",
        "requirementTypes": ["Product", "Sample Testing", "Consulting"],
        "contactMethods": ["Meeting", "Email"]
    }
    lead_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]

    # Add Communication History to Lead
    comm_payload = {
        "channel": "Phone",
        "eventType": "Initial Discovery Call",
        "summary": "Discussed effluent characteristics and sample delivery timeline.",
        "outcome": "Client agreed to send 5L effluent sample for lab analysis."
    }
    comm_res = client.post(f"/api/v1/crm/leads/{lead['id']}/communications", json=comm_payload, headers=headers)
    assert comm_res.status_code == 201
    comm = comm_res.json()["communication"]

    # Qualify Lead
    qualify_payload = {
        "account": {"action": "create", "name": f"Joshi Distilleries {uid}"},
        "contact": {"action": "create", "name": "Arun Joshi", "email": f"arun_{uid}@joshidistill.com"},
        "opportunityName": f"Joshi Distillery UASB {uid}"
    }
    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=headers)
    assert q_res.status_code == 200

    # Retrieve Lead and verify ALL original enquiry details & communications are intact
    get_lead_res = client.get(f"/api/v1/crm/leads/{lead['id']}", headers=headers)
    assert get_lead_res.status_code == 200
    q_lead = get_lead_res.json()["lead"]
    assert q_lead["leadName"] == f"High COD Distillery Wastewater {uid}"
    assert q_lead["description"] == "Distillery with 80,000 ppm COD requiring UASB biomethanation."
    assert q_lead["companyName"] == f"Joshi Distilleries {uid}"
    assert q_lead["contactEmail"] == f"arun_{uid}@joshidistill.com"
    assert q_lead["businessArea"] == "Biogas"
    assert q_lead["leadSource"] == "Trade Show / Expo"
    assert set(q_lead["requirementTypes"]) == {"Product", "Sample Testing", "Consulting"}

    # Verify communication history is preserved
    comm_list_res = client.get(f"/api/v1/crm/leads/{lead['id']}/communications", headers=headers)
    assert comm_list_res.status_code == 200
    comms = comm_list_res.json()["communications"]
    assert any(c["id"] == comm["id"] for c in comms)


def test_9_10_11_rollback_atomicity_on_failure(setup_phase3_env):
    """
    Test 9, 10, 11: Transaction atomicity and rollback.
    When any step (e.g. invalid contact, missing primary contact, or relationship violation) fails,
    the entire transaction is rolled back and NO orphaned Account, Contact, or Opportunity records remain.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Failed Qualification Lead {uid}",
        "companyName": f"Ghost Energy {uid}"
    }, headers=headers)
    lead = lead_res.json()["lead"]

    # Attempt qualification with missing primary contact action/name -> validation fails
    invalid_payload = {
        "account": {
            "action": "create",
            "name": f"Ghost Energy Corp {uid}"
        },
        "contact": {
            "action": "create",
            "name": "   "  # Invalid empty contact name
        },
        "opportunityName": f"Ghost Opp {uid}"
    }
    res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=invalid_payload, headers=headers)
    assert res.status_code in (400, 422)

    # Verify that Ghost Energy Corp was ROLLED BACK and does NOT exist in the database
    with SessionLocal() as db:
        acc = db.query(Account).filter(Account.name == f"Ghost Energy Corp {uid}").first()
        assert acc is None, "Account should not exist because qualification rolled back!"

        # Verify lead status was NOT changed to Qualified
        db_lead = db.query(Lead).filter(Lead.id == lead["id"]).first()
        assert db_lead.lifecycle_status == "Open"
        assert db_lead.opportunity_id is None


def test_12_and_13_idempotency_retry_after_successful_commit(setup_phase3_env):
    """
    Test 12 & 13: Retry after successful commit returns existing qualification result idempotently
    without creating a second Opportunity.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Idempotency Test Lead {uid}",
        "companyName": f"Idempotent Solutions {uid}",
        "contactEmail": f"info_{uid}@idempotent.com"
    }, headers=headers)
    lead = lead_res.json()["lead"]

    payload = {
        "account": {"action": "create", "name": f"Idempotent Solutions {uid}"},
        "contact": {"action": "create", "name": f"Idempotent Contact {uid}", "email": f"info_{uid}@idempotent.com"},
        "opportunityName": f"Opportunity One {uid}"
    }

    # 1. First qualification call
    res1 = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=payload, headers=headers)
    assert res1.status_code == 200
    first_opp = res1.json()["opportunity"]

    # 2. Second qualification call (retry or double-click simulation)
    res2 = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=payload, headers=headers)
    assert res2.status_code == 200
    second_opp = res2.json()["opportunity"]

    # Must return the SAME opportunity
    assert first_opp["id"] == second_opp["id"]
    assert first_opp["opportunityId"] == second_opp["opportunityId"]
    assert "already qualified" in res2.json()["message"]

    # Verify in DB that only 1 Opportunity exists linked to this lead
    with SessionLocal() as db:
        opp_count = db.query(Opportunity).filter(Opportunity.originating_lead_id == lead["id"]).count()
        assert opp_count == 1


def test_14_concurrent_qualification_attempts_for_same_lead(setup_phase3_env):
    """
    Test 14: Two concurrent qualification requests for the same Lead.
    Row locking ensures exactly one Opportunity is created.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Concurrency Test Lead {uid}",
        "companyName": f"Concurrent Bio Corp {uid}",
        "contactEmail": f"contact_{uid}@concurrent.com"
    }, headers=headers)
    lead = lead_res.json()["lead"]

    payload = {
        "account": {"action": "create", "name": f"Concurrent Bio Corp {uid}"},
        "contact": {"action": "create", "name": f"Concurrent Agent {uid}", "email": f"contact_{uid}@concurrent.com"},
        "opportunityName": f"Concurrent Opportunity {uid}"
    }

    def do_qualify():
        return client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=payload, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_qualify)
        f2 = executor.submit(do_qualify)
        r1 = f1.result()
        r2 = f2.result()

    # Both requests should return HTTP 200 (one created, the other returned idempotent result)
    assert r1.status_code == 200
    assert r2.status_code == 200

    opp1_id = r1.json()["opportunity"]["id"]
    opp2_id = r2.json()["opportunity"]["id"]
    assert opp1_id == opp2_id, "Concurrent requests must resolve to the exact same Opportunity!"

    with SessionLocal() as db:
        opp_count = db.query(Opportunity).filter(Opportunity.originating_lead_id == lead["id"]).count()
        assert opp_count == 1


def test_15_rejection_of_invalid_lifecycle_transitions(setup_phase3_env):
    """
    Test 15: Rejection of invalid lifecycle transitions (e.g. attempting to qualify a Disqualified Lead).
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    # Create Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Disqualified Test Lead {uid}",
        "companyName": f"Declined Corp {uid}"
    }, headers=headers)
    lead = lead_res.json()["lead"]

    # Transition Lead to Disqualified
    disq_res = client.post(f"/api/v1/crm/leads/{lead['id']}/status", json={
        "status": "Disqualified",
        "remarks": "Project abandoned by client."
    }, headers=headers)
    assert disq_res.status_code == 200
    assert disq_res.json()["lead"]["lifecycleStatus"] == "Disqualified"

    # Attempt to qualify Disqualified Lead -> rejected
    qualify_payload = {
        "account": {"action": "create", "name": f"Declined Corp {uid}"},
        "contact": {"action": "create", "name": "Declined Person"},
        "opportunityName": "Invalid Opp"
    }
    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=headers)
    assert q_res.status_code == 400
    err_text = q_res.json().get("message") or q_res.json().get("detail", "")
    assert "Disqualified" in err_text


def test_16_rejection_of_unauthorized_qualification_attempts():
    """
    Test 16: Rejection of unauthorized qualification attempts (no token or forbidden role).
    """
    # 1. No token -> 401/403
    res_no_auth = client.post("/api/v1/crm/leads/any-lead-id/qualify", json={
        "account": {"action": "create", "name": "Hack Corp"}
    })
    assert res_no_auth.status_code in (401, 403)

    # 2. Invalid / Non-CRM token -> 401/403
    fake_headers = {"Authorization": "Bearer bad.token.value"}
    res_fake = client.post("/api/v1/crm/leads/any-lead-id/qualify", json={
        "account": {"action": "create", "name": "Hack Corp"}
    }, headers=fake_headers)
    assert res_fake.status_code in (401, 403)


def test_17_contact_account_mismatch_rejection(setup_phase3_env):
    """
    Test 17: Contact/Account mismatch handling.
    Reject qualifying with a Contact that belongs to another Account.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    # Create Account A and Contact A
    acc_a_res = client.post("/api/v1/crm/accounts", json={"name": f"Account A {uid}"}, headers=headers)
    acc_a = acc_a_res.json()["account"]

    con_a_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Contact A {uid}",
        "accountId": acc_a["id"]
    }, headers=headers)
    con_a = con_a_res.json()["contact"]

    # Create Account B
    acc_b_res = client.post("/api/v1/crm/accounts", json={"name": f"Account B {uid}"}, headers=headers)
    acc_b = acc_b_res.json()["account"]

    # Create Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Mismatch Lead {uid}",
        "companyName": f"Account B {uid}"
    }, headers=headers)
    lead = lead_res.json()["lead"]

    # Attempt to qualify Lead with Account B but Contact A -> rejected!
    mismatch_payload = {
        "account": {
            "action": "reuse",
            "accountId": acc_b["id"]
        },
        "contact": {
            "action": "reuse",
            "contactId": con_a["id"]
        },
        "opportunityName": f"Mismatch Opp {uid}"
    }
    res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=mismatch_payload, headers=headers)
    assert res.status_code == 400
    err_text = res.json().get("message") or res.json().get("detail", "")
    assert "different Account" in err_text


def test_18_potential_duplicate_matches_surfaced(setup_phase3_env):
    """
    Test 18: Potential duplicate matches surfaced by qualification-matches endpoint.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]
    comp_name = f"Bharat Bio Fuel {uid}"
    comp_email = f"info@{uid}.bharatbio.com"

    # Create existing account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": comp_name,
        "email": comp_email
    }, headers=headers)
    assert acc_res.status_code == 201

    # Create Lead matching that company
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Biofuel Enquiry {uid}",
        "companyName": comp_name,
        "companyEmail": comp_email
    }, headers=headers)
    lead = lead_res.json()["lead"]

    # Query matches endpoint
    match_res = client.get(f"/api/v1/crm/leads/{lead['id']}/qualification-matches", headers=headers)
    assert match_res.status_code == 200
    data = match_res.json()
    assert len(data["matchingAccounts"]) >= 1
    assert data["suggestedAccount"] is not None
    assert data["suggestedClientStatus"] == "Existing"


def test_19_existing_account_and_contact_data_preserved(setup_phase3_env):
    """
    Test 19: Reusing existing Account and Contact preserves their existing data without silent overwrite.
    """
    headers = setup_phase3_env
    uid = uuid.uuid4().hex[:8]

    # Create Account with specific phone and address
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Preserved Industries {uid}",
        "phone": "+91 22 1234 5678",
        "address": "Original Head Office, Mumbai"
    }, headers=headers)
    account = acc_res.json()["account"]

    # Create Contact with specific designation
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Prakash Rao {uid}",
        "designation": "Executive Director",
        "accountId": account["id"]
    }, headers=headers)
    contact = con_res.json()["contact"]

    # Create Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"New Project {uid}",
        "companyName": account["name"]
    }, headers=headers)
    lead = lead_res.json()["lead"]

    # Qualify reusing Account and Contact
    q_payload = {
        "account": {"action": "reuse", "accountId": account["id"]},
        "contact": {"action": "reuse", "contactId": contact["id"]},
        "opportunityName": f"Preserved Opp {uid}"
    }
    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=q_payload, headers=headers)
    assert q_res.status_code == 200

    # Verify Account & Contact remain intact in database
    with SessionLocal() as db:
        acc_db = db.query(Account).filter(Account.id == account["id"]).first()
        con_db = db.query(Contact).filter(Contact.id == contact["id"]).first()
        assert acc_db.phone == "+91 22 1234 5678"
        assert acc_db.address == "Original Head Office, Mumbai"
        assert con_db.designation == "Executive Director"
