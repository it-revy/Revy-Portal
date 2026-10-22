import os
import sys
import pytest
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


def get_test_contact_id(headers, name="Test Contact"):
    ts = int(datetime.now(timezone.utc).timestamp())
    res = client.post("/api/v1/crm/contacts", json={
        "name": f"{name} {ts}",
        "email": f"contact_{ts}_{name.lower().replace(' ', '_')}@revy-test.com"
    }, headers=headers)
    assert res.status_code == 201, f"Failed to create test contact: {res.text}"
    return res.json()["contact"]["id"]


def test_optional_product_spec_and_mandatory_title(setup_crm_stage4_environment):
    """
    Requirement 2 & 13:
    - Lead Title / Name remains mandatory.
    - Requested Product / Service Specification is optional for early enquiries and prospective clients.
    - Business Area accepts Biogas and WWT only.
    - Requirement Type accepts Direct Product/Service, Sample Testing, Undetermined.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())
    con_id = get_test_contact_id(headers, "Early Enquiry Contact")

    # 1. Lead saves when requestedProductService is empty/missing
    res_optional = client.post("/api/v1/crm/leads", json={
        "leadName": f"Early Prospect Enquiry {ts}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "contactId": con_id,
        "leadSource": "Website"
        # requestedProductService omitted
    }, headers=headers)
    assert res_optional.status_code == 201, res_optional.text
    lead_id = res_optional.json()["lead"]["id"]
    lead_data = res_optional.json()["lead"]
    assert lead_data["leadName"] == f"Early Prospect Enquiry {ts}"
    assert lead_data["requestedProductService"] is None

    # Reload and verify persistence
    res_reload = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert res_reload.status_code == 200
    assert res_reload.json()["lead"]["requestedProductService"] is None

    # 2. Phase 1 Update: Lead Title / Name is optional (empty/whitespace accepted, falls back to leadId)
    res_empty_title = client.post("/api/v1/crm/leads", json={
        "leadName": "   ",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "contactId": con_id
    }, headers=headers)
    assert res_empty_title.status_code == 201
    assert res_empty_title.json()["lead"]["displayName"] == res_empty_title.json()["lead"]["leadId"]


def test_lead_sources_including_email_campaign(setup_crm_stage4_environment):
    """
    Requirement 4 & 13:
    - Email Campaign can be selected and saved as Lead Source.
    - All canonical lead sources persist and reload successfully.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())
    con_id = get_test_contact_id(headers, "Sources Contact")

    # 1. Test 'Email Campaign'
    res_email_camp = client.post("/api/v1/crm/leads", json={
        "leadName": f"Email Campaign Lead {ts}",
        "businessArea": "WWT",
        "requirementType": "Sample Testing",
        "leadSource": "Email Campaign",
        "contactId": con_id
    }, headers=headers)
    assert res_email_camp.status_code == 201, res_email_camp.text
    assert res_email_camp.json()["lead"]["leadSource"] == "Email Campaign"

    # Reload to verify
    lead_id = res_email_camp.json()["lead"]["id"]
    res_get = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["lead"]["leadSource"] == "Email Campaign"

    # 2. Test other sources: Investor, Social Media, Cold Outreach
    for source in ["Investor", "Social Media", "Cold Outreach", "Trade Show / Expo"]:
        res = client.post("/api/v1/crm/leads", json={
            "leadName": f"{source} Lead {ts}",
            "businessArea": "Biogas",
            "requirementType": "Direct Product/Service",
            "leadSource": source,
            "contactId": con_id
        }, headers=headers)
        assert res.status_code == 201, f"Failed for source {source}: {res.text}"
        assert res.json()["lead"]["leadSource"] == source


def test_website_bare_domain_and_unsafe_scheme_validation(setup_crm_stage4_environment):
    """
    Requirement 5 & 13:
    - Bare domains like 'renergydynamics.com' and subdomains are accepted.
    - Unsafe schemes (javascript:) are rejected.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())
    con_id = get_test_contact_id(headers, "Website Contact")

    # 1. Bare domain on Lead
    res_bare = client.post("/api/v1/crm/leads", json={
        "leadName": f"Bare Domain Lead {ts}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "websiteLink": "renergydynamics.com",
        "contactId": con_id
    }, headers=headers)
    assert res_bare.status_code == 201, res_bare.text
    assert res_bare.json()["lead"]["websiteLink"] == "renergydynamics.com"

    # 2. Subdomain on Account
    res_acc = client.post("/api/v1/crm/accounts", json={
        "name": f"Subdomain Corp {ts}",
        "website": "sales.renergydynamics.com"
    }, headers=headers)
    assert res_acc.status_code == 201, res_acc.text
    assert res_acc.json()["account"]["website"] == "sales.renergydynamics.com"

    # 3. Reject unsafe javascript: scheme
    res_unsafe = client.post("/api/v1/crm/leads", json={
        "leadName": f"Unsafe Scheme Lead {ts}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "websiteLink": "javascript:alert('xss')",
        "contactId": con_id
    }, headers=headers)
    assert res_unsafe.status_code in [400, 422]


def test_next_follow_up_date_only_persistence(setup_crm_stage4_environment):
    """
    Requirement 8 & 13:
    - Next Follow-up Date persists as a calendar date (YYYY-MM-DD) without timezone shifting.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())
    con_id = get_test_contact_id(headers, "Date Contact")

    target_date = "2026-10-14"

    res_lead = client.post("/api/v1/crm/leads", json={
        "leadName": f"Date Only Lead {ts}",
        "businessArea": "WWT",
        "requirementType": "Sample Testing",
        "contactId": con_id,
        "nextFollowUpDate": target_date
    }, headers=headers)
    assert res_lead.status_code == 201, res_lead.text
    lead_id = res_lead.json()["lead"]["id"]
    assert res_lead.json()["lead"]["nextFollowUpDate"] == target_date

    # Reload from database and verify exact date match
    res_reload = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert res_reload.status_code == 200
    assert res_reload.json()["lead"]["nextFollowUpDate"] == target_date


def test_duplicate_validation_with_and_without_product_spec(setup_crm_stage4_environment):
    """
    Requirement 3 & 13:
    - When product specification is unknown, multiple leads for the same account/contact can be created without duplicate conflict.
    - When product specification is provided, duplicate open leads for the same client are prevented.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    res_acc = client.post("/api/v1/crm/accounts", json={"name": f"Dupe Spec Test {ts}"}, headers=headers)
    acc_id = res_acc.json()["account"]["id"]
    res_con = client.post("/api/v1/crm/contacts", json={"name": f"Contact Dupe {ts}", "accountId": acc_id}, headers=headers)
    con_id = res_con.json()["contact"]["id"]

    # 1. Create first enquiry without product spec -> SUCCESS
    res_early1 = client.post("/api/v1/crm/leads", json={
        "leadName": f"Early Enquiry 1 {ts}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "accountId": acc_id,
        "contactId": con_id
    }, headers=headers)
    assert res_early1.status_code == 201, res_early1.text

    # 2. Create second enquiry without product spec for same account -> MUST ALSO SUCCEED (no conflict because spec is unknown)
    res_early2 = client.post("/api/v1/crm/leads", json={
        "leadName": f"Early Enquiry 2 {ts}",
        "businessArea": "Biogas",
        "requirementType": "Undetermined",
        "accountId": acc_id,
        "contactId": con_id
        # No product spec
    }, headers=headers)
    assert res_early2.status_code == 201, res_early2.text

    # 3. Create lead with known product spec -> SUCCESS
    spec = f"Specific Bio Culture Pack {ts}"
    res_spec1 = client.post("/api/v1/crm/leads", json={
        "leadName": f"Specified Lead 1 {ts}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "requestedProductService": spec,
        "accountId": acc_id,
        "contactId": con_id
    }, headers=headers)
    assert res_spec1.status_code == 201, res_spec1.text

    # 4. Phase 1 Update: Duplicate open leads with same requirement/spec are now ALLOWED (HTTP 201)
    res_spec2 = client.post("/api/v1/crm/leads", json={
        "leadName": f"Specified Lead 2 {ts}",
        "businessArea": "Biogas",
        "requirementType": "Product",
        "requestedProductService": spec.upper(),
        "accountId": acc_id,
        "contactId": con_id
    }, headers=headers)
    assert res_spec2.status_code == 201
    assert res_spec2.json()["lead"]["id"] != res_spec1.json()["lead"]["id"]


def test_quick_create_account_and_contact_lead_assignment(setup_crm_stage4_environment):
    """
    Requirement 6, 7 & 13:
    - Quick-create Account returns valid ID, is assignable to lead.
    - Quick-create Contact returns valid ID, is assignable to lead.
    - Contact remains mandatory; Account remains optional.
    - Reloaded lead retains both relationships.
    """
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Quick-create Account
    res_acc = client.post("/api/v1/crm/accounts", json={
        "name": f"Quick Linked Enterprise {ts}",
        "website": "quick-enterprise.com",
        "industry": "CleanTech"
    }, headers=headers)
    assert res_acc.status_code == 201
    new_acc = res_acc.json()["account"]
    assert new_acc["id"] is not None

    # 2. Quick-create Contact associated with this Account
    res_con = client.post("/api/v1/crm/contacts", json={
        "name": f"Dr. Priya Sharma {ts}",
        "accountId": new_acc["id"],
        "email": f"priya_{ts}@quick-enterprise.com",
        "mobileNumber": f"+91 9988{ts % 1000000:06d}",
        "designation": "Chief Technology Officer"
    }, headers=headers)
    assert res_con.status_code == 201
    new_con = res_con.json()["contact"]
    assert new_con["id"] is not None

    # 3. Save Lead with newly created Account and Contact
    res_lead = client.post("/api/v1/crm/leads", json={
        "leadName": f"Full Quick-Created Integration Lead {ts}",
        "businessArea": "WWT",
        "requirementType": "Sample Testing",
        "accountId": new_acc["id"],
        "contactId": new_con["id"],
        "leadSource": "Email Campaign"
    }, headers=headers)
    assert res_lead.status_code == 201, res_lead.text
    lead_id = res_lead.json()["lead"]["id"]

    # 4. Reload Lead and confirm both relationships remain linked
    res_reload = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert res_reload.status_code == 200
    lead_detail = res_reload.json()["lead"]
    assert lead_detail["accountId"] == new_acc["id"]
    assert lead_detail["accountName"] == f"Quick Linked Enterprise {ts}"
    assert lead_detail["contactId"] == new_con["id"]
    assert lead_detail["contactName"] == f"Dr. Priya Sharma {ts}"

    # 5. Verify Contact remains mandatory: creating lead without contactId must fail
    res_no_con = client.post("/api/v1/crm/leads", json={
        "leadName": "Lead Without Contact",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service"
    }, headers=headers)
    assert res_no_con.status_code in [400, 422]
