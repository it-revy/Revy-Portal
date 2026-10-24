import os
import sys
import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.crm.model import Lead, Account, Contact
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_reengineering_env(setup_crm_stage4_environment):
    return get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")


def test_create_lead_with_topic_only(setup_reengineering_env):
    """Criteria 4: A Lead with only a Topic/Title and otherwise valid required fields can be saved."""
    headers = setup_reengineering_env
    ts = int(datetime.now(timezone.utc).timestamp())

    payload = {
        "topic": f"Topic Only Enquiry {ts}",
        "businessArea": "Biogas",
        "leadSource": "Website",
        "contactMethods": ["Email"],
        "connectedDate": str(date.today())
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code == 201
    lead = res.json()["lead"]
    assert lead["leadName"] == f"Topic Only Enquiry {ts}"
    assert lead["companyName"] is None
    assert lead["leadId"].startswith("LEAD-")


def test_create_lead_with_company_only(setup_reengineering_env):
    """Criteria 5: A Lead with only a Company Name and otherwise valid required fields can be saved."""
    headers = setup_reengineering_env
    ts = int(datetime.now(timezone.utc).timestamp())

    payload = {
        "companyName": f"Acme Bio Solutions {ts}",
        "businessArea": "WWT",
        "leadSource": "Inbound Call",
        "contactMethods": ["Phone"],
        "connectedDate": str(date.today())
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code == 201
    lead = res.json()["lead"]
    assert lead["leadName"] is None
    assert lead["companyName"] == f"Acme Bio Solutions {ts}"
    assert lead["displayName"] == lead["leadId"]  # Fallback display is leadId


def test_reject_when_both_topic_and_company_omitted(setup_reengineering_env):
    """Criteria 10: Reject when both Topic/Title and Company Name are omitted."""
    headers = setup_reengineering_env

    payload = {
        "businessArea": "Biogas",
        "leadSource": "Website",
        "contactMethods": ["Email"],
        "connectedDate": str(date.today())
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code in (400, 422)
    assert "Topic/Title or Company Name" in (res.json().get("message") or str(res.json().get("detail")))


def test_create_lead_without_requirement_type(setup_reengineering_env):
    """Criteria 6: A Lead can be saved without a Requirement Type."""
    headers = setup_reengineering_env
    ts = int(datetime.now(timezone.utc).timestamp())

    payload = {
        "topic": f"No Req Type Enquiry {ts}",
        "businessArea": "Biogas",
        "leadSource": "Trade Show / Expo",
        "contactMethods": ["Meeting"],
        "connectedDate": str(date.today()),
        "requirementTypes": []
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code == 201
    lead = res.json()["lead"]
    assert lead["requirementTypes"] == []
    assert lead["requirementType"] is None


def test_create_lead_with_all_three_requirement_types(setup_reengineering_env):
    """Criteria 7: A Lead can be saved with one, two, or all three Requirement Types."""
    headers = setup_reengineering_env
    ts = int(datetime.now(timezone.utc).timestamp())

    # All three types
    payload = {
        "topic": f"Triple Scope Enquiry {ts}",
        "companyName": f"Enterprise Org {ts}",
        "businessArea": "Biogas",
        "leadSource": "Referral",
        "contactMethods": ["Email", "Phone", "WhatsApp"],
        "preferredContactMethod": "WhatsApp",
        "connectedDate": str(date.today()),
        "requirementTypes": ["Consulting", "Sample Testing", "Product"]
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code == 201
    lead = res.json()["lead"]
    assert set(lead["requirementTypes"]) == {"Consulting", "Sample Testing", "Product"}
    assert "Consulting" in lead["requirementType"]
    assert lead["preferredContactMethod"] == "WhatsApp"


def test_create_lead_with_additional_contacts_omitted(setup_reengineering_env):
    """Criteria 8: A Lead can be saved with optional additional contacts omitted."""
    headers = setup_reengineering_env
    ts = int(datetime.now(timezone.utc).timestamp())

    payload = {
        "topic": f"Single Contact Lead {ts}",
        "firstName": "Siddharth",
        "lastName": "Mehta",
        "contactEmail": f"sid_{ts}@mehta.test",
        "companyName": f"Mehta Industries {ts}",
        "businessArea": "Biogas",
        "leadSource": "Cold Outreach",
        "contactMethods": ["Email", "Phone"],
        "connectedDate": str(date.today())
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code == 201
    lead = res.json()["lead"]
    assert lead["additionalContacts"] == []
    assert lead["contactEmail"] == f"sid_{ts}@mehta.test"


def test_duplicate_lead_names_accepted(setup_reengineering_env):
    """Criteria 9: Duplicate Lead names and legitimate repeat enquiries are accepted with unique IDs."""
    headers = setup_reengineering_env
    ts = int(datetime.now(timezone.utc).timestamp())
    shared_title = f"Duplicate Name Test {ts}"

    payload1 = {
        "topic": shared_title,
        "companyName": f"Client Alpha {ts}",
        "businessArea": "Biogas",
        "leadSource": "Website",
        "contactMethods": ["Email"],
        "connectedDate": str(date.today())
    }
    payload2 = {
        "topic": shared_title,
        "companyName": f"Client Beta {ts}",
        "businessArea": "WWT",
        "leadSource": "Email Received",
        "contactMethods": ["Phone"],
        "connectedDate": str(date.today())
    }

    res1 = client.post("/api/v1/crm/leads", json=payload1, headers=headers)
    res2 = client.post("/api/v1/crm/leads", json=payload2, headers=headers)
    assert res1.status_code == 201
    assert res2.status_code == 201

    lead1 = res1.json()["lead"]
    lead2 = res2.json()["lead"]
    assert lead1["leadName"] == shared_title
    assert lead2["leadName"] == shared_title
    assert lead1["leadId"] != lead2["leadId"]


def test_lead_details_persistence_on_reload(setup_reengineering_env):
    """Criteria 14: Saved Lead details survive reload and match API response."""
    headers = setup_reengineering_env
    ts = int(datetime.now(timezone.utc).timestamp())

    payload = {
        "topic": f"Persistence Test {ts}",
        "firstName": "Ananya",
        "lastName": "Sharma",
        "jobTitle": "Head of Sustainability",
        "businessPhone": "+91 22 5555 1234",
        "mobilePhone": "+91 98765 43210",
        "contactEmail": f"ananya_{ts}@green.test",
        "companyName": f"Green Future Corp {ts}",
        "websiteLink": "https://greenfuture.test",
        "location": "Pune, Maharashtra",
        "communicationChannel": "Email",
        "connectedDate": str(date.today()),
        "companyEmail": f"info_{ts}@greenfuture.test",
        "leadSource": "In-Person Meeting",
        "rating": "Hot",
        "clientStatus": "New",
        "description": "Comprehensive biogas plant evaluation and trial testing request.",
        "industry": "Renewable Energy",
        "numberOfEmployees": 250,
        "currency": "INR",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting", "Product"],
        "contactMethods": ["Email", "WhatsApp"],
        "preferredContactMethod": "Email"
    }

    create_res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert create_res.status_code == 201
    created_lead = create_res.json()["lead"]
    lead_id = created_lead["id"]

    # Reload via GET
    get_res = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert get_res.status_code == 200
    fetched_lead = get_res.json()["lead"]

    assert fetched_lead["leadName"] == payload["topic"]
    assert fetched_lead["firstName"] == "Ananya"
    assert fetched_lead["lastName"] == "Sharma"
    assert fetched_lead["jobTitle"] == "Head of Sustainability"
    assert fetched_lead["contactEmail"] == f"ananya_{ts}@green.test"
    assert fetched_lead["companyName"] == f"Green Future Corp {ts}"
    assert fetched_lead["websiteLink"] == "https://greenfuture.test"
    assert fetched_lead["location"] == "Pune, Maharashtra"
    assert fetched_lead["connectedDate"] == str(date.today())
    assert fetched_lead["companyEmail"] == f"info_{ts}@greenfuture.test"
    assert fetched_lead["leadSource"] == "In-Person Meeting"
    assert fetched_lead["rating"] == "Hot"
    assert fetched_lead["clientStatus"] == "New"
    assert fetched_lead["industry"] == "Renewable Energy"
    assert fetched_lead["numberOfEmployees"] == 250
    assert fetched_lead["currency"] == "INR"
    assert set(fetched_lead["requirementTypes"]) == {"Consulting", "Product"}
    assert set(fetched_lead["contactMethods"]) == {"Email", "WhatsApp"}
    assert fetched_lead["preferredContactMethod"] == "Email"
