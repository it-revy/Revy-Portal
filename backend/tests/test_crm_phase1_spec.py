import os
import sys
import pytest
from decimal import Decimal
from datetime import datetime, timezone, date, timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.crm.model import (
    Account, Contact, Lead, LeadRequirementType,
    ConsultingEngagement, SampleSubmission, SampleTestRequest, TestingChargeRecord, ProductTransaction
)
from app.crm import service as crm_service
from app.core.security import get_password_hash
from app.core.init_roles import ensure_roles_and_permissions
from app.core.init_modules import ensure_modules_and_memberships

client = TestClient(app)

_TOKEN_CACHE = {}


def get_token_headers(username, password, role_used=None):
    cache_key = (username, password)
    if cache_key not in _TOKEN_CACHE:
        res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert res.status_code == 200, f"Login failed for {username}: {res.text}"
        _TOKEN_CACHE[cache_key] = res.json()["token"]

    token = _TOKEN_CACHE[cache_key]
    headers = {"Authorization": f"Bearer {token}"}
    if role_used:
        headers["X-Role-Used"] = role_used
    return headers


@pytest.fixture(scope="module")
def setup_phase1_environment():
    """Ensure roles, permissions, modules, and test users exist."""
    db = SessionLocal()
    try:
        crm_mod = db.query(Module).filter(Module.code == "CRM").first()
        if not crm_mod:
            ensure_roles_and_permissions()
            ensure_modules_and_memberships()
            crm_mod = db.query(Module).filter(Module.code == "CRM").first()
        assert crm_mod is not None, "CRM module must exist"

        role_admin = db.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_ADMIN").first()
        role_sales_mgr = db.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_SALES_MANAGER").first()
        role_sales_exec = db.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_SALES_EXECUTIVE").first()

        # Admin user
        u_admin = db.query(User).filter(User.username == "p1_crm_admin").first()
        if not u_admin:
            u_admin = User(name="Phase1 Admin", username="p1_crm_admin", email="p1_admin@revy.test", password_hash=get_password_hash("Pass123!"), status="active")
            db.add(u_admin)
            db.commit()
            db.refresh(u_admin)
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == u_admin.id).delete()
        db.add(UserModuleMembership(user_id=u_admin.id, module_id=crm_mod.id, role_id=role_admin.id, is_active=True))

        # Sales Manager
        u_mgr = db.query(User).filter(User.username == "p1_sales_mgr").first()
        if not u_mgr:
            u_mgr = User(name="Phase1 Manager", username="p1_sales_mgr", email="p1_mgr@revy.test", password_hash=get_password_hash("Pass123!"), status="active")
            db.add(u_mgr)
            db.commit()
            db.refresh(u_mgr)
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == u_mgr.id).delete()
        db.add(UserModuleMembership(user_id=u_mgr.id, module_id=crm_mod.id, role_id=role_sales_mgr.id, is_active=True))

        # Non-CRM user (BMS employee only)
        bms_mod = db.query(Module).filter(Module.code == "BMS").first()
        bms_role = db.query(ModuleRole).filter(ModuleRole.module_id == bms_mod.id, ModuleRole.code == "BMS_EMPLOYEE").first() if bms_mod else None
        u_non = db.query(User).filter(User.username == "p1_non_crm").first()
        if not u_non:
            u_non = User(name="Phase1 Non CRM", username="p1_non_crm", email="p1_non@revy.test", password_hash=get_password_hash("Pass123!"), status="active")
            db.add(u_non)
            db.commit()
            db.refresh(u_non)
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == u_non.id).delete()
        if bms_mod and bms_role:
            db.add(UserModuleMembership(user_id=u_non.id, module_id=bms_mod.id, role_id=bms_role.id, is_active=True))

        db.commit()
    finally:
        db.close()


# =========================================================================
# 1. REQUIREMENT TYPES: EXACTLY THREE MULTI-SELECT OPTIONS
# =========================================================================

def test_requirement_types_individual_and_combinations(setup_phase1_environment):
    headers = get_token_headers("p1_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create account and contact
    res_acc = client.post("/api/v1/crm/accounts", json={"name": f"ReqType Client {ts}"}, headers=headers)
    assert res_acc.status_code == 201
    acc_id = res_acc.json()["account"]["id"]

    res_con = client.post("/api/v1/crm/contacts", json={"name": f"ReqType Contact {ts}", "accountId": acc_id, "email": f"req_{ts}@client.test"}, headers=headers)
    assert res_con.status_code == 201
    con_id = res_con.json()["contact"]["id"]

    # 1. Consulting only
    res1 = client.post("/api/v1/crm/leads", json={
        "leadName": f"Consulting Lead {ts}",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting"],
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res1.status_code == 201
    lead1 = res1.json()["lead"]
    assert lead1["requirementTypes"] == ["Consulting"]
    assert lead1["requirementType"] == "Consulting"

    # 2. Sample Testing only
    res2 = client.post("/api/v1/crm/leads", json={
        "leadName": f"Sample Testing Lead {ts}",
        "businessArea": "WWT",
        "requirementTypes": ["Sample Testing"],
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res2.status_code == 201
    lead2 = res2.json()["lead"]
    assert lead2["requirementTypes"] == ["Sample Testing"]

    # 3. Product only
    res3 = client.post("/api/v1/crm/leads", json={
        "leadName": f"Product Lead {ts}",
        "businessArea": "Biogas",
        "requirementTypes": ["Product"],
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res3.status_code == 201
    lead3 = res3.json()["lead"]
    assert lead3["requirementTypes"] == ["Product"]

    # 4. Multi-select: Consulting + Sample Testing
    res4 = client.post("/api/v1/crm/leads", json={
        "leadName": f"Consulting and Testing Lead {ts}",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting", "Sample Testing"],
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res4.status_code == 201
    lead4 = res4.json()["lead"]
    assert set(lead4["requirementTypes"]) == {"Consulting", "Sample Testing"}

    # 5. Multi-select: All three (Consulting, Sample Testing, Product)
    res5 = client.post("/api/v1/crm/leads", json={
        "leadName": f"All Three Types Lead {ts}",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting", "Sample Testing", "Product"],
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res5.status_code == 201
    lead5 = res5.json()["lead"]
    assert set(lead5["requirementTypes"]) == {"Consulting", "Sample Testing", "Product"}

    # 6. Update saved requirement types
    res_upd = client.put(f"/api/v1/crm/leads/{lead1['id']}", json={
        "requirementTypes": ["Product", "Consulting"]
    }, headers=headers)
    assert res_upd.status_code == 200
    updated_lead = res_upd.json()["lead"]
    assert set(updated_lead["requirementTypes"]) == {"Product", "Consulting"}

    # Verify retrieval
    res_get = client.get(f"/api/v1/crm/leads/{lead1['id']}", headers=headers)
    assert res_get.status_code == 200
    assert set(res_get.json()["lead"]["requirementTypes"]) == {"Product", "Consulting"}


def test_requirement_types_validation(setup_phase1_environment):
    headers = get_token_headers("p1_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    res_con = client.post("/api/v1/crm/contacts", json={"name": f"Val Contact {ts}", "email": f"val_{ts}@test.com"}, headers=headers)
    con_id = res_con.json()["contact"]["id"]

    # Reject invalid requirement value
    res_invalid = client.post("/api/v1/crm/leads", json={
        "businessArea": "Biogas",
        "requirementTypes": ["InvalidType"],
        "contactId": con_id
    }, headers=headers)
    assert res_invalid.status_code in (400, 422)

    # Saving lead without requirement selection is now permitted in Phase 1
    res_empty = client.post("/api/v1/crm/leads", json={
        "businessArea": "Biogas",
        "requirementTypes": [],
        "contactId": con_id
    }, headers=headers)
    assert res_empty.status_code == 201
    lead_empty = res_empty.json()["lead"]
    assert lead_empty["requirementTypes"] == []
    assert lead_empty["requirementType"] is None


# =========================================================================
# 2. OPTIONAL LEAD TITLE AND DUPLICATE RESTRICTION REMOVAL
# =========================================================================

def test_optional_lead_title_and_display_fallback(setup_phase1_environment):
    headers = get_token_headers("p1_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    res_con = client.post("/api/v1/crm/contacts", json={"name": f"Title Contact {ts}", "email": f"title_{ts}@test.com"}, headers=headers)
    con_id = res_con.json()["contact"]["id"]

    # 1. Lead created without title (omitted)
    res_notitle = client.post("/api/v1/crm/leads", json={
        "businessArea": "Biogas",
        "requirementTypes": ["Sample Testing"],
        "contactId": con_id
    }, headers=headers)
    assert res_notitle.status_code == 201
    lead_data = res_notitle.json()["lead"]
    assert lead_data["leadName"] is None or lead_data["leadName"] == ""
    assert lead_data["displayName"] == lead_data["leadId"]  # fallback display

    # 2. Lead created with blank string title
    res_blank = client.post("/api/v1/crm/leads", json={
        "leadName": "   ",
        "businessArea": "WWT",
        "requirementTypes": ["Product"],
        "contactId": con_id
    }, headers=headers)
    assert res_blank.status_code == 201
    assert res_blank.json()["lead"]["displayName"] == res_blank.json()["lead"]["leadId"]


def test_duplicate_leads_permitted_with_unique_ids(setup_phase1_environment):
    headers = get_token_headers("p1_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    res_acc = client.post("/api/v1/crm/accounts", json={"name": f"Dup Account {ts}"}, headers=headers)
    acc_id = res_acc.json()["account"]["id"]
    res_con = client.post("/api/v1/crm/contacts", json={"name": f"Dup Contact {ts}", "accountId": acc_id, "email": f"dup_{ts}@client.test"}, headers=headers)
    con_id = res_con.json()["contact"]["id"]

    same_title = f"Identical Title Lead {ts}"
    same_requirements = ["Consulting", "Sample Testing"]

    # Create Lead 1
    res1 = client.post("/api/v1/crm/leads", json={
        "leadName": same_title,
        "businessArea": "Biogas",
        "requirementTypes": same_requirements,
        "accountId": acc_id,
        "contactId": con_id
    }, headers=headers)
    assert res1.status_code == 201
    id1 = res1.json()["lead"]["id"]
    lead_num1 = res1.json()["lead"]["leadId"]

    # Create Lead 2: SAME account, SAME contact, SAME title, SAME requirement selections -> MUST SUCCEED (201)
    res2 = client.post("/api/v1/crm/leads", json={
        "leadName": same_title,
        "businessArea": "Biogas",
        "requirementTypes": same_requirements,
        "accountId": acc_id,
        "contactId": con_id
    }, headers=headers)
    assert res2.status_code == 201, f"Expected duplicate lead creation to succeed, got: {res2.text}"
    id2 = res2.json()["lead"]["id"]
    lead_num2 = res2.json()["lead"]["leadId"]

    # IDs must be unique
    assert id1 != id2
    assert lead_num1 != lead_num2
    assert lead_num1.startswith("LEAD-")
    assert lead_num2.startswith("LEAD-")


# =========================================================================
# 3. ACCOUNT AND CONTACT CRUD & RELATIONSHIPS
# =========================================================================

def test_account_crud_and_related_entities(setup_phase1_environment):
    headers = get_token_headers("p1_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create Account
    res_create = client.post("/api/v1/crm/accounts", json={
        "name": f"Enterprise Corp {ts}",
        "industry": "Renewables",
        "website": "enterprisecorp.com",
        "phone": "+91 9876543210",
        "email": f"info_{ts}@enterprisecorp.com",
        "address": "Plot 42, Green Tech Park",
        "location": "Vadodara, Gujarat"
    }, headers=headers)
    assert res_create.status_code == 201
    acc = res_create.json()["account"]
    acc_id = acc["id"]
    assert acc["accountId"].startswith("ACC-")

    # Update Account (PUT /crm/accounts/{id})
    res_update = client.put(f"/api/v1/crm/accounts/{acc_id}", json={
        "name": f"Enterprise Corp International {ts}",
        "industry": "Clean Energy & Biofuels",
        "website": "enterprisecorp-intl.com",
        "location": "Ahmedabad, Gujarat",
        "isActive": True
    }, headers=headers)
    assert res_update.status_code == 200
    updated_acc = res_update.json()["account"]
    assert updated_acc["name"] == f"Enterprise Corp International {ts}"
    assert updated_acc["industry"] == "Clean Energy & Biofuels"

    # Associate Contacts to Account
    res_con1 = client.post("/api/v1/crm/contacts", json={"name": f"Contact A {ts}", "accountId": acc_id, "email": f"ca_{ts}@ent.com"}, headers=headers)
    assert res_con1.status_code == 201
    res_con2 = client.post("/api/v1/crm/contacts", json={"name": f"Contact B {ts}", "accountId": acc_id, "email": f"cb_{ts}@ent.com"}, headers=headers)
    assert res_con2.status_code == 201

    # Link Lead to Account and Contact A
    res_lead = client.post("/api/v1/crm/leads", json={
        "leadName": f"Enterprise Account Lead {ts}",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting"],
        "accountId": acc_id,
        "contactId": res_con1.json()["contact"]["id"]
    }, headers=headers)
    assert res_lead.status_code == 201

    # Get Account Detail: must include contacts and leads
    res_get = client.get(f"/api/v1/crm/accounts/{acc_id}", headers=headers)
    assert res_get.status_code == 200
    acc_detail = res_get.json()["account"]
    assert len(acc_detail.get("contacts", [])) >= 2
    assert len(acc_detail.get("leads", [])) >= 1


def test_contact_crud_and_account_association(setup_phase1_environment):
    headers = get_token_headers("p1_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create Contact without Account (Direct Contact)
    res_direct = client.post("/api/v1/crm/contacts", json={
        "name": f"Direct Contact {ts}",
        "designation": "Plant Consultant",
        "email": f"direct_{ts}@consulting.test",
        "mobileNumber": f"+91 91234{ts % 100000:05d}"
    }, headers=headers)
    assert res_direct.status_code == 201
    contact_id = res_direct.json()["contact"]["id"]
    assert res_direct.json()["contact"]["contactId"].startswith("CON-")

    # Update Contact to associate with an Account (PUT /crm/contacts/{id})
    res_acc = client.post("/api/v1/crm/accounts", json={"name": f"Linked Org {ts}"}, headers=headers)
    acc_id = res_acc.json()["account"]["id"]

    res_update = client.put(f"/api/v1/crm/contacts/{contact_id}", json={
        "designation": "Chief Bio-Energy Scientist",
        "accountId": acc_id
    }, headers=headers)
    assert res_update.status_code == 200
    assert res_update.json()["contact"]["accountId"] == acc_id
    assert res_update.json()["contact"]["designation"] == "Chief Bio-Energy Scientist"

    # Get Contact Detail: check linked account and leads
    res_get = client.get(f"/api/v1/crm/contacts/{contact_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["contact"]["account"]["name"] == f"Linked Org {ts}"


def test_account_contact_relationship_consistency(setup_phase1_environment):
    headers = get_token_headers("p1_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Account 1 and its Contact
    res_acc1 = client.post("/api/v1/crm/accounts", json={"name": f"Account One {ts}"}, headers=headers)
    acc1_id = res_acc1.json()["account"]["id"]
    res_con1 = client.post("/api/v1/crm/contacts", json={"name": f"Contact One {ts}", "accountId": acc1_id, "email": f"c1_{ts}@one.com"}, headers=headers)
    con1_id = res_con1.json()["contact"]["id"]

    # Account 2
    res_acc2 = client.post("/api/v1/crm/accounts", json={"name": f"Account Two {ts}"}, headers=headers)
    acc2_id = res_acc2.json()["account"]["id"]

    # Attempt to create Lead with Account 2 but Contact 1 (belongs to Account 1) -> MUST REJECT (HTTP 400)
    res_mismatch = client.post("/api/v1/crm/leads", json={
        "businessArea": "Biogas",
        "requirementTypes": ["Product"],
        "accountId": acc2_id,
        "contactId": con1_id
    }, headers=headers)
    assert res_mismatch.status_code == 400
    assert "belongs to a different account" in res_mismatch.text.lower()


def test_crm_permissions_enforcement(setup_phase1_environment):
    # Non-CRM user attempting to create lead or edit account -> MUST BE REJECTED (HTTP 403)
    headers_non_crm = get_token_headers("p1_non_crm", "Pass123!", "BMS_EMPLOYEE")

    res = client.post("/api/v1/crm/leads", json={
        "businessArea": "Biogas",
        "requirementTypes": ["Product"],
        "contactId": "dummy-contact-id"
    }, headers=headers_non_crm)
    assert res.status_code == 403

    res_acc = client.post("/api/v1/crm/accounts", json={"name": "Forbidden Account"}, headers=headers_non_crm)
    assert res_acc.status_code == 403


# =========================================================================
# 4. CHARGE-READY DATA MODELS AND BUSINESS OPERATIONS
# =========================================================================

def test_charge_ready_models_and_calculations(setup_phase1_environment):
    db = SessionLocal()
    try:
        ts = int(datetime.now(timezone.utc).timestamp())

        # Setup lead with Account and Contact
        account = Account(account_id=f"ACC-TST-{ts}", name=f"Testing Client Org {ts}")
        db.add(account)
        db.commit()
        db.refresh(account)

        contact = Contact(contact_id=f"CON-TST-{ts}", name=f"Dr. Laboratory Client {ts}", account_id=account.id, email=f"lab_{ts}@client.test")
        db.add(contact)
        db.commit()
        db.refresh(contact)

        lead = Lead(
            lead_id=f"LEAD-TST-{ts}",
            business_area="Biogas",
            requirement_type="Sample Testing",
            account_id=account.id,
            contact_id=contact.id
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # 1. Sample Testing: Sample Submission with multiple Requested Tests
        submission = crm_service.create_sample_submission(
            db,
            sample_data={
                "lead_id": lead.id,
                "account_id": account.id,
                "contact_id": contact.id,
                "sample_description": "Anaerobic Digester Sludge (Digestant #1)",
                "sample_type": "Sludge",
                "sample_charge": Decimal("1500.00"),
                "sample_condition": "Sealed airtight container at 4°C"
            },
            tests_data=[
                {"test_type": "BOD_5_DAY", "test_rate": Decimal("850.50"), "billable_units": 1},
                {"test_type": "COD_REFLUX", "test_rate": Decimal("1200.00"), "billable_units": 1},
                {"test_type": "VOLATILE_FATTY_ACIDS", "test_rate": Decimal("2500.25"), "billable_units": 2}  # 2 * 2500.25 = 5000.50
            ]
        )
        assert submission.id is not None
        assert submission.sample_id.startswith("SMP-")
        assert len(submission.requested_tests) == 3

        # 2. Financial calculation: Sample charge + Test charges + Additional charges - Discount
        # Expected:
        # Sample charge: 1500.00
        # Test 1: 850.50
        # Test 2: 1200.00
        # Test 3: 5000.50 (2 * 2500.25)
        # Sum of tests: 7051.00
        # Additional charges: 350.00 (Express handling)
        # Discount: 500.00
        # Total: 1500.00 + 7051.00 + 350.00 - 500.00 = 8401.00
        calc = crm_service.calculate_testing_charges(
            db,
            sample_submission_id=submission.id,
            additional_charge=Decimal("350.00"),
            discount_amount=Decimal("500.00")
        )
        assert calc["sample_level_charge"] == Decimal("1500.00")
        assert calc["sum_of_test_charges"] == Decimal("7051.00")
        assert calc["additional_charges"] == Decimal("350.00")
        assert calc["discounts"] == Decimal("500.00")
        assert calc["total_charge"] == Decimal("8401.00")

        # 3. Record Charge with idempotency key and preserved historical rates
        charge_record = crm_service.record_testing_charge(
            db,
            sample_submission_id=submission.id,
            test_request_id=submission.requested_tests[0].id,
            charge_type="TEST_CHARGE",
            description="BOD 5-Day Analysis Agreed Rate",
            charge_amount=Decimal("850.50"),
            agreed_unit_rate=Decimal("850.50"),
            billable_units=1,
            idempotency_key=f"CHG-SMP-{submission.id}-TEST-1",
            applied_by_user_id=None
        )
        assert charge_record.id is not None
        assert charge_record.charge_id.startswith("CHG-")
        assert charge_record.agreed_unit_rate == Decimal("850.50")
        assert charge_record.charge_amount == Decimal("850.50")

        # Attempt duplicate billing with same idempotency key -> returns existing record safely
        dup_charge = crm_service.record_testing_charge(
            db,
            sample_submission_id=submission.id,
            test_request_id=submission.requested_tests[0].id,
            charge_type="TEST_CHARGE",
            description="BOD 5-Day Analysis Duplicate",
            charge_amount=Decimal("850.50"),
            idempotency_key=f"CHG-SMP-{submission.id}-TEST-1"
        )
        assert dup_charge.id == charge_record.id

        # 4. Failed / Unsuitable Sample Handling
        failed_submission = crm_service.create_sample_submission(
            db,
            sample_data={
                "lead_id": lead.id,
                "account_id": account.id,
                "contact_id": contact.id,
                "sample_description": "Effluent Sample from Tank B",
                "sample_status": "FAILED_SPOILED",
                "failure_reason": "Sample degraded and fermented in transit due to improper refrigeration",
                "stage_reached": "PRE_ANALYSIS_INSPECTION",
                "work_performed_notes": "Sample received spoiled, pH tested at 3.2. Retest requested from client.",
                "charge_decision": "HALF_CHARGE_APPLIED",
                "chargeable_amount": Decimal("750.00"),
                "billing_status": "AUTHORIZED"
            }
        )
        assert failed_submission.sample_status == "FAILED_SPOILED"
        assert failed_submission.failure_reason is not None
        assert failed_submission.chargeable_amount == Decimal("750.00")

        # Replacement sample references original failed sample
        replacement_submission = crm_service.create_sample_submission(
            db,
            sample_data={
                "lead_id": lead.id,
                "account_id": account.id,
                "contact_id": contact.id,
                "sample_description": "Replacement Effluent Sample from Tank B",
                "replacement_for_sample_id": failed_submission.id,
                "sample_charge": Decimal("1500.00")
            }
        )
        assert replacement_submission.replacement_for_sample_id == failed_submission.id

        # 5. Product Transactions (Recommendations vs Orders)
        prod_tx = crm_service.create_product_transaction(
            db,
            product_data={
                "lead_id": lead.id,
                "account_id": account.id,
                "contact_id": contact.id,
                "product_reference": "REVY-BIOMIX-L400",
                "status": "RECOMMENDED",
                "quantity": Decimal("500.00"),
                "unit_of_measure": "Litres",
                "unit_rate": Decimal("450.00"),
                "currency": "INR",
                "notes": "Recommended for inoculum startup phase"
            }
        )
        assert prod_tx.id is not None
        assert prod_tx.calculated_amount == Decimal("225000.00")  # 500 * 450
        assert prod_tx.status == "RECOMMENDED"

        # 6. Consulting Engagements (Configurable Billing Arrangement)
        engagement = crm_service.create_consulting_engagement(
            db,
            engagement_data={
                "lead_id": lead.id,
                "account_id": account.id,
                "contact_id": contact.id,
                "contract_start_date": date.today(),
                "contract_end_date": date.today() + timedelta(days=365),
                "duration_description": "1 Year Biogas Digester Performance Advisory",
                "agreed_fee": Decimal("600000.00"),
                "billing_arrangement": "QUARTERLY_MILESTONE",  # configurable, not strictly monthly
                "status": "ACTIVE"
            }
        )
        assert engagement.id is not None
        assert engagement.engagement_id.startswith("ENG-")
        assert engagement.agreed_fee == Decimal("600000.00")
        assert engagement.billing_arrangement == "QUARTERLY_MILESTONE"

    finally:
        db.close()
