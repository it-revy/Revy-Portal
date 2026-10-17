import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import app.models
from app.main import app
from app.core.database import SessionLocal
from app.crm.model import Lead, Account, Contact
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


def create_test_account(headers, name="Rel Test Account"):
    uid = uuid.uuid4().hex[:8]
    ts = int(datetime.now(timezone.utc).timestamp())
    res = client.post("/api/v1/crm/accounts", json={
        "name": f"{name} {uid}",
        "industry": "Renewable Energy",
        "website": f"renergy-{uid}.com",
        "phone": f"+9197{uuid.uuid4().int % 100000000:08d}",
        "email": f"info_{uid}_{ts}@renergy.test"
    }, headers=headers)
    assert res.status_code == 201, f"Failed to create account: {res.text}"
    return res.json()["account"]


def create_test_contact(headers, account_id=None, name="Rel Test Contact"):
    uid = uuid.uuid4().hex[:8]
    ts = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "name": f"{name} {uid}",
        "designation": "Technical Lead",
        "email": f"contact_{uid}_{ts}@renergy.test",
        "mobileNumber": f"+9198{uuid.uuid4().int % 100000000:08d}"
    }
    if account_id:
        payload["accountId"] = account_id
    res = client.post("/api/v1/crm/contacts", json=payload, headers=headers)
    assert res.status_code == 201, f"Failed to create contact: {res.text}"
    return res.json()["contact"]


def test_lead_creation_and_persistence_with_account_and_contact(setup_crm_stage4_environment):
    """
    1. Create Lead with existing Account and Contact.
    2. Verify relationships persist in database.
    3. Verify API response includes rich relationship objects (account, contact) and flat fields.
    4. Verify Lead Detail endpoint returns saved relationships.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    uid = uuid.uuid4().hex[:6]

    account = create_test_account(headers, "Acme Biogas Corp")
    contact = create_test_contact(headers, account_id=account["id"], name="Dr. Ramesh Verma")

    create_payload = {
        "leadName": f"Full Relationship Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "requestedProductService": f"Enzyme Supply {uid}",
        "accountId": account["id"],
        "contactId": contact["id"],
        "leadSource": "Website"
    }
    res = client.post("/api/v1/crm/leads", json=create_payload, headers=headers)
    assert res.status_code == 201, res.text
    created = res.json()["lead"]

    # Verify API response has both rich and flat relationship attributes
    assert created["accountId"] == account["id"]
    assert created["accountName"] == account["name"]
    assert created["account"] is not None
    assert created["account"]["name"] == account["name"]
    assert created["account"]["accountId"] == account["accountId"]
    assert created["account"]["industry"] == "Renewable Energy"

    assert created["contactId"] == contact["id"]
    assert created["contactName"] == contact["name"]
    assert created["contact"] is not None
    assert created["contact"]["name"] == contact["name"]
    assert created["contact"]["contactId"] == contact["contactId"]
    assert created["contact"]["email"] == contact["email"]
    assert created["contact"]["mobileNumber"] == contact["mobileNumber"]

    lead_db_id = created["id"]

    # Verify directly against database
    db = SessionLocal()
    try:
        db_lead = db.query(Lead).filter(Lead.id == lead_db_id).first()
        assert db_lead is not None
        assert db_lead.account_id == account["id"]
        assert db_lead.contact_id == contact["id"]
    finally:
        db.close()

    # Verify detail GET endpoint
    res_get = client.get(f"/api/v1/crm/leads/{lead_db_id}", headers=headers)
    assert res_get.status_code == 200
    detail = res_get.json()["lead"]
    assert detail["account"] is not None
    assert detail["account"]["name"] == account["name"]
    assert detail["contact"] is not None
    assert detail["contact"]["name"] == contact["name"]


def test_lead_creation_without_account_but_valid_contact(setup_crm_stage4_environment):
    """
    A Lead can be created without an Account, but must have a valid Contact.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    uid = uuid.uuid4().hex[:6]

    unassigned_contact = create_test_contact(headers, account_id=None, name="Direct Consultant")

    res = client.post("/api/v1/crm/leads", json={
        "leadName": f"Direct Lead No Account {uid}",
        "businessArea": "WWT",
        "requirementType": "Sample Testing",
        "contactId": unassigned_contact["id"],
        "leadSource": "Cold Outreach"
    }, headers=headers)
    assert res.status_code == 201, res.text
    lead_data = res.json()["lead"]

    assert lead_data["accountId"] is None
    assert lead_data["account"] is None
    assert lead_data["contactId"] == unassigned_contact["id"]
    assert lead_data["contact"]["name"] == unassigned_contact["name"]

    # Verify reload
    res_get = client.get(f"/api/v1/crm/leads/{lead_data['id']}", headers=headers)
    assert res_get.status_code == 200
    detail = res_get.json()["lead"]
    assert detail["account"] is None
    assert detail["accountId"] is None
    assert detail["contact"] is not None


def test_lead_creation_auto_populates_account_from_contact(setup_crm_stage4_environment):
    """
    If account is omitted during lead creation, but the contact belongs to an account,
    the lead automatically inherits the contact's account.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    uid = uuid.uuid4().hex[:6]

    account = create_test_account(headers, "Auto Populate Parent Corp")
    contact = create_test_contact(headers, account_id=account["id"], name="Affiliated Contact")

    res = client.post("/api/v1/crm/leads", json={
        "leadName": f"Auto Inherit Account Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "contactId": contact["id"]
        # accountId deliberately omitted
    }, headers=headers)
    assert res.status_code == 201, res.text
    lead_data = res.json()["lead"]

    assert lead_data["accountId"] == account["id"]
    assert lead_data["account"]["name"] == account["name"]
    assert lead_data["contactId"] == contact["id"]


def test_lead_editing_preserves_relationships_on_unrelated_update(setup_crm_stage4_environment):
    """
    Editing an unrelated Lead field (title, remarks, nextFollowUpDate) must not
    clear or alter the Account and Contact relationships.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    uid = uuid.uuid4().hex[:6]

    account = create_test_account(headers, "Preserve Rel Account")
    contact = create_test_contact(headers, account_id=account["id"], name="Preserve Rel Contact")

    res = client.post("/api/v1/crm/leads", json={
        "leadName": f"Initial Lead Title {uid}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "accountId": account["id"],
        "contactId": contact["id"]
    }, headers=headers)
    lead_id = res.json()["lead"]["id"]

    # Update only unrelated fields
    res_update = client.put(f"/api/v1/crm/leads/{lead_id}", json={
        "leadName": f"Updated Lead Title {uid}",
        "remarks": "Updated remark text without touching account/contact",
        "nextFollowUpDate": "2026-11-20"
    }, headers=headers)
    assert res_update.status_code == 200, res_update.text
    updated = res_update.json()["lead"]

    assert updated["leadName"] == f"Updated Lead Title {uid}"
    assert updated["remarks"] == "Updated remark text without touching account/contact"
    assert updated["accountId"] == account["id"]
    assert updated["account"]["name"] == account["name"]
    assert updated["contactId"] == contact["id"]
    assert updated["contact"]["name"] == contact["name"]

    # Verify on reload
    res_reload = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert res_reload.status_code == 200
    reloaded = res_reload.json()["lead"]
    assert reloaded["accountId"] == account["id"]
    assert reloaded["contactId"] == contact["id"]


def test_lead_editing_change_account_and_contact(setup_crm_stage4_environment):
    """
    Change Account and select a valid Contact belonging to the new Account.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    uid = uuid.uuid4().hex[:6]

    account1 = create_test_account(headers, "Original Account")
    contact1 = create_test_contact(headers, account_id=account1["id"], name="Contact One")

    account2 = create_test_account(headers, "New Target Account")
    contact2 = create_test_contact(headers, account_id=account2["id"], name="Contact Two")

    res = client.post("/api/v1/crm/leads", json={
        "leadName": f"Reassign Pair Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "accountId": account1["id"],
        "contactId": contact1["id"]
    }, headers=headers)
    lead_id = res.json()["lead"]["id"]

    # Update both to account2 and contact2
    res_update = client.put(f"/api/v1/crm/leads/{lead_id}", json={
        "accountId": account2["id"],
        "contactId": contact2["id"]
    }, headers=headers)
    assert res_update.status_code == 200, res_update.text
    updated = res_update.json()["lead"]

    assert updated["accountId"] == account2["id"]
    assert updated["account"]["name"] == account2["name"]
    assert updated["contactId"] == contact2["id"]
    assert updated["contact"]["name"] == contact2["name"]

    # Reload check
    res_reload = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert res_reload.json()["lead"]["accountId"] == account2["id"]
    assert res_reload.json()["lead"]["contactId"] == contact2["id"]


def test_lead_editing_clear_optional_account(setup_crm_stage4_environment):
    """
    Clearing optional Account when the contact is unassigned is permitted.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    uid = uuid.uuid4().hex[:6]

    account = create_test_account(headers, "Initial Clearing Account")
    unassigned_contact = create_test_contact(headers, account_id=None, name="Independent Consultant")

    res = client.post("/api/v1/crm/leads", json={
        "leadName": f"Clear Account Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "accountId": account["id"],
        "contactId": unassigned_contact["id"]
    }, headers=headers)
    lead_id = res.json()["lead"]["id"]

    # Now edit to clear the account by selecting another unassigned contact
    unassigned_contact2 = create_test_contact(headers, account_id=None, name="Independent Consultant 2")
    res_update = client.put(f"/api/v1/crm/leads/{lead_id}", json={
        "accountId": None,
        "contactId": unassigned_contact2["id"]
    }, headers=headers)
    assert res_update.status_code == 200, res_update.text
    updated = res_update.json()["lead"]
    assert updated["accountId"] is None
    assert updated["account"] is None
    assert updated["contactId"] == unassigned_contact2["id"]


def test_validation_rejects_missing_contact_and_inconsistent_pairs(setup_crm_stage4_environment):
    """
    - Contact is mandatory (reject missing/empty).
    - Reject non-existent Account or Contact.
    - Reject inconsistent Account-Contact relationship (contact belongs to Account A, but Lead uses Account B).
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    uid = uuid.uuid4().hex[:6]

    account_a = create_test_account(headers, "Company Alpha")
    contact_a = create_test_contact(headers, account_id=account_a["id"], name="Alpha Employee")

    account_b = create_test_account(headers, "Company Beta")

    # 1. Missing Contact on creation -> 400 or 422
    res_missing_con = client.post("/api/v1/crm/leads", json={
        "leadName": f"No Contact Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined"
        # contactId missing
    }, headers=headers)
    assert res_missing_con.status_code in [400, 422]

    # 2. Invalid contact ID -> 404
    res_invalid_con = client.post("/api/v1/crm/leads", json={
        "leadName": f"Invalid Contact Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "contactId": "00000000-0000-0000-0000-000000000000"
    }, headers=headers)
    assert res_invalid_con.status_code == 404

    # 3. Inconsistent Account-Contact pair -> 400
    res_inconsistent = client.post("/api/v1/crm/leads", json={
        "leadName": f"Inconsistent Pair Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "accountId": account_b["id"],
        "contactId": contact_a["id"]  # belongs to account_a!
    }, headers=headers)
    assert res_inconsistent.status_code == 400
    assert "belongs to a different Account" in res_inconsistent.text

    # 4. Attempt to clear contact on update -> 400
    lead_res = client.post("/api/v1/crm/leads", json={
        "leadName": f"Valid Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "accountId": account_a["id"],
        "contactId": contact_a["id"]
    }, headers=headers)
    valid_lead_id = lead_res.json()["lead"]["id"]

    res_clear_con = client.put(f"/api/v1/crm/leads/{valid_lead_id}", json={
        "contactId": ""
    }, headers=headers)
    assert res_clear_con.status_code in [400, 422]


def test_quick_create_account_and_contact_immediate_assignment(setup_crm_stage4_environment):
    """
    Test the quick-create workflow:
    1. Create account via quick-create API endpoint.
    2. Create contact linked to that account via quick-create API endpoint.
    3. Use both IDs immediately in a new Lead request.
    4. Verify relationships persist in DB and display correctly after reload.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    uid = uuid.uuid4().hex[:6]

    # Quick create Account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Quick Biofuels Ltd {uid}",
        "industry": "Bioenergy",
        "phone": f"+9196{uuid.uuid4().int % 100000000:08d}",
        "website": f"quickbio-{uid}.com"
    }, headers=headers)
    assert acc_res.status_code == 201
    new_acc = acc_res.json()["account"]
    assert new_acc["id"] is not None
    assert new_acc["accountId"] is not None

    # Quick create Contact associated with new Account
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Pooja Sharma {uid}",
        "designation": "Director of Operations",
        "email": f"pooja_{uid}@quickbiofuels.com",
        "mobileNumber": f"+9195{uuid.uuid4().int % 100000000:08d}",
        "accountId": new_acc["id"]
    }, headers=headers)
    assert con_res.status_code == 201
    new_con = con_res.json()["contact"]
    assert new_con["id"] is not None
    assert new_con["contactId"] is not None
    assert new_con["accountId"] == new_acc["id"]

    # Submit Lead with both
    lead_res = client.post("/api/v1/crm/leads", json={
        "leadName": f"Quick Created Pipeline Lead {uid}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "requestedProductService": f"Inoculum 500 TPD {uid}",
        "accountId": new_acc["id"],
        "contactId": new_con["id"]
    }, headers=headers)
    assert lead_res.status_code == 201, lead_res.text
    lead = lead_res.json()["lead"]

    assert lead["accountId"] == new_acc["id"]
    assert lead["contactId"] == new_con["id"]
    assert lead["account"]["name"] == new_acc["name"]
    assert lead["contact"]["name"] == new_con["name"]
    assert lead["contact"]["email"] == new_con["email"]

    # Reload from DB via GET endpoint
    reload_res = client.get(f"/api/v1/crm/leads/{lead['id']}", headers=headers)
    assert reload_res.status_code == 200
    reloaded = reload_res.json()["lead"]
    assert reloaded["account"]["id"] == new_acc["id"]
    assert reloaded["account"]["name"] == new_acc["name"]
    assert reloaded["contact"]["id"] == new_con["id"]
    assert reloaded["contact"]["name"] == new_con["name"]
