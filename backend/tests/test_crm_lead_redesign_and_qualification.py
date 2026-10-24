import os
import sys
import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.crm.model import Lead, Account, Contact, Opportunity
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


def test_create_lead_without_account_or_contact_fk(setup_crm_stage4_environment):
    """
    Requirement 2 & 9:
    - A Lead can exist without an Account or Contact foreign key.
    - Lead creation must not require an Account or Contact relationship.
    - Direct contact and company info must be stored on the Lead.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    payload = {
        "topic": f"Independent Prospect {ts}",
        # Direct Section 1 Contact Fields
        "firstName": "Arun",
        "lastName": "Verma",
        "jobTitle": "Plant Head",
        "businessPhone": "+91 20 1234 5678",
        "mobilePhone": "+91 98765 11223",
        "contactEmail": f"arun.verma.{ts}@independent-bio.com",

        # Direct Section 2 Company Fields
        "companyName": f"Verma Bio-Energies {ts}",
        "websiteLink": "https://www.verma-bio.com",
        "clientLocation": "Nashik, Maharashtra",
        "communicationChannel": "Inbound Call",
        "connectedDate": "2026-10-23",
        "companyEmail": f"info.{ts}@verma-bio.com",

        # Section 3 Additional Lead Info
        "leadSource": "Inbound Call",
        "rating": "Hot",
        "clientStatus": "New",

        # Section 4 Description & Business
        "description": "Client wants to install a 50 TPD CBG plant.",
        "industry": "Distilleries",
        "numberOfEmployees": 250,
        "currency": "INR",
        "requirementTypes": ["Consulting", "Product"],
        "businessArea": "Biogas",

        # Section 5 Contact Method
        "contactMethods": ["Phone", "WhatsApp"],
        "preferredContactMethod": "WhatsApp"
    }

    # 1. Post Lead without contactId or accountId
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code == 201, f"Failed: {res.text}"
    created_lead = res.json()["lead"]

    # Verify no foreign keys were required or auto-created
    assert created_lead["contactId"] is None
    assert created_lead["accountId"] is None
    assert created_lead["contact"] is None
    assert created_lead["account"] is None

    # Verify all 5 sections were stored directly on the lead
    assert created_lead["firstName"] == "Arun"
    assert created_lead["lastName"] == "Verma"
    assert created_lead["jobTitle"] == "Plant Head"
    assert created_lead["businessPhone"] == "+91 20 1234 5678"
    assert created_lead["mobilePhone"] == "+91 98765 11223"
    assert created_lead["contactEmail"] == f"arun.verma.{ts}@independent-bio.com"

    assert created_lead["companyName"] == f"Verma Bio-Energies {ts}"
    assert created_lead["websiteLink"] == "https://www.verma-bio.com"
    assert created_lead["location"] == "Nashik, Maharashtra"
    assert created_lead["communicationChannel"] == "Inbound Call"
    assert created_lead["connectedDate"] == "2026-10-23"
    assert created_lead["companyEmail"] == f"info.{ts}@verma-bio.com"

    assert created_lead["leadSource"] == "Inbound Call"
    assert created_lead["rating"] == "Hot"
    assert created_lead["clientStatus"] == "New"

    assert created_lead["description"] == "Client wants to install a 50 TPD CBG plant."
    assert created_lead["industry"] == "Distilleries"
    assert created_lead["numberOfEmployees"] == 250
    assert created_lead["currency"] == "INR"
    assert set(created_lead["requirementTypes"]) == {"Consulting", "Product"}

    assert set(created_lead["contactMethods"]) == {"Phone", "WhatsApp"}
    assert created_lead["preferredContactMethod"] == "WhatsApp"

    # 2. Retrieve via GET /api/v1/crm/leads/{id} and verify exact persistence
    lead_id = created_lead["id"]
    get_res = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert get_res.status_code == 200
    retrieved = get_res.json()["lead"]

    assert retrieved["contactId"] is None
    assert retrieved["accountId"] is None
    assert retrieved["firstName"] == "Arun"
    assert retrieved["companyName"] == f"Verma Bio-Energies {ts}"
    assert retrieved["preferredContactMethod"] == "WhatsApp"


def test_optional_and_duplicate_lead_titles(setup_crm_stage4_environment):
    """
    Requirement 9:
    - Keep Lead Title optional.
    - Allow duplicate Lead names and duplicate enquiries.
    - Retain unique, automatically generated Lead IDs.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Lead without title (empty string / omitted)
    res_no_title = client.post("/api/v1/crm/leads", json={
        "topic": "",
        "firstName": "Priya",
        "companyName": f"Priya Bio {ts}",
        "requirementTypes": ["Sample Testing"],
        "leadSource": "Website"
    }, headers=headers)
    assert res_no_title.status_code == 201
    lead_a = res_no_title.json()["lead"]
    assert lead_a["leadId"].startswith("LEAD-")
    assert lead_a["leadName"] is None

    # 2. Two leads with exact duplicate title
    duplicate_title = f"Duplicate Enquiry Title {ts}"
    res_dup1 = client.post("/api/v1/crm/leads", json={
        "leadName": duplicate_title,
        "companyName": f"Company A {ts}",
        "leadSource": "Website"
    }, headers=headers)
    assert res_dup1.status_code == 201
    lead_dup1 = res_dup1.json()["lead"]

    res_dup2 = client.post("/api/v1/crm/leads", json={
        "leadName": duplicate_title,
        "companyName": f"Company B {ts}",
        "leadSource": "Referral"
    }, headers=headers)
    assert res_dup2.status_code == 201
    lead_dup2 = res_dup2.json()["lead"]

    assert lead_dup1["leadName"] == duplicate_title
    assert lead_dup2["leadName"] == duplicate_title
    assert lead_dup1["leadId"] != lead_dup2["leadId"]


def test_update_lead_preserves_original_data(setup_crm_stage4_environment):
    """
    Requirement 9 & 14:
    - Edit a Lead without losing its original contact, company, or requirement data.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create lead
    create_res = client.post("/api/v1/crm/leads", json={
        "firstName": "Sunil",
        "lastName": "Kapoor",
        "contactEmail": f"sunil.{ts}@kapoor-ent.com",
        "companyName": f"Kapoor Enterprises {ts}",
        "websiteLink": "https://www.kapoor.com",
        "rating": "Cold",
        "requirementTypes": ["Consulting", "Sample Testing"],
        "contactMethods": ["Email", "Phone"],
        "preferredContactMethod": "Email"
    }, headers=headers)
    assert create_res.status_code == 201
    lead_id = create_res.json()["lead"]["id"]

    # Update only rating and description
    update_res = client.put(f"/api/v1/crm/leads/{lead_id}", json={
        "rating": "Hot",
        "description": "Client upgraded urgency to immediate requirement."
    }, headers=headers)
    assert update_res.status_code == 200
    updated = update_res.json()["lead"]

    # Verify updated fields
    assert updated["rating"] == "Hot"
    assert updated["description"] == "Client upgraded urgency to immediate requirement."

    # Verify original fields preserved
    assert updated["firstName"] == "Sunil"
    assert updated["lastName"] == "Kapoor"
    assert updated["contactEmail"] == f"sunil.{ts}@kapoor-ent.com"
    assert updated["companyName"] == f"Kapoor Enterprises {ts}"
    assert updated["websiteLink"] == "https://www.kapoor.com"
    assert set(updated["requirementTypes"]) == {"Consulting", "Sample Testing"}
    assert set(updated["contactMethods"]) == {"Email", "Phone"}
    assert updated["preferredContactMethod"] == "Email"


def test_qualification_create_new_account_and_contact(setup_crm_stage4_environment):
    """
    Requirement 10 & 11:
    - Qualify a Lead into an Opportunity.
    - Transactionally creates new Account and Contact based on Lead's company & person info.
    - Sets Lead status to Qualified.
    - Links Lead to resulting Account, Contact, and Opportunity.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Create fresh unlinked lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"New Bio Plant Project {ts}",
        "firstName": "Vikram",
        "lastName": "Mehta",
        "jobTitle": "CEO",
        "businessPhone": "+91 22 9988 7766",
        "contactEmail": f"vikram.{ts}@mehtabio.com",
        "companyName": f"Mehta BioTech {ts}",
        "websiteLink": "https://www.mehtabiotech.com",
        "location": "Vadodara, Gujarat",
        "industry": "Renewable Energy",
        "numberOfEmployees": 120,
        "currency": "INR",
        "requirementTypes": ["Consulting", "Product"],
        "leadSource": "Website",
        "rating": "Hot"
    }, headers=headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]
    lead_id = lead["id"]

    # 2. Check qualification matches endpoint
    match_res = client.get(f"/api/v1/crm/leads/{lead_id}/qualification-matches", headers=headers)
    assert match_res.status_code == 200
    assert "matchingAccounts" in match_res.json()
    assert "matchingContacts" in match_res.json()

    # 3. Qualify with new Account and new Contact
    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"Mehta BioTech {ts}",
            "website": "https://www.mehtabiotech.com",
            "email": f"info.{ts}@mehtabio.com",
            "industry": "Renewable Energy",
            "address": "Vadodara, Gujarat"
        },
        "contact": {
            "action": "create",
            "name": "Vikram Mehta",
            "email": f"vikram.{ts}@mehtabio.com",
            "mobileNumber": "+91 22 9988 7766",
            "designation": "CEO"
        },
        "opportunityName": f"Opportunity — Mehta BioTech {ts}",
        "opportunityDescription": "500 kW Bio-CNG Consulting and Product supply.",
        "estimatedValue": 7500000.0
    }

    qual_res = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json=qualify_payload, headers=headers)
    assert qual_res.status_code == 200, f"Qualify failed: {qual_res.text}"
    qual_data = qual_res.json()

    assert qual_data["success"] is True
    assert "successfully qualified" in qual_data["message"]

    # Verify Account
    account = qual_data["account"]
    assert account["id"] is not None
    assert account["accountId"].startswith("ACC-")
    assert account["name"] == f"Mehta BioTech {ts}"

    # Verify Contact
    contact = qual_data["contact"]
    assert contact["id"] is not None
    assert contact["contactId"].startswith("CON-")
    assert contact["name"] == "Vikram Mehta"

    # Verify Opportunity
    opportunity = qual_data["opportunity"]
    assert opportunity["id"] is not None
    assert opportunity["opportunityId"].startswith("OPP-")
    assert opportunity["name"] == f"Opportunity — Mehta BioTech {ts}"
    assert opportunity["accountId"] == account["id"]
    assert opportunity["contactId"] == contact["id"]
    assert opportunity["originatingLeadId"] == lead_id
    assert opportunity["estimatedValue"] == 7500000.0

    # Verify Lead updated status and linkages
    lead_after = qual_data["lead"]
    assert lead_after["lifecycleStatus"] == "Qualified"
    assert lead_after["accountId"] == account["id"]
    assert lead_after["contactId"] == contact["id"]
    assert lead_after["opportunityId"] == opportunity["id"]
    assert lead_after["qualifiedAt"] is not None

    # Verify via separate GET /leads/{id}
    refetch = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert refetch.status_code == 200
    r_lead = refetch.json()["lead"]
    assert r_lead["lifecycleStatus"] == "Qualified"
    assert r_lead["opportunityId"] == opportunity["id"]
    assert r_lead["account"]["id"] == account["id"]
    assert r_lead["contact"]["id"] == contact["id"]


def test_qualification_reuse_existing_account_and_contact(setup_crm_stage4_environment):
    """
    Requirement 10 & 11:
    - Qualify a Lead by reusing an existing Account and Contact.
    - Does not create duplicate Account or Contact records.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Create pre-existing Account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Existing Enterprise {ts}",
        "website": "https://www.existing-enterprise.com",
        "email": f"corp.{ts}@existing-enterprise.com"
    }, headers=headers)
    assert acc_res.status_code == 201
    existing_acc_id = acc_res.json()["account"]["id"]

    # 2. Create pre-existing Contact under that Account
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Existing Executive {ts}",
        "accountId": existing_acc_id,
        "email": f"exec.{ts}@existing-enterprise.com",
        "designation": "VP Operations"
    }, headers=headers)
    assert con_res.status_code == 201
    existing_con_id = con_res.json()["contact"]["id"]

    # 3. Create fresh Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Second Expansion Project {ts}",
        "firstName": "Existing",
        "lastName": "Executive",
        "contactEmail": f"exec.{ts}@existing-enterprise.com",
        "companyName": f"Existing Enterprise {ts}",
        "requirementTypes": ["Sample Testing"],
        "leadSource": "In-Person Meeting"
    }, headers=headers)
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["lead"]["id"]

    # 4. Qualify Lead reusing the existing Account & Contact
    qualify_payload = {
        "account": {
            "action": "reuse",
            "accountId": existing_acc_id
        },
        "contact": {
            "action": "reuse",
            "contactId": existing_con_id
        },
        "opportunityName": f"Opportunity for Existing Corp {ts}"
    }

    qual_res = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json=qualify_payload, headers=headers)
    assert qual_res.status_code == 200
    res_data = qual_res.json()

    assert res_data["account"]["id"] == existing_acc_id
    assert res_data["contact"]["id"] == existing_con_id
    assert res_data["opportunity"]["accountId"] == existing_acc_id
    assert res_data["opportunity"]["contactId"] == existing_con_id
    assert res_data["lead"]["lifecycleStatus"] == "Qualified"


def test_qualification_idempotency_on_retry(setup_crm_stage4_environment):
    """
    Requirement 12:
    - Qualifying the same Lead twice cannot create duplicate Opportunities.
    - If already qualified, safely returns existing linked records.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Idempotency Lead {ts}",
        "firstName": "Anita",
        "lastName": "Rao",
        "companyName": f"Rao Systems {ts}",
        "requirementTypes": ["Consulting"]
    }, headers=headers)
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["lead"]["id"]

    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"Rao Systems {ts}"
        },
        "contact": {
            "action": "create",
            "name": "Anita Rao"
        },
        "opportunityName": f"Opportunity Rao {ts}"
    }

    # First qualification call
    res1 = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json=qualify_payload, headers=headers)
    assert res1.status_code == 200
    opp_id_1 = res1.json()["opportunity"]["id"]

    # Second qualification call (e.g. repeated click or timeout retry)
    res2 = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json=qualify_payload, headers=headers)
    assert res2.status_code == 200
    opp_id_2 = res2.json()["opportunity"]["id"]

    # Must return the SAME opportunity ID without creating duplicates
    assert opp_id_1 == opp_id_2
    assert "already qualified" in res2.json()["message"]


def test_qualification_rejects_incompatible_account_contact(setup_crm_stage4_environment):
    """
    Requirement 16:
    - Reject invalid Account-Contact combinations.
    - Contact belonging to Account A cannot be assigned to Opportunity for Account B without resolution.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create Account A
    acc_a = client.post("/api/v1/crm/accounts", json={"name": f"Account A {ts}"}, headers=headers).json()["account"]

    # Create Account B
    acc_b = client.post("/api/v1/crm/accounts", json={"name": f"Account B {ts}"}, headers=headers).json()["account"]

    # Create Contact strictly under Account A
    con_a = client.post("/api/v1/crm/contacts", json={
        "name": f"Contact of Account A {ts}",
        "accountId": acc_a["id"]
    }, headers=headers).json()["contact"]

    # Create a fresh Lead
    lead = client.post("/api/v1/crm/leads", json={
        "topic": f"Incompatible Test {ts}",
        "requirementTypes": ["Product"]
    }, headers=headers).json()["lead"]

    # Try qualifying with Account B while reusing Contact A (belongs to Account A)
    res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json={
        "account": {"action": "reuse", "accountId": acc_b["id"]},
        "contact": {"action": "reuse", "contactId": con_a["id"]}
    }, headers=headers)

    # Must reject with 400 Validation Error
    assert res.status_code == 400
    assert "belongs to a different Account" in res.text

    # Verify transaction rollback: Lead remains Open and not qualified
    lead_check = client.get(f"/api/v1/crm/leads/{lead['id']}", headers=headers).json()["lead"]
    assert lead_check["lifecycleStatus"] == "Open"
    assert lead_check["opportunityId"] is None


def test_list_and_get_opportunities_api(setup_crm_stage4_environment):
    """
    Test Opportunity listing and retrieval APIs exposed at /api/v1/crm/opportunities.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create and qualify a lead to ensure at least one opportunity exists
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Opportunity List Test {ts}",
        "companyName": f"Opp Listed Corp {ts}",
        "firstName": "Naveen",
        "lastName": "Kumar",
        "requirementTypes": ["Consulting"]
    }, headers=headers)
    lead_id = lead_res.json()["lead"]["id"]

    client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json={
        "account": {"action": "create", "name": f"Opp Listed Corp {ts}"},
        "contact": {"action": "create", "name": "Naveen Kumar"},
        "opportunityName": f"Searchable Opp {ts}"
    }, headers=headers)

    # 1. List opportunities
    list_res = client.get("/api/v1/crm/opportunities", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["success"] is True
    assert list_res.json()["count"] >= 1
    opps = list_res.json()["opportunities"]

    # 2. Search for the opportunity
    search_res = client.get(f"/api/v1/crm/opportunities?search=Searchable Opp {ts}", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["count"] >= 1
    found_opp = search_res.json()["opportunities"][0]

    # 3. Get single opportunity
    get_res = client.get(f"/api/v1/crm/opportunities/{found_opp['id']}", headers=headers)
    assert get_res.status_code == 200
    opp_detail = get_res.json()["opportunity"]
    assert opp_detail["id"] == found_opp["id"]
    assert opp_detail["name"] == f"Searchable Opp {ts}"


def test_qualification_create_account_and_reuse_unassigned_contact(setup_crm_stage4_environment):
    """
    Requirement 16:
    - Create a new Account and reuse an existing Contact when valid (e.g. contact has no existing account association).
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Create an independent Contact without an account
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Freelance Consultant {ts}",
        "email": f"freelance.{ts}@domain.com",
        "designation": "Advisor"
    }, headers=headers)
    assert con_res.status_code == 201
    con_id = con_res.json()["contact"]["id"]
    assert con_res.json()["contact"]["accountId"] is None

    # 2. Create a Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Advisor Engagement Lead {ts}",
        "companyName": f"New Bio Client Corp {ts}",
        "requirementTypes": ["Consulting"]
    }, headers=headers)
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["lead"]["id"]

    # 3. Qualify with new Account and reusing the independent Contact
    qual_res = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json={
        "account": {
            "action": "create",
            "name": f"New Bio Client Corp {ts}"
        },
        "contact": {
            "action": "reuse",
            "contactId": con_id
        },
        "opportunityName": f"Opportunity for Advisor Corp {ts}"
    }, headers=headers)
    assert qual_res.status_code == 200, f"Failed: {qual_res.text}"
    qual_data = qual_res.json()

    created_acc_id = qual_data["account"]["id"]
    assert qual_data["contact"]["id"] == con_id
    assert qual_data["opportunity"]["accountId"] == created_acc_id
    assert qual_data["opportunity"]["contactId"] == con_id
    assert qual_data["lead"]["lifecycleStatus"] == "Qualified"

    # Verify contact was linked to the newly created Account
    con_check = client.get(f"/api/v1/crm/contacts/{con_id}", headers=headers).json()["contact"]
    assert con_check["accountId"] == created_acc_id


def test_qualification_reuse_account_and_create_new_contact(setup_crm_stage4_environment):
    """
    Requirement 16:
    - Create a new Contact under an existing Account during qualification.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Create existing Account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"Parent Conglomerate {ts}",
        "website": "https://www.parent-conglomerate.com"
    }, headers=headers)
    assert acc_res.status_code == 201
    acc_id = acc_res.json()["account"]["id"]

    # 2. Create Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"New Division Lead {ts}",
        "firstName": "Divisional",
        "lastName": "Director",
        "companyName": f"Parent Conglomerate {ts}",
        "requirementTypes": ["Product"]
    }, headers=headers)
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["lead"]["id"]

    # 3. Qualify with reusing existing Account and creating new Contact
    qual_res = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json={
        "account": {
            "action": "reuse",
            "accountId": acc_id
        },
        "contact": {
            "action": "create",
            "name": f"Divisional Director {ts}",
            "email": f"div.director.{ts}@parent-conglomerate.com",
            "designation": "Division Head"
        },
        "opportunityName": f"Division Product Supply {ts}"
    }, headers=headers)
    assert qual_res.status_code == 200, f"Failed: {qual_res.text}"
    qual_data = qual_res.json()

    assert qual_data["account"]["id"] == acc_id
    new_con_id = qual_data["contact"]["id"]
    assert qual_data["opportunity"]["accountId"] == acc_id
    assert qual_data["opportunity"]["contactId"] == new_con_id

    # Verify newly created contact is linked to the existing Account
    con_check = client.get(f"/api/v1/crm/contacts/{new_con_id}", headers=headers).json()["contact"]
    assert con_check["accountId"] == acc_id


def test_qualification_preserves_additional_contacts(setup_crm_stage4_environment):
    """
    Requirement 11 & 16:
    - Preserve Primary and Additional Contact relationships during qualification.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Create an existing contact for additional contact role
    extra_con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Additional Engineer {ts}",
        "email": f"eng.{ts}@partner.com"
    }, headers=headers)
    assert extra_con_res.status_code == 201
    extra_con_id = extra_con_res.json()["contact"]["id"]

    # 2. Create Lead with additionalContactIds
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"Multi Contact Project {ts}",
        "firstName": "Lead",
        "lastName": "Primary",
        "contactEmail": f"lead.primary.{ts}@example.com",
        "companyName": f"Multi Contact Org {ts}",
        "requirementTypes": ["Consulting", "Sample Testing"],
        "additionalContactIds": [extra_con_id]
    }, headers=headers)
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["lead"]["id"]

    # Verify additional contacts attached before qualification
    lead_before = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers).json()["lead"]
    assert extra_con_id in lead_before["additionalContactIds"]

    # 3. Qualify Lead
    qual_res = client.post(f"/api/v1/crm/leads/{lead_id}/qualify", json={
        "account": {"action": "create", "name": f"Multi Contact Org {ts}"},
        "contact": {"action": "create", "name": "Lead Primary", "email": f"lead.primary.{ts}@example.com"},
        "opportunityName": f"Multi Contact Opportunity {ts}"
    }, headers=headers)
    assert qual_res.status_code == 200
    primary_con_id = qual_res.json()["contact"]["id"]

    # 4. Verify after qualification: Lead is Qualified, has Primary contact, and retains Additional contact
    lead_after = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers).json()["lead"]
    assert lead_after["lifecycleStatus"] == "Qualified"
    assert lead_after["contactId"] == primary_con_id
    assert extra_con_id in lead_after["additionalContactIds"]

