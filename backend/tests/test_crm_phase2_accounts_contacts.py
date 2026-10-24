import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.crm.model import Account, Contact, Lead, Opportunity
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_phase2_env(setup_crm_stage4_environment):
    return get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")


def test_authorized_account_lifecycle(setup_phase2_env):
    """
    Test 1 & 5: Authorized Account creation, retrieval, editing, validation, and independent creation without a Lead.
    """
    headers = setup_phase2_env
    uid = uuid.uuid4().hex[:8]

    # Validation test: empty name rejected
    bad_res = client.post("/api/v1/crm/accounts", json={"name": "   "}, headers=headers)
    assert bad_res.status_code in (400, 422)

    # Create account
    create_payload = {
        "name": f"Praj Bioprocess Solutions {uid}",
        "industry": "Bioenergy",
        "website": f"praj-bioprocess-{uid}.com",
        "phone": "+91 20 7180 2000",
        "email": f"info@{uid}.praj.net",
        "address": "Bavdhan Industrial Estate, Pune"
    }
    create_res = client.post("/api/v1/crm/accounts", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    account = create_res.json()["account"]
    acc_id = account["id"]
    assert account["accountId"].startswith("ACC-")
    assert account["name"] == f"Praj Bioprocess Solutions {uid}"
    assert account["contactCount"] == 0
    assert account["leadCount"] == 0

    # Retrieve account details
    get_res = client.get(f"/api/v1/crm/accounts/{acc_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["success"] is True
    assert detail["account"]["id"] == acc_id
    assert "contacts" in detail
    assert "leads" in detail
    assert "opportunities" in detail

    # Update account
    update_payload = {
        "name": f"Praj Bioprocess Solutions International {uid}",
        "industry": "Renewables & Bio-Hydrogen",
        "phone": "+91 20 7180 2999"
    }
    update_res = client.put(f"/api/v1/crm/accounts/{acc_id}", json=update_payload, headers=headers)
    assert update_res.status_code == 200
    updated_acc = update_res.json()["account"]
    assert updated_acc["name"] == f"Praj Bioprocess Solutions International {uid}"
    assert updated_acc["industry"] == "Renewables & Bio-Hydrogen"
    assert updated_acc["phone"] == "+91 20 7180 2999"


def test_authorized_contact_lifecycle(setup_phase2_env):
    """
    Test 2 & 3: Authorized Contact creation, retrieval, editing, validation, and creation without an Account.
    """
    headers = setup_phase2_env
    uid = uuid.uuid4().hex[:8]

    # Validation: empty name rejected
    bad_res = client.post("/api/v1/crm/contacts", json={"name": "   "}, headers=headers)
    assert bad_res.status_code in (400, 422)

    # Create independent contact without account
    create_payload = {
        "name": f"Dr. Vikram Sarabhai {uid}",
        "designation": "Chief Scientist",
        "email": f"vikram_{uid}@science.res.in",
        "mobileNumber": f"+9198{uuid.uuid4().int % 100000000:08d}"
    }
    create_res = client.post("/api/v1/crm/contacts", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    contact = create_res.json()["contact"]
    con_id = contact["id"]
    assert contact["contactId"].startswith("CON-")
    assert contact["accountId"] is None
    assert contact["accountName"] is None

    # Retrieve contact
    get_res = client.get(f"/api/v1/crm/contacts/{con_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["contact"]["id"] == con_id
    assert detail["contact"]["accountId"] is None
    assert "leads" in detail
    assert "opportunities" in detail

    # Update contact
    update_payload = {
        "designation": "Director of Applied Microbiology",
        "name": f"Dr. Vikram Sarabhai (Director) {uid}"
    }
    update_res = client.put(f"/api/v1/crm/contacts/{con_id}", json=update_payload, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["contact"]["designation"] == "Director of Applied Microbiology"


def test_contact_association_with_existing_account(setup_phase2_env):
    """
    Test 4 & 9: Contact association with an existing Account and Account-Contact relationship display.
    """
    headers = setup_phase2_env
    uid = uuid.uuid4().hex[:8]

    # 1. Create account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Tata Bio-Energy Corp {uid}",
        "industry": "Industrial Biofuels"
    }, headers=headers)
    assert acc_res.status_code == 201
    account = acc_res.json()["account"]

    # 2. Create contact associated with account
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Ananya Deshmukh {uid}",
        "designation": "Head of Procurement",
        "email": f"ananya_{uid}@tatabioenergy.com",
        "mobileNumber": f"+9197{uuid.uuid4().int % 100000000:08d}",
        "accountId": account["id"]
    }, headers=headers)
    assert con_res.status_code == 201
    contact = con_res.json()["contact"]
    assert contact["accountId"] == account["id"]
    assert contact["accountName"] == account["name"]

    # 3. Retrieve account details and verify contact is in associated contacts list
    acc_detail_res = client.get(f"/api/v1/crm/accounts/{account['id']}", headers=headers)
    assert acc_detail_res.status_code == 200
    acc_detail = acc_detail_res.json()
    assert acc_detail["account"]["contactCount"] >= 1
    found = any(c["id"] == contact["id"] for c in acc_detail["contacts"])
    assert found is True

    # 4. Disassociate contact from account
    disassoc_res = client.put(f"/api/v1/crm/contacts/{contact['id']}", json={"accountId": ""}, headers=headers)
    assert disassoc_res.status_code == 200
    assert disassoc_res.json()["contact"]["accountId"] is None


def test_potential_duplicate_account_matching(setup_phase2_env):
    """
    Test 6 & 8: Potential duplicate Account matching and duplicate prevention without automatic merge.
    """
    headers = setup_phase2_env
    uid = uuid.uuid4().hex[:8]
    company_name = f"GreenTech Energies India {uid}"
    domain = f"greentech-india-{uid}.com"

    # Create original account
    res = client.post("/api/v1/crm/accounts", json={
        "name": company_name,
        "website": f"https://www.{domain}/in",
        "email": f"contact@{domain}"
    }, headers=headers)
    assert res.status_code == 201
    orig_account = res.json()["account"]

    # Search matches by name
    match_name_res = client.get(f"/api/v1/crm/accounts/matches?name={company_name}", headers=headers)
    assert match_name_res.status_code == 200
    matches = match_name_res.json()["matches"]
    assert len(matches) >= 1
    assert any(m["id"] == orig_account["id"] for m in matches)
    assert "Exact company name match" in matches[0]["matchReasons"]

    # Search matches by domain
    match_domain_res = client.get(f"/api/v1/crm/accounts/matches?website={domain}", headers=headers)
    assert match_domain_res.status_code == 200
    d_matches = match_domain_res.json()["matches"]
    assert len(d_matches) >= 1
    assert any(m["id"] == orig_account["id"] for m in d_matches)

    # Attempt to create duplicate without confirmDuplicate -> 409 Conflict
    dup_res = client.post("/api/v1/crm/accounts", json={
        "name": company_name,
        "website": f"alt-{domain}"
    }, headers=headers)
    assert dup_res.status_code == 409
    err_body = dup_res.json()
    assert "already exists" in err_body["message"]
    assert "matches" in err_body["details"]

    # Proceed with legitimate distinct account with confirmDuplicate = True
    distinct_res = client.post("/api/v1/crm/accounts", json={
        "name": company_name,
        "website": f"regional-{domain}",
        "confirmDuplicate": True
    }, headers=headers)
    assert distinct_res.status_code == 201
    distinct_account = distinct_res.json()["account"]
    assert distinct_account["id"] != orig_account["id"]
    assert distinct_account["accountId"] != orig_account["accountId"]


def test_potential_duplicate_contact_matching(setup_phase2_env):
    """
    Test 7 & 8: Potential duplicate Contact matching by email, phone, and confirmation.
    """
    headers = setup_phase2_env
    uid = uuid.uuid4().hex[:8]
    test_email = f"lead.engineer.{uid}@energycorp.com"
    test_phone = f"+9198{uuid.uuid4().int % 100000000:08d}"

    # Create original contact
    c1_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Sunil Kulkarni {uid}",
        "email": test_email,
        "mobileNumber": test_phone,
        "designation": "Senior Chemical Engineer"
    }, headers=headers)
    assert c1_res.status_code == 201
    c1 = c1_res.json()["contact"]

    # Search matches by email
    match_email_res = client.get(f"/api/v1/crm/contacts/matches?email={test_email}", headers=headers)
    assert match_email_res.status_code == 200
    matches = match_email_res.json()["matches"]
    assert len(matches) >= 1
    assert matches[0]["id"] == c1["id"]
    assert "Exact email match" in matches[0]["matchReasons"]

    # Attempt to create contact with duplicate email without confirmDuplicate -> 409 Conflict
    dup_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Sunil Kulkarni Jr {uid}",
        "email": test_email,
        "mobileNumber": f"+9199{uuid.uuid4().int % 100000000:08d}"
    }, headers=headers)
    assert dup_res.status_code == 409
    assert "matches" in dup_res.json()["details"]

    # Proceed with legitimate distinct contact sharing corporate email with confirmDuplicate = True
    c2_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Sunil Kulkarni Jr {uid}",
        "email": test_email,
        "mobileNumber": f"+9199{uuid.uuid4().int % 100000000:08d}",
        "confirmDuplicate": True
    }, headers=headers)
    assert c2_res.status_code == 201
    c2 = c2_res.json()["contact"]
    assert c2["id"] != c1["id"]
    assert c2["contactId"] != c1["contactId"]


def test_lead_independence_preserved(setup_phase2_env):
    """
    Test 10: Correct handling of Leads that have no Account or Contact relationship.
    Creating Leads must remain independent of Accounts/Contacts.
    """
    headers = setup_phase2_env
    ts = int(datetime.now(timezone.utc).timestamp())

    lead_payload = {
        "topic": f"Standalone Direct Enquiry {ts}",
        "companyName": f"Direct Walkin Client {ts}",
        "firstName": "Ramesh",
        "lastName": "Patel",
        "contactEmail": f"ramesh_{ts}@walkinclient.org",
        "mobilePhone": "+91 98220 12345",
        "businessArea": "Biogas",
        "leadSource": "In-Person Meeting",
        "contactMethods": ["Meeting", "Phone"],
        "connectedDate": str(date.today()),
        "accountId": None,
        "contactId": None
    }
    res = client.post("/api/v1/crm/leads", json=lead_payload, headers=headers)
    assert res.status_code == 201
    lead = res.json()["lead"]

    # Verify relationships are null and lead enquiry details stored directly
    assert lead["accountId"] is None
    assert lead["contactId"] is None
    assert lead["account"] is None
    assert lead["contact"] is None
    assert lead["companyName"] == f"Direct Walkin Client {ts}"
    assert lead["firstName"] == "Ramesh"
    assert lead["contactEmail"] == f"ramesh_{ts}@walkinclient.org"


def test_backend_authorization_and_unauthorized_access():
    """
    Test 11: Backend authorization enforces permissions; forbidden direct API calls are rejected.
    """
    # 1. No token -> 401 Unauthorized
    res_no_auth = client.get("/api/v1/crm/accounts")
    assert res_no_auth.status_code in (401, 403)

    res_post_no_auth = client.post("/api/v1/crm/accounts", json={"name": "Hacker Corp"})
    assert res_post_no_auth.status_code in (401, 403)

    # 2. User with non-CRM role (e.g. employee without CRM access) -> 403 Forbidden
    # Let's test with invalid / non-crm token or non-crm credentials if available
    fake_headers = {"Authorization": "Bearer invalid.jwt.token"}
    res_fake = client.get("/api/v1/crm/accounts", headers=fake_headers)
    assert res_fake.status_code in (401, 403)


def test_database_transaction_integrity_and_error_handling(setup_phase2_env):
    """
    Test 12: Database transaction integrity and error handling (e.g. invalid foreign keys).
    """
    headers = setup_phase2_env
    non_existent_uuid = str(uuid.uuid4())

    # Contact with non-existent account -> 404
    res = client.post("/api/v1/crm/contacts", json={
        "name": "Orphan Contact",
        "accountId": non_existent_uuid
    }, headers=headers)
    assert res.status_code == 404
    err_text = res.json().get("message") or res.json().get("detail", "")
    assert "does not exist or is inactive" in err_text
