import os
import sys
import pytest
import concurrent.futures
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.crm.model import Account, Contact, Lead, LeadCommunicationHistory, CrmSequence
from app.core.security import get_password_hash
from app.audit.model import AuditLog
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
def setup_crm_stage4_environment():
    """Seed dedicated users for Stage 4 testing: Admin, Sales Manager, Sales Exec, Finance Manager, Non-CRM."""
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
        role_finance_mgr = db.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_FINANCE_MANAGER").first()

        # 1. CRM Admin
        u_admin = db.query(User).filter(User.username == "stg4_crm_admin").first()
        if not u_admin:
            u_admin = User(name="Stage4 Admin", username="stg4_crm_admin", email="stg4_admin@revy.test", password_hash=get_password_hash("Pass123!"), status="active")
            db.add(u_admin)
            db.commit()
            db.refresh(u_admin)
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == u_admin.id).delete()
        db.add(UserModuleMembership(user_id=u_admin.id, module_id=crm_mod.id, role_id=role_admin.id, is_active=True))

        # 2. CRM Sales Manager
        u_mgr = db.query(User).filter(User.username == "stg4_sales_mgr").first()
        if not u_mgr:
            u_mgr = User(name="Stage4 Sales Manager", username="stg4_sales_mgr", email="stg4_mgr@revy.test", password_hash=get_password_hash("Pass123!"), status="active")
            db.add(u_mgr)
            db.commit()
            db.refresh(u_mgr)
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == u_mgr.id).delete()
        db.add(UserModuleMembership(user_id=u_mgr.id, module_id=crm_mod.id, role_id=role_sales_mgr.id, is_active=True))

        # 3. CRM Sales Executive
        u_exec = db.query(User).filter(User.username == "stg4_sales_exec").first()
        if not u_exec:
            u_exec = User(name="Stage4 Sales Exec", username="stg4_sales_exec", email="stg4_exec@revy.test", password_hash=get_password_hash("Pass123!"), status="active")
            db.add(u_exec)
            db.commit()
            db.refresh(u_exec)
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == u_exec.id).delete()
        db.add(UserModuleMembership(user_id=u_exec.id, module_id=crm_mod.id, role_id=role_sales_exec.id, is_active=True))

        # 4. CRM Finance Manager
        u_fin = db.query(User).filter(User.username == "stg4_finance_mgr").first()
        if not u_fin:
            u_fin = User(name="Stage4 Finance Mgr", username="stg4_finance_mgr", email="stg4_fin@revy.test", password_hash=get_password_hash("Pass123!"), status="active")
            db.add(u_fin)
            db.commit()
            db.refresh(u_fin)
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == u_fin.id).delete()
        db.add(UserModuleMembership(user_id=u_fin.id, module_id=crm_mod.id, role_id=role_finance_mgr.id, is_active=True))

        # 5. Non-CRM User (BMS employee only)
        bms_mod = db.query(Module).filter(Module.code == "BMS").first()
        bms_role = db.query(ModuleRole).filter(ModuleRole.module_id == bms_mod.id, ModuleRole.code == "BMS_EMPLOYEE").first()
        u_non_crm = db.query(User).filter(User.username == "stg4_non_crm").first()
        if not u_non_crm:
            u_non_crm = User(name="Stage4 Non-CRM", username="stg4_non_crm", email="stg4_noncrm@revy.test", password_hash=get_password_hash("Pass123!"), status="active")
            db.add(u_non_crm)
            db.commit()
            db.refresh(u_non_crm)
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == u_non_crm.id).delete()
        db.add(UserModuleMembership(user_id=u_non_crm.id, module_id=bms_mod.id, role_id=bms_role.id, is_active=True))

        db.commit()
        return True
    finally:
        db.close()


# =========================================================================
# TEST 1: ACCOUNT & CONTACT SEARCH, CREATION, DUPLICATES, RELATIONSHIPS
# =========================================================================

def test_account_and_contact_lifecycle_and_duplicates(setup_crm_stage4_environment):
    headers = get_token_headers("stg4_crm_admin", "Pass123!", "CRM_ADMIN")

    # 1. Create unique account
    ts = int(datetime.now(timezone.utc).timestamp())
    acc_name = f"Apex Biotech {ts}"
    res_acc = client.post("/api/v1/crm/accounts", json={
        "name": acc_name,
        "industry": "Renewable Energy",
        "website": "https://apexbiotech.test",
        "phone": "+91 9876543210"
    }, headers=headers)
    assert res_acc.status_code == 201
    acc_data = res_acc.json()["account"]
    assert acc_data["name"] == acc_name
    assert acc_data["accountId"].startswith("ACC-")
    acc_id = acc_data["id"]

    # 2. Duplicate Account Name returns HTTP 409 Conflict
    res_dup_acc = client.post("/api/v1/crm/accounts", json={
        "name": f"  {acc_name.upper()}  ",
        "industry": "Different Industry"
    }, headers=headers)
    assert res_dup_acc.status_code == 409

    # 3. Create Contact linked to Account
    contact_email = f"lead.contact_{ts}@apexbiotech.test"
    contact_phone = f"+91 91234{ts % 100000:05d}"
    res_con = client.post("/api/v1/crm/contacts", json={
        "name": "Dr. Ramesh Verma",
        "accountId": acc_id,
        "email": contact_email,
        "mobileNumber": contact_phone,
        "designation": "Plant Head"
    }, headers=headers)
    assert res_con.status_code == 201
    con_data = res_con.json()["contact"]
    assert con_data["name"] == "Dr. Ramesh Verma"
    assert con_data["accountId"] == acc_id
    assert con_data["contactId"].startswith("CON-")
    con_id = con_data["id"]

    # 4. Duplicate Contact Email returns HTTP 409 Conflict
    res_dup_email = client.post("/api/v1/crm/contacts", json={
        "name": "Different Name",
        "email": contact_email.upper()
    }, headers=headers)
    assert res_dup_email.status_code == 409

    # 5. Create Contact WITHOUT Account (Allowed)
    res_no_acc_con = client.post("/api/v1/crm/contacts", json={
        "name": f"Independent Consultant {ts}",
        "email": f"consultant_{ts}@independent.test"
    }, headers=headers)
    assert res_no_acc_con.status_code == 201
    assert res_no_acc_con.json()["contact"]["accountId"] is None

    # 6. Search Accounts and Contacts
    res_search_acc = client.get(f"/api/v1/crm/accounts?search={acc_name[:10]}", headers=headers)
    assert res_search_acc.status_code == 200
    assert any(a["id"] == acc_id for a in res_search_acc.json()["accounts"])

    res_search_con = client.get(f"/api/v1/crm/contacts?accountId={acc_id}", headers=headers)
    assert res_search_con.status_code == 200
    assert any(c["id"] == con_id for c in res_search_con.json()["contacts"])


# =========================================================================
# TEST 2: LEAD CREATION, VALIDATION, AND ENUM INTEGRITY
# =========================================================================

def test_lead_creation_and_field_validations(setup_crm_stage4_environment):
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create account and contact
    res_acc = client.post("/api/v1/crm/accounts", json={"name": f"Clean Energy Corp {ts}"}, headers=headers)
    acc_id = res_acc.json()["account"]["id"]

    res_con = client.post("/api/v1/crm/contacts", json={
        "name": f"Vikram Patel {ts}",
        "accountId": acc_id,
        "email": f"vikram_{ts}@cleanenergy.test"
    }, headers=headers)
    con_id = res_con.json()["contact"]["id"]

    # Valid lead creation
    res_lead = client.post("/api/v1/crm/leads", json={
        "leadName": f"Biogas Inoculum Requirement {ts}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "requestedProductService": "Specialized Anaerobic Inoculum 5000L",
        "leadSource": "Investor",
        "contactId": con_id,
        "accountId": acc_id,
        "communicationChannel": "Email"
    }, headers=headers)
    assert res_lead.status_code == 201
    lead_data = res_lead.json()["lead"]
    assert lead_data["leadId"].startswith("LEAD-")
    assert lead_data["businessArea"] == "Biogas"
    assert lead_data["requirementType"] in ["Product", "Direct Product/Service"]
    assert lead_data["leadSource"] == "Investor"
    assert lead_data["lifecycleStatus"] in ["Enquiry", "Open"]

    # Reject invalid Business Area
    res_bad_ba = client.post("/api/v1/crm/leads", json={
        "leadName": "Bad BA Lead",
        "businessArea": "SolarEnergy",  # Invalid
        "requirementType": "Direct Product/Service",
        "requestedProductService": "Panels",
        "contactId": con_id
    }, headers=headers)
    assert res_bad_ba.status_code in [400, 422]

    # Reject invalid Requirement Type
    res_bad_rt = client.post("/api/v1/crm/leads", json={
        "leadName": "Bad RT Lead",
        "businessArea": "WWT",
        "requirementType": "CustomConsulting",  # Invalid
        "requestedProductService": "Consulting",
        "contactId": con_id
    }, headers=headers)
    assert res_bad_rt.status_code in [400, 422]


# =========================================================================
# TEST 3: DUPLICATE OPEN LEAD RULE & REOPENING BEHAVIOR
# =========================================================================

def test_duplicate_open_lead_rules(setup_crm_stage4_environment):
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    # Setup Account and Contact
    res_acc = client.post("/api/v1/crm/accounts", json={"name": f"Dupe Test Enterprise {ts}"}, headers=headers)
    acc_id = res_acc.json()["account"]["id"]
    res_con = client.post("/api/v1/crm/contacts", json={"name": f"Manager Dupe {ts}", "accountId": acc_id, "email": f"dupe_{ts}@test.com"}, headers=headers)
    con_id = res_con.json()["contact"]["id"]

    product_req = "Bio-Culture Solution Type-B"

    # 1. Create first Open lead
    res_lead1 = client.post("/api/v1/crm/leads", json={
        "leadName": f"First Open Lead {ts}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "requestedProductService": product_req,
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res_lead1.status_code == 201
    lead1_id = res_lead1.json()["lead"]["id"]

    # 2. Phase 1 Update: Multiple leads for the same Account & Contact with identical requirement selections are ALLOWED (HTTP 201)
    res_dupe = client.post("/api/v1/crm/leads", json={
        "leadName": f"Second Duplicate Lead {ts}",
        "businessArea": "Biogas",
        "requirementType": "Product",
        "requestedProductService": f"  {product_req.upper()}   ",  # same requirement
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res_dupe.status_code == 201
    lead2_id = res_dupe.json()["lead"]["id"]
    assert lead2_id != lead1_id

    # 3. Create lead for SAME client but with a DIFFERENT product requirement -> MUST BE ALLOWED
    res_diff_req = client.post("/api/v1/crm/leads", json={
        "leadName": f"Different Product Lead {ts}",
        "businessArea": "Biogas",
        "requirementType": "Sample Testing",
        "requestedProductService": "Nutrient Blend 100Kg",  # distinct requirement
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res_diff_req.status_code == 201

    # 4. Close first lead (transition to Dormant)
    res_close = client.post(f"/api/v1/crm/leads/{lead1_id}/status", json={"status": "Dormant", "remarks": "Moved to dormant"}, headers=headers)
    assert res_close.status_code == 200
    assert res_close.json()["lead"]["lifecycleStatus"] == "Dormant"

    # 5. Now that first lead is Dormant, creating a NEW lead for the SAME requirement -> MUST BE ALLOWED!
    res_new_lead_after_close = client.post("/api/v1/crm/leads", json={
        "leadName": f"New Lead After Close {ts}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "requestedProductService": product_req,
        "contactId": con_id,
        "accountId": acc_id
    }, headers=headers)
    assert res_new_lead_after_close.status_code == 201


# =========================================================================
# TEST 4: CONCURRENT OPEN LEAD CREATION ATTEMPTS
# =========================================================================

def test_concurrent_duplicate_lead_creation_safety(setup_crm_stage4_environment):
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    res_acc = client.post("/api/v1/crm/accounts", json={"name": f"Concurrency Client {ts}"}, headers=headers)
    acc_id = res_acc.json()["account"]["id"]
    res_con = client.post("/api/v1/crm/contacts", json={"name": f"Contact Concurrency {ts}", "accountId": acc_id, "email": f"concur_{ts}@client.test"}, headers=headers)
    con_id = res_con.json()["contact"]["id"]

    same_product = f"Enzyme Catalyst Pack {ts}"

    def attempt_create_lead(idx):
        return client.post("/api/v1/crm/leads", json={
            "leadName": f"Concurrent Lead Attempt {idx}",
            "businessArea": "WWT",
            "requirementType": "Direct Product/Service",
            "requestedProductService": same_product,
            "contactId": con_id,
            "accountId": acc_id
        }, headers=headers)

    # Launch 4 concurrent creation attempts
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(attempt_create_lead, i) for i in range(4)]
        responses = [f.result() for f in futures]

    statuses = [r.status_code for r in responses]
    success_count = statuses.count(201)

    # Phase 1 Update: All requests succeed with unique generated Lead IDs
    assert success_count == 4, f"Expected 4 successful creations, got statuses: {statuses}"
    created_ids = {r.json()["lead"]["leadId"] for r in responses}
    assert len(created_ids) == 4, "Each created lead must have a distinct unique leadId"


# =========================================================================
# TEST 5: ASSIGNEE VALIDATION (ACTIVE CRM USER ONLY)
# =========================================================================

def test_lead_assignee_validation(setup_crm_stage4_environment):
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    db = SessionLocal()
    u_exec = db.query(User).filter(User.username == "stg4_sales_exec").first()
    u_non_crm = db.query(User).filter(User.username == "stg4_non_crm").first()
    con = db.query(Contact).filter(Contact.is_active == True).first()
    db.close()

    # 1. Assign to valid active CRM user (Sales Executive) -> SUCCESS
    res_valid_assign = client.post("/api/v1/crm/leads", json={
        "leadName": f"Assigned Lead {ts}",
        "businessArea": "WWT",
        "requirementType": "Direct Product/Service",
        "requestedProductService": f"WWT Aeration Culture {ts}",
        "contactId": con.id,
        "assignedToUserId": u_exec.id
    }, headers=headers)
    assert res_valid_assign.status_code == 201
    assert res_valid_assign.json()["lead"]["assignedToUserId"] == u_exec.id

    # 2. Assign to user without CRM membership -> REJECTED (HTTP 400)
    res_invalid_assign = client.post("/api/v1/crm/leads", json={
        "leadName": f"Invalid Assigned Lead {ts}",
        "businessArea": "WWT",
        "requirementType": "Direct Product/Service",
        "requestedProductService": f"Culture Pack {ts}",
        "contactId": con.id,
        "assignedToUserId": u_non_crm.id
    }, headers=headers)
    assert res_invalid_assign.status_code in [400, 422]


# =========================================================================
# TEST 6: COMMUNICATION HISTORY & LAST_CONNECTED_DATE QUALIFICATION
# =========================================================================

def test_communication_history_and_last_connected_date(setup_crm_stage4_environment):
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    ts = int(datetime.now(timezone.utc).timestamp())

    db = SessionLocal()
    con = db.query(Contact).filter(Contact.is_active == True).first()
    db.close()

    # Create lead
    res_lead = client.post("/api/v1/crm/leads", json={
        "leadName": f"Comm History Lead {ts}",
        "businessArea": "Biogas",
        "requirementType": "Direct Product/Service",
        "requestedProductService": f"Comm Culture Test {ts}",
        "contactId": con.id
    }, headers=headers)
    lead_id = res_lead.json()["lead"]["id"]
    assert res_lead.json()["lead"]["lastConnectedDate"] is None

    # 1. Non-qualifying internal note -> last_connected_date must NOT be updated
    res_internal = client.post(f"/api/v1/crm/leads/{lead_id}/communications", json={
        "channel": "Other",
        "eventType": "Internal discussion with REVY colleague",
        "summary": "Discussed client specs with lab team"
    }, headers=headers)
    assert res_internal.status_code == 201

    lead_after_internal = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers).json()["lead"]
    assert lead_after_internal["lastConnectedDate"] is None
    assert "Discussed client specs" in lead_after_internal["remarks"]

    # 2. Qualifying client interaction -> last_connected_date MUST be updated
    res_client_call = client.post(f"/api/v1/crm/leads/{lead_id}/communications", json={
        "channel": "Phone / Call",
        "eventType": "Introductory call with client",
        "summary": "Client agreed to pilot test schedule",
        "followUpDate": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    }, headers=headers)
    assert res_client_call.status_code == 201

    lead_after_call = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers).json()["lead"]
    assert lead_after_call["lastConnectedDate"] is not None
    assert lead_after_call["nextFollowUpDate"] is not None

    # 3. Verify communication history list ordering
    res_comms = client.get(f"/api/v1/crm/leads/{lead_id}/communications", headers=headers)
    assert res_comms.status_code == 200
    comms_list = res_comms.json()["communications"]
    assert len(comms_list) == 2
    assert comms_list[0]["communicationId"].startswith("COM-")


# =========================================================================
# TEST 7: REAL DASHBOARD METRICS CALCULATION
# =========================================================================

def test_dashboard_metrics_real_queries(setup_crm_stage4_environment):
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")

    res_metrics = client.get("/api/v1/crm/dashboard/metrics", headers=headers)
    assert res_metrics.status_code == 200
    data = res_metrics.json()
    assert data["success"] is True
    assert "totalLeads" in data
    assert "openLeads" in data
    assert "qualifiedLeads" in data
    assert "disqualifiedLeads" in data
    assert "myLeads" in data
    assert "followUpsDue" in data
    assert "overdueFollowUps" in data

    # Verify actual database math consistency
    assert data["totalLeads"] >= data["openLeads"]
    assert data["totalLeads"] >= data["qualifiedLeads"]
    assert data["totalLeads"] >= data["disqualifiedLeads"]


# =========================================================================
# TEST 8: SAVED VIEWS, SEARCH, SORTING, AND PAGINATION
# =========================================================================

def test_lead_views_search_and_pagination(setup_crm_stage4_environment):
    headers = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")

    # 1. Open view
    res_open = client.get("/api/v1/crm/leads?view=open", headers=headers)
    assert res_open.status_code == 200
    for l in res_open.json()["leads"]:
        assert l["lifecycleStatus"] in ("Enquiry", "Offer", "Negotiation", "Supply", "Payment", "Open")

    # 2. All view
    res_all = client.get("/api/v1/crm/leads?view=all&page=1&pageSize=10", headers=headers)
    assert res_all.status_code == 200
    assert "totalPages" in res_all.json()
    assert res_all.json()["pageSize"] == 10

    # 3. Sorting
    res_sorted = client.get("/api/v1/crm/leads?view=all&sortBy=created_at&sortOrder=asc", headers=headers)
    assert res_sorted.status_code == 200


# =========================================================================
# TEST 9: ROLE AUTHORIZATION & PERMISSION ENFORCEMENT
# =========================================================================

def test_role_based_api_permissions(setup_crm_stage4_environment):
    admin_hdr = get_token_headers("stg4_crm_admin", "Pass123!", "CRM_ADMIN")
    mgr_hdr = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    fin_hdr = get_token_headers("stg4_finance_mgr", "Pass123!", "CRM_FINANCE_MANAGER")
    non_crm_hdr = get_token_headers("stg4_non_crm", "Pass123!", "BMS_EMPLOYEE")

    # 1. Non-CRM user is blocked from all CRM endpoints (HTTP 403)
    assert client.get("/api/v1/crm/leads", headers=non_crm_hdr).status_code == 403
    assert client.get("/api/v1/crm/accounts", headers=non_crm_hdr).status_code == 403
    assert client.get("/api/v1/crm/dashboard/metrics", headers=non_crm_hdr).status_code == 403

    # 2. CRM Finance Manager can VIEW leads and metrics...
    assert client.get("/api/v1/crm/leads", headers=fin_hdr).status_code == 200
    assert client.get("/api/v1/crm/dashboard/metrics", headers=fin_hdr).status_code == 200

    # ...but CANNOT CREATE leads or accounts (HTTP 403)
    assert client.post("/api/v1/crm/leads", json={"leadName": "Blocked"}, headers=fin_hdr).status_code == 403
    assert client.post("/api/v1/crm/accounts", json={"name": "Blocked"}, headers=fin_hdr).status_code == 403

    # 3. Sales Manager can create leads...
    # ...but CANNOT access CRM User Hub (HTTP 403)
    assert client.get("/api/v1/crm/users", headers=mgr_hdr).status_code == 403
    assert client.get("/api/v1/crm/roles", headers=mgr_hdr).status_code == 403

    # 4. CRM Admin CAN access CRM User Hub
    assert client.get("/api/v1/crm/users", headers=admin_hdr).status_code == 200
    assert client.get("/api/v1/crm/roles", headers=admin_hdr).status_code == 200
