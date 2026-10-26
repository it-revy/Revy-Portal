import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.crm.model import Account, Contact, Lead, Opportunity
from app.crm.service import CrmService
from app.crm.schema import LeadQualifyRequest, LeadQualifyAccountChoice, LeadQualifyContactChoice
from app.core.database import SessionLocal, Base
from app.users.model import User

client = TestClient(app)


@pytest.fixture
def auth_headers():
    res = client.post("/api/v1/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "CRM_SALES_MANAGER"
    }


def test_lead_qualification_creates_account_with_site_name_and_business_phone(auth_headers):
    """
    Verify:
    1. New Account receives Lead's site_name.
    2. Business Phone maps to Account Phone, NEVER Contact Mobile Number.
    3. Company Email maps to Account Email, NEVER Contact Email.
    4. Mobile Phone maps to Contact Mobile Number.
    5. Personal Email maps to Contact Email.
    """
    uid = uuid.uuid4().hex[:8]
    lead_payload = {
        "topic": f"Site Mapping Lead {uid}",
        "companyName": f"Gujarat Bio Refineries {uid}",
        "siteName": f"Dahej Plant Site {uid}",
        "businessPhone": "+91 261 4001122",
        "companyEmail": f"info_{uid}@gujaratbio.com",
        "websiteLink": "https://gujaratbio.example.com",
        "location": "Dahej PCPIR, Bharuch",
        "firstName": "Arun",
        "lastName": f"Patel {uid}",
        "jobTitle": "Chief Operations Officer",
        "mobilePhone": "+91 98250 99887",
        "contactEmail": f"arun_{uid}@gujaratbio.com",
        "requirementTypes": ["Consulting", "Sample Testing"],
        "businessArea": "Biogas"
    }

    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code == 201, f"Lead creation failed: {create_res.text}"
    lead = create_res.json()["lead"]
    assert lead["siteName"] == f"Dahej Plant Site {uid}"
    assert lead["businessPhone"] == "+91 261 4001122"
    assert lead["mobilePhone"] == "+91 98250 99887"

    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"Gujarat Bio Refineries {uid}",
            "siteName": f"Dahej Plant Site {uid}",
            "phone": "+91 261 4001122",
            "email": f"info_{uid}@gujaratbio.com",
            "website": "https://gujaratbio.example.com"
        },
        "contact": {
            "action": "create",
            "name": f"Arun Patel {uid}",
            "designation": "Chief Operations Officer",
            "email": f"arun_{uid}@gujaratbio.com",
            "mobileNumber": "+91 98250 99887"
        },
        "opportunityName": f"Bio Refinery Opportunity {uid}",
        "estimatedValue": 1250000.0,
        "opportunityDescription": "Comprehensive biogas consulting and sample testing"
    }

    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=auth_headers)
    assert q_res.status_code == 200, f"Qualification failed: {q_res.text}"
    q_data = q_res.json()

    # Verify Account returned in qualification response
    acc_data = q_data["account"]
    assert acc_data["siteName"] == f"Dahej Plant Site {uid}"
    assert acc_data["phone"] == "+91 261 4001122"
    assert acc_data["email"] == f"info_{uid}@gujaratbio.com"

    # Verify Contact returned in qualification response
    con_data = q_data["contact"]
    assert con_data["name"] == f"Arun Patel {uid}"

    # Verify database directly
    with SessionLocal() as db:
        acc_db = db.query(Account).filter(Account.id == acc_data["id"]).first()
        assert acc_db is not None
        assert acc_db.site_name == f"Dahej Plant Site {uid}"
        assert acc_db.phone == "+91 261 4001122"
        assert acc_db.email == f"info_{uid}@gujaratbio.com"

        con_db = db.query(Contact).filter(Contact.id == con_data["id"]).first()
        assert con_db is not None
        assert con_db.mobile_number == "+91 98250 99887"
        assert con_db.email == f"arun_{uid}@gujaratbio.com"
        # Business phone must NEVER populate Contact.mobile_number
        assert con_db.mobile_number != lead["businessPhone"]
        # Company email must NEVER populate Contact.email
        assert con_db.email != lead["companyEmail"]

        # Verify Opportunity link
        opp_db = db.query(Opportunity).filter(Opportunity.id == q_data["opportunity"]["id"]).first()
        assert opp_db is not None
        assert opp_db.account_id == acc_db.id
        assert opp_db.contact_id == con_db.id
        assert opp_db.originating_lead_id == lead["id"]


def test_missing_site_name_remains_valid(auth_headers):
    """
    Verify qualification succeeds when site_name is omitted or empty.
    """
    uid = uuid.uuid4().hex[:8]
    lead_payload = {
        "topic": f"No Site Lead {uid}",
        "companyName": f"Simple Bio {uid}",
        "businessPhone": "+91 11 2233 4455",
        "contactEmail": f"contact_{uid}@simplebio.com",
        "firstName": "Pooja",
        "lastName": f"Sharma {uid}",
        "mobilePhone": "+91 98111 22334"
    }

    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code == 201
    lead = create_res.json()["lead"]
    assert lead["siteName"] is None or lead["siteName"] == ""

    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"Simple Bio {uid}"
        },
        "contact": {
            "action": "create",
            "name": f"Pooja Sharma {uid}",
            "email": f"contact_{uid}@simplebio.com",
            "mobileNumber": "+91 98111 22334"
        },
        "opportunityName": f"Simple Opportunity {uid}"
    }

    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=auth_headers)
    assert q_res.status_code == 200
    acc_id = q_res.json()["account"]["id"]

    with SessionLocal() as db:
        acc_db = db.query(Account).filter(Account.id == acc_id).first()
        assert acc_db.site_name is None
        assert acc_db.phone == "+91 11 2233 4455"


def test_existing_account_reuse_preserves_site_name_without_overwrite(auth_headers):
    """
    Verify that reusing an existing Account:
    1. Preserves existing Account site_name when no siteName override is sent.
    2. Updates Account site_name only when the user explicitly provides a new siteName.
    """
    uid = uuid.uuid4().hex[:8]

    # Create canonical Account directly
    with SessionLocal() as db:
        acc = Account(
            account_id=f"ACC-TEST-{uid}",
            name=f"Existing Enterprise {uid}",
            site_name=f"Canonical Main Plant {uid}",
            phone="+91 22 8888 1111",
            email=f"corp_{uid}@enterprise.com",
            is_active=True
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        acc_id = acc.id

    # Create Lead with different site name
    lead_payload = {
        "topic": f"Site Reuse Lead {uid}",
        "companyName": f"Existing Enterprise {uid}",
        "siteName": f"Proposed Satellite Site {uid}",
        "contactEmail": f"lead_{uid}@enterprise.com",
        "firstName": "Vikram",
        "lastName": f"Mehta {uid}",
        "mobilePhone": "+91 97000 12345"
    }
    lead_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert lead_res.status_code == 201
    lead = lead_res.json()["lead"]

    # Case 1: Reuse existing account without explicitly changing siteName
    qualify_payload_1 = {
        "account": {
            "action": "reuse",
            "accountId": acc_id
        },
        "contact": {
            "action": "create",
            "name": f"Vikram Mehta {uid}",
            "email": f"vikram_{uid}@enterprise.com",
            "mobileNumber": "+91 97000 12345"
        },
        "opportunityName": f"Preserve Site Opp {uid}"
    }

    q1_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload_1, headers=auth_headers)
    assert q1_res.status_code == 200

    # Ensure canonical site name was NOT overwritten
    with SessionLocal() as db:
        acc_db = db.query(Account).filter(Account.id == acc_id).first()
        assert acc_db.site_name == f"Canonical Main Plant {uid}"
        assert acc_db.phone == "+91 22 8888 1111"

    # Case 2: Create another Lead and qualify with explicit new siteName choice
    uid2 = uuid.uuid4().hex[:8]
    lead2_payload = {
        "topic": f"Explicit Site Update Lead {uid2}",
        "companyName": f"Existing Enterprise {uid}",
        "siteName": f"Updated Phase 2 Site {uid2}",
        "contactEmail": f"lead2_{uid2}@enterprise.com",
        "firstName": "Ramesh",
        "lastName": f"Gupta {uid2}",
        "mobilePhone": "+91 97000 67890"
    }
    lead2_res = client.post("/api/v1/crm/leads", json=lead2_payload, headers=auth_headers)
    assert lead2_res.status_code == 201
    lead2 = lead2_res.json()["lead"]

    qualify_payload_2 = {
        "account": {
            "action": "reuse",
            "accountId": acc_id,
            "siteName": f"Updated Phase 2 Site {uid2}"  # Explicit user decision
        },
        "contact": {
            "action": "create",
            "name": f"Ramesh Gupta {uid2}",
            "email": f"ramesh_{uid2}@enterprise.com",
            "mobileNumber": "+91 97000 67890"
        },
        "opportunityName": f"Explicit Update Opp {uid2}"
    }
    q2_res = client.post(f"/api/v1/crm/leads/{lead2['id']}/qualify", json=qualify_payload_2, headers=auth_headers)
    assert q2_res.status_code == 200

    with SessionLocal() as db:
        acc_db = db.query(Account).filter(Account.id == acc_id).first()
        assert acc_db.site_name == f"Updated Phase 2 Site {uid2}"


def test_concurrent_qualification_attempts_creates_exactly_one_opportunity(auth_headers):
    """
    Verify: Two concurrent qualification requests for the same Lead:
    - Both return HTTP 200 (one executes the qualification, the other receives idempotent response)
    - Exactly ONE Opportunity is created in database
    - Exactly ONE Account and Contact are created
    """
    uid = uuid.uuid4().hex[:8]
    lead_payload = {
        "topic": f"Concurrent Lock Lead {uid}",
        "companyName": f"Concurrent Lock Bio {uid}",
        "siteName": f"Concurrent Site {uid}",
        "businessPhone": "+91 22 7700 8899",
        "companyEmail": f"info_{uid}@concurrentlock.com",
        "firstName": "Sanjay",
        "lastName": f"Verma {uid}",
        "mobilePhone": "+91 98999 11223",
        "contactEmail": f"sanjay_{uid}@concurrentlock.com"
    }

    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code == 201
    lead = create_res.json()["lead"]

    qualify_payload = {
        "account": {
            "action": "create",
            "name": f"Concurrent Lock Bio {uid}",
            "siteName": f"Concurrent Site {uid}",
            "phone": "+91 22 7700 8899",
            "email": f"info_{uid}@concurrentlock.com"
        },
        "contact": {
            "action": "create",
            "name": f"Sanjay Verma {uid}",
            "email": f"sanjay_{uid}@concurrentlock.com",
            "mobileNumber": "+91 98999 11223"
        },
        "opportunityName": f"Concurrent Lock Opp {uid}"
    }

    def do_qualify():
        return client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=auth_headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_qualify)
        f2 = executor.submit(do_qualify)
        r1 = f1.result()
        r2 = f2.result()

    assert r1.status_code == 200, f"Req 1 failed: {r1.text}"
    assert r2.status_code == 200, f"Req 2 failed: {r2.text}"

    opp1_id = r1.json()["opportunity"]["id"]
    opp2_id = r2.json()["opportunity"]["id"]
    assert opp1_id == opp2_id, "Both requests must resolve to the identical Opportunity ID"

    with SessionLocal() as db:
        opp_count = db.query(Opportunity).filter(Opportunity.originating_lead_id == lead["id"]).count()
        assert opp_count == 1, "Exactly one Opportunity must exist for this Lead"


def test_contact_reuse_preserves_existing_contact_data(auth_headers):
    """
    Verify:
    1. Reusing an existing Contact preserves its existing phone and email.
    2. Lead's business phone and company email NEVER overwrite the reused contact.
    """
    uid = uuid.uuid4().hex[:8]

    # Create canonical Account and Contact
    with SessionLocal() as db:
        acc = Account(
            account_id=f"ACC-CON-{uid}",
            name=f"Existing Firm {uid}",
            site_name=f"Firm Site {uid}",
            phone="+91 22 3344 5566",
            email=f"firm_{uid}@example.com",
            is_active=True
        )
        db.add(acc)
        db.flush()

        con = Contact(
            contact_id=f"CON-PRESERVE-{uid}",
            account_id=acc.id,
            name=f"Deepak Shah {uid}",
            email=f"deepak_{uid}@example.com",
            mobile_number="+91 98111 55443",
            designation="VP Technology",
            is_active=True
        )
        db.add(con)
        db.commit()
        db.refresh(acc)
        db.refresh(con)
        acc_id = acc.id
        con_id = con.id

    # Create Lead with different business phone and company email
    lead_payload = {
        "topic": f"Contact Reuse Lead {uid}",
        "companyName": f"Existing Firm {uid}",
        "businessPhone": "+91 22 9999 0000",
        "companyEmail": f"corporate_{uid}@example.com",
        "firstName": "Deepak",
        "lastName": f"Shah {uid}",
        "mobilePhone": "+91 98111 55443",
        "contactEmail": f"deepak_{uid}@example.com"
    }
    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code == 201
    lead = create_res.json()["lead"]

    qualify_payload = {
        "account": {
            "action": "reuse",
            "accountId": acc_id
        },
        "contact": {
            "action": "reuse",
            "contactId": con_id
        },
        "opportunityName": f"Preserve Contact Opp {uid}"
    }

    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=qualify_payload, headers=auth_headers)
    assert q_res.status_code == 200

    with SessionLocal() as db:
        con_db = db.query(Contact).filter(Contact.id == con_id).first()
        assert con_db.email == f"deepak_{uid}@example.com"
        assert con_db.mobile_number == "+91 98111 55443"
        assert con_db.mobile_number != lead_payload["businessPhone"]
        assert con_db.email != lead_payload["companyEmail"]


def test_qualification_transaction_rollback_on_failure(auth_headers):
    """
    Verify: A business logic failure during qualification rolls back all database modifications:
    - Lead remains 'Open'
    - No orphan Opportunity is created
    """
    uid = uuid.uuid4().hex[:8]
    lead_payload = {
        "topic": f"Rollback Test Lead {uid}",
        "companyName": f"Rollback Enterprise {uid}",
        "contactEmail": f"contact_{uid}@rollback.com",
        "firstName": "Anand",
        "lastName": f"Kumar {uid}"
    }
    create_res = client.post("/api/v1/crm/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code == 201
    lead = create_res.json()["lead"]

    # Attempt to qualify with an invalid account action to trigger a ValidationError
    invalid_qualify_payload = {
        "account": {
            "action": "invalid_action_choice"
        },
        "contact": {
            "action": "create",
            "name": f"Anand Kumar {uid}"
        },
        "opportunityName": f"Should Not Exist Opp {uid}"
    }

    q_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json=invalid_qualify_payload, headers=auth_headers)
    assert q_res.status_code in [400, 422]

    # Verify rollback in database
    with SessionLocal() as db:
        reloaded_lead = db.query(Lead).filter(Lead.id == lead["id"]).first()
        assert reloaded_lead.lifecycle_status == "Open"
        assert reloaded_lead.opportunity_id is None
        opp_count = db.query(Opportunity).filter(Opportunity.originating_lead_id == lead["id"]).count()
        assert opp_count == 0


def test_postgresql_qualification_without_outer_join_error():
    """
    Direct PostgreSQL regression test:
    Connects directly to PostgreSQL using DATABASE_URL from .env.
    Executes qualify_lead() to empirically verify:
    1. with_for_update(of=Lead) with selectinload does NOT produce:
       psycopg2.errors.FeatureNotSupported: FOR UPDATE cannot be applied to the nullable side of an outer join
    2. Concurrency row lock on Lead succeeds.
    3. Account, Contact, and Opportunity are created atomically.
    4. Idempotency on repeated qualification returns existing opportunity.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url or "sqlite" in db_url.lower():
        # Fall back to testing .env DATABASE_URL if in test mode
        from dotenv import dotenv_values
        env_dict = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env"))
        db_url = env_dict.get("DATABASE_URL")

    if not db_url or "postgresql" not in db_url.lower():
        pytest.skip("PostgreSQL DATABASE_URL not available; skipping live PostgreSQL integration test.")

    pg_engine = create_engine(db_url, pool_pre_ping=True)
    PgSession = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

    uid = uuid.uuid4().hex[:8]
    lead_id = f"LEAD-PG-{uid}"

    with PgSession() as db:
        # Resolve actor user
        actor = db.query(User).filter(User.username == "vasudev").first()
        if not actor:
            actor = db.query(User).first()
        assert actor is not None, "No user found in PostgreSQL for qualification test"

        # Create a fresh Lead with relationships
        new_lead = Lead(
            lead_id=lead_id,
            lead_name=f"PostgreSQL Outer Join Test Lead {uid}",
            company_name=f"PG Industries {uid}",
            site_name=f"PG Chemical Plant {uid}",
            business_phone="+91 22 4433 2211",
            company_email=f"corp_{uid}@pgindustries.com",
            mobile_phone="+91 99887 76655",
            contact_email=f"vp_{uid}@pgindustries.com",
            lifecycle_status="Open",
            business_area="Biogas"
        )
        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)

        service = CrmService(db)

        # Qualify the lead
        qual_req = LeadQualifyRequest(
            account=LeadQualifyAccountChoice(
                action="create",
                name=f"PG Industries {uid}",
                siteName=f"PG Chemical Plant {uid}",
                phone="+91 22 4433 2211",
                email=f"corp_{uid}@pgindustries.com"
            ),
            contact=LeadQualifyContactChoice(
                action="create",
                name=f"VP Operations {uid}",
                email=f"vp_{uid}@pgindustries.com",
                mobileNumber="+91 99887 76655"
            ),
            opportunityName=f"PG Opportunity {uid}",
            estimatedValue=500000.0,
            opportunityDescription="PostgreSQL verification of outer-join row-locking fix"
        )

        # THIS IS THE CRITICAL LINE THAT PREVIOUSLY FAILED WITH psycopg2.errors.FeatureNotSupported
        result = service.qualify_lead(
            actor=actor,
            lead_id=new_lead.id,
            payload=qual_req
        )

        assert result["success"] is True
        assert result["account"]["siteName"] == f"PG Chemical Plant {uid}"
        assert result["account"]["phone"] == "+91 22 4433 2211"
        assert result["opportunity"]["name"] == f"PG Opportunity {uid}"

        # Re-check database state
        db.expire_all()
        reloaded_lead = db.query(Lead).filter(Lead.id == new_lead.id).first()
        assert reloaded_lead.lifecycle_status == "Qualified"
        assert reloaded_lead.account_id is not None
        assert reloaded_lead.opportunity_id is not None

        # Verify idempotency retry on PostgreSQL
        retry_result = service.qualify_lead(
            actor=actor,
            lead_id=new_lead.id,
            payload=qual_req
        )
        assert retry_result["success"] is True
        assert "already qualified" in retry_result["message"]
        assert retry_result["opportunity"]["id"] == result["opportunity"]["id"]
