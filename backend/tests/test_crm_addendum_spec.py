import os
import sys
import uuid
import pytest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.roles.model import Role, Permission
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.crm.model import Account, Contact, Lead, lead_additional_contacts
from app.core.security import get_password_hash
from app.core.init_roles import ensure_roles_and_permissions
from app.core.init_modules import ensure_modules_and_memberships

client = TestClient(app)

_TOKEN_CACHE = {}


def get_token_headers(username: str, role_code: str = "IT_ADMIN") -> dict:
    key = f"{username}:{role_code}"
    if key in _TOKEN_CACHE:
        return _TOKEN_CACHE[key]

    # Pre-configure user if needed
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                name=f"Test {username}",
                username=username,
                email=f"{username}@revy.test",
                password_hash=get_password_hash("TestPass123!"),
                status="active"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

    res = client.post("/api/v1/auth/login", json={"username": username, "password": "TestPass123!"})
    if res.status_code != 200:
        # Try default passwords
        for pwd in ["Vasudev123", "Rajneesh123", "Jyoti123", "Faiz123", "Finance123", "CrmAdmin123!"]:
            r = client.post("/api/v1/auth/login", json={"username": username, "password": pwd})
            if r.status_code == 200:
                res = r
                break

    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    token = res.json()["token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": role_code
    }
    _TOKEN_CACHE[key] = headers
    return headers


@pytest.fixture(scope="module")
def setup_addendum_environment():
    """Setup test users, accounts, and contacts for addendum testing."""
    db = SessionLocal()
    try:
        ensure_roles_and_permissions()
        ensure_modules_and_memberships()

        crm_mod = db.query(Module).filter(Module.code == "CRM").first()
        bms_mod = db.query(Module).filter(Module.code == "BMS").first()
        assert crm_mod is not None and bms_mod is not None

        crm_admin_role = db.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_ADMIN").first()

        # Dedicated CRM Admin User
        admin_user = db.query(User).filter(User.username == "addendum_crm_admin").first()
        if not admin_user:
            admin_user = User(
                name="Addendum CRM Admin",
                username="addendum_crm_admin",
                email="addendum_crm_admin@revy.test",
                password_hash=get_password_hash("TestPass123!"),
                status="active"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        # Grant CRM Admin
        db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == admin_user.id,
            UserModuleMembership.module_id == crm_mod.id
        ).delete()
        db.add(UserModuleMembership(user_id=admin_user.id, module_id=crm_mod.id, role_id=crm_admin_role.id, is_active=True))
        db.commit()

        # Central User with NO module memberships
        central_only = db.query(User).filter(User.username == "addendum_central_pure").first()
        if not central_only:
            central_only = User(
                name="Pure Central Identity",
                username="addendum_central_pure",
                email="pure_central@revy.test",
                phone="+91 9876543210",
                password_hash=get_password_hash("TestPass123!"),
                status="active"
            )
            db.add(central_only)
            db.commit()
            db.refresh(central_only)
        # Ensure no CRM or BMS membership
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == central_only.id).delete()
        db.commit()

        # Test Accounts and Contacts
        acc_a = db.query(Account).filter(Account.account_id == "ACC-ADD-001").first()
        if not acc_a:
            acc_a = Account(
                account_id="ACC-ADD-001",
                name="Alpha Bio-Energy Corp",
                industry="Renewable Energy",
                is_active=True
            )
            db.add(acc_a)
            db.commit()
            db.refresh(acc_a)

        acc_b = db.query(Account).filter(Account.account_id == "ACC-ADD-002").first()
        if not acc_b:
            acc_b = Account(
                account_id="ACC-ADD-002",
                name="Beta Wastewater Solutions",
                industry="Wastewater Treatment",
                is_active=True
            )
            db.add(acc_b)
            db.commit()
            db.refresh(acc_b)

        # Contacts for Account A
        con_a1 = db.query(Contact).filter(Contact.contact_id == "CON-ADD-001").first()
        if not con_a1:
            con_a1 = Contact(
                contact_id="CON-ADD-001",
                name="Dr. Anil Sharma",
                designation="Plant Technical Director",
                email="anil.sharma@alphabio.test",
                mobile_number="+91 9123456781",
                account_id=acc_a.id,
                is_active=True
            )
            db.add(con_a1)

        con_a2 = db.query(Contact).filter(Contact.contact_id == "CON-ADD-002").first()
        if not con_a2:
            con_a2 = Contact(
                contact_id="CON-ADD-002",
                name="Ms. Priya Verma",
                designation="Procurement Specialist",
                email="priya.verma@alphabio.test",
                mobile_number="+91 9123456782",
                account_id=acc_a.id,
                is_active=True
            )
            db.add(con_a2)

        con_a3 = db.query(Contact).filter(Contact.contact_id == "CON-ADD-003").first()
        if not con_a3:
            con_a3 = Contact(
                contact_id="CON-ADD-003",
                name="Mr. Suresh Patel",
                designation="Operations Engineer",
                email="suresh.patel@alphabio.test",
                mobile_number="+91 9123456783",
                account_id=acc_a.id,
                is_active=True
            )
            db.add(con_a3)

        # Contact for Account B
        con_b1 = db.query(Contact).filter(Contact.contact_id == "CON-ADD-004").first()
        if not con_b1:
            con_b1 = Contact(
                contact_id="CON-ADD-004",
                name="Mr. Vikram Singh",
                designation="General Manager",
                email="vikram.singh@betaww.test",
                mobile_number="+91 9123456784",
                account_id=acc_b.id,
                is_active=True
            )
            db.add(con_b1)

        db.commit()

        yield {
            "admin_user": admin_user,
            "central_only": central_only,
            "acc_a": acc_a,
            "acc_b": acc_b,
            "con_a1": con_a1,
            "con_a2": con_a2,
            "con_a3": con_a3,
            "con_b1": con_b1
        }
    finally:
        db.close()


# =========================================================================
# 1. LEAD CREATION — CONNECTED DATE TESTS (SECTION 2)
# =========================================================================

def test_lead_connected_date_persistence_and_editing(setup_addendum_environment):
    env = setup_addendum_environment
    headers = get_token_headers("addendum_crm_admin", "CRM_ADMIN")

    # 1. Create Lead with Connected Date
    connected_str = "2026-10-15"
    payload = {
        "leadName": "Biogas Yield Enhancement Inoculum",
        "businessArea": "Biogas",
        "requirementTypes": ["Product"],
        "requestedProductService": "Specialized Bacterial Culture 1000L",
        "leadSource": "Email Received",
        "connectedDate": connected_str,
        "contactId": env["con_a1"].id,
        "accountId": env["acc_a"].id
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code in (200, 201), res.text
    lead = res.json()["lead"]
    lead_id = lead["id"]

    assert lead["connectedDate"] == connected_str
    # Verify Connected Date is stored as a date and distinct from timestamps
    assert lead["connectedDate"] != lead["createdAt"]
    assert lead["connectedDate"] != lead["lastConnectedDate"]

    # 2. Retrieve Lead
    res_get = client.get(f"/api/v1/crm/leads/{lead_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["lead"]["connectedDate"] == connected_str

    # 3. Update Connected Date
    new_connected_str = "2026-10-18"
    res_up = client.put(f"/api/v1/crm/leads/{lead_id}", json={"connectedDate": new_connected_str}, headers=headers)
    assert res_up.status_code == 200
    assert res_up.json()["lead"]["connectedDate"] == new_connected_str


# =========================================================================
# 2. MULTIPLE CONTACTS ON A LEAD TESTS (SECTION 3)
# =========================================================================

def test_lead_multiple_contacts_attachment_and_revalidation(setup_addendum_environment):
    env = setup_addendum_environment
    headers = get_token_headers("addendum_crm_admin", "CRM_ADMIN")

    # 1. Create Lead with Primary Contact and 2 Additional Contacts
    payload = {
        "leadName": "Multi-Contact Plant Commissioning",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting", "Sample Testing"],
        "leadSource": "Email Received",
        "contactId": env["con_a1"].id,  # Primary Contact
        "additionalContactIds": [env["con_a2"].id, env["con_a3"].id],
        "accountId": env["acc_a"].id
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code in (200, 201), res.text
    lead = res.json()["lead"]
    lead_id = lead["id"]

    # Primary Contact preserved
    assert lead["contactId"] == env["con_a1"].id
    assert lead["contactName"] == env["con_a1"].name

    # Additional contacts attached
    add_contacts = lead["additionalContacts"]
    assert len(add_contacts) == 2
    add_ids = [c["id"] for c in add_contacts]
    assert env["con_a2"].id in add_ids
    assert env["con_a3"].id in add_ids

    # Additional contact details serialized
    for c in add_contacts:
        assert "name" in c and c["name"]
        assert "email" in c and c["email"]
        assert "mobileNumber" in c
        assert "designation" in c

    # 2. Primary Contact cannot be duplicated in additional contacts
    payload_dup = {
        "leadName": "Multi-Contact Primary Dup Test",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting"],
        "leadSource": "Email Received",
        "contactId": env["con_a1"].id,
        "additionalContactIds": [env["con_a1"].id, env["con_a2"].id],  # includes primary
        "accountId": env["acc_a"].id
    }
    res_dup = client.post("/api/v1/crm/leads", json=payload_dup, headers=headers)
    assert res_dup.status_code in (200, 201), res_dup.text
    # Primary contact should not be duplicated in additional contacts list
    add_dup_ids = [c["id"] for c in res_dup.json()["lead"]["additionalContacts"]]
    assert env["con_a1"].id not in add_dup_ids
    assert env["con_a2"].id in add_dup_ids

    # 3. Reject Cross-Account Additional Contact Assignment
    payload_cross = {
        "leadName": "Cross-Account Contact Rejection Test",
        "businessArea": "WWT",
        "requirementTypes": ["Sample Testing"],
        "leadSource": "Email Received",
        "contactId": env["con_a1"].id,
        "additionalContactIds": [env["con_b1"].id],  # Belongs to Account B, while Lead is for Account A
        "accountId": env["acc_a"].id
    }
    res_cross = client.post("/api/v1/crm/leads", json=payload_cross, headers=headers)
    assert res_cross.status_code in (400, 422)
    assert "belongs to a different Account" in res_cross.text

    # 4. Same Contact associated with multiple Leads
    payload_lead_2 = {
        "leadName": "Second Lead Sharing Same Additional Contact",
        "businessArea": "Biogas",
        "requirementTypes": ["Product"],
        "leadSource": "Email Received",
        "contactId": env["con_a2"].id,  # Con A2 is primary here
        "additionalContactIds": [env["con_a3"].id],  # Con A3 is additional on both leads
        "accountId": env["acc_a"].id
    }
    res_l2 = client.post("/api/v1/crm/leads", json=payload_lead_2, headers=headers)
    assert res_l2.status_code in (200, 201), res_l2.text
    assert env["con_a3"].id in [c["id"] for c in res_l2.json()["lead"]["additionalContacts"]]


# =========================================================================
# 3. LEAD SOURCE RESTRICTION TESTS (SECTION 4)
# =========================================================================

def test_lead_source_restriction_and_historical_compatibility(setup_addendum_environment):
    env = setup_addendum_environment
    headers = get_token_headers("addendum_crm_admin", "CRM_ADMIN")

    # 1. Accepts "Email Received"
    payload_valid = {
        "leadName": "Email Source Lead",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting"],
        "leadSource": "Email Received",
        "contactId": env["con_a1"].id
    }
    res_valid = client.post("/api/v1/crm/leads", json=payload_valid, headers=headers)
    assert res_valid.status_code in (200, 201), res_valid.text
    assert res_valid.json()["lead"]["leadSource"] == "Email Received"

    # 2. Rejects newly submitted unsupported sources
    payload_invalid = {
        "leadName": "Invalid Source Lead",
        "businessArea": "Biogas",
        "requirementTypes": ["Consulting"],
        "leadSource": "Cold Phone Call",
        "contactId": env["con_a1"].id
    }
    res_invalid = client.post("/api/v1/crm/leads", json=payload_invalid, headers=headers)
    assert res_invalid.status_code in (400, 422)

    # 3. Historical Lead Source is preserved in DB and retrieves cleanly
    db = SessionLocal()
    try:
        hist_lead = Lead(
            lead_id=f"LEAD-HIST-{uuid.uuid4().hex[:6]}",
            lead_name="Historical Referral Lead",
            business_area="WWT",
            requirement_type="Consulting",
            lead_source="Referral",  # Historical legacy value
            contact_id=env["con_a1"].id,
            lifecycle_status="Open"
        )
        db.add(hist_lead)
        db.commit()
        db.refresh(hist_lead)
        hist_id = hist_lead.id
    finally:
        db.close()

    res_hist = client.get(f"/api/v1/crm/leads/{hist_id}", headers=headers)
    assert res_hist.status_code == 200
    assert res_hist.json()["lead"]["leadSource"] == "Referral"


# =========================================================================
# 4. REMOVE WEBSITE / DOCUMENT LINK FROM FORM (SECTION 5)
# =========================================================================

def test_lead_creation_and_editing_without_website_link(setup_addendum_environment):
    env = setup_addendum_environment
    headers = get_token_headers("addendum_crm_admin", "CRM_ADMIN")

    # Lead create and update without websiteLink field
    payload = {
        "leadName": "No Website Field Lead",
        "businessArea": "Biogas",
        "requirementTypes": ["Product"],
        "leadSource": "Email Received",
        "contactId": env["con_a1"].id
    }
    res = client.post("/api/v1/crm/leads", json=payload, headers=headers)
    assert res.status_code in (200, 201), res.text
    lead_id = res.json()["lead"]["id"]

    res_up = client.put(f"/api/v1/crm/leads/{lead_id}", json={"remarks": "Updated without website link"}, headers=headers)
    assert res_up.status_code == 200
    assert res_up.json()["lead"]["remarks"] == "Updated without website link"


# =========================================================================
# 5. HYBRID CENTRAL USER MANAGEMENT TESTS (SECTIONS 6-12)
# =========================================================================

def test_hybrid_user_hub_isolation_and_assignment_workflow(setup_addendum_environment):
    env = setup_addendum_environment
    headers = get_token_headers("addendum_crm_admin", "CRM_ADMIN")
    pure_central = env["central_only"]

    # 1. CRM User Hub list shows ONLY explicit CRM members
    res_users = client.get("/api/v1/crm/users", headers=headers)
    assert res_users.status_code == 200
    crm_user_ids = [u["userId"] for u in res_users.json()["users"]]
    assert pure_central.id not in crm_user_ids, "Central user without CRM membership must NOT appear in CRM user hub"

    # 2. Central user appears in available-users endpoint
    res_avail = client.get(f"/api/v1/crm/available-users?search={pure_central.username}", headers=headers)
    assert res_avail.status_code == 200
    avail_ids = [u["id"] for u in res_avail.json()["users"]]
    assert pure_central.id in avail_ids

    # 3. Assign Central User to CRM module with CRM role
    assign_payload = {
        "userId": pure_central.id,
        "roleCode": "CRM_SALES_EXECUTIVE",
        "isActive": True
    }
    res_assign = client.post("/api/v1/crm/users/assign", json=assign_payload, headers=headers)
    assert res_assign.status_code == 200, res_assign.text
    assigned_data = res_assign.json()["user"]
    assert assigned_data["userId"] == pure_central.id
    assert assigned_data["crmAccess"] is True
    assert assigned_data["crmRoleCode"] == "CRM_SALES_EXECUTIVE"

    # 4. User now appears in CRM User Hub
    res_users_after = client.get("/api/v1/crm/users", headers=headers)
    assert res_users_after.status_code == 200
    crm_user_ids_after = [u["userId"] for u in res_users_after.json()["users"]]
    assert pure_central.id in crm_user_ids_after

    # 5. Assigning CRM does NOT grant BMS access
    db = SessionLocal()
    try:
        bms_mod = db.query(Module).filter(Module.code == "BMS").first()
        bms_mem = db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == pure_central.id,
            UserModuleMembership.module_id == bms_mod.id
        ).first()
        assert bms_mem is None, "Assigning CRM must NOT grant BMS access"
    finally:
        db.close()

    # 6. Reject invalid or cross-module role assignment
    res_bad_role = client.post("/api/v1/crm/users/assign", json={
        "userId": pure_central.id,
        "roleCode": "BMS_BREAKFAST_ADMIN"  # BMS role, invalid for CRM
    }, headers=headers)
    assert res_bad_role.status_code in (400, 422, 409)

    # 7. View User (Read-Only Identity)
    res_view = client.get(f"/api/v1/crm/users/{pure_central.id}", headers=headers)
    assert res_view.status_code == 200
    user_view = res_view.json()["user"]
    assert user_view["name"] == pure_central.name
    assert user_view["email"] == pure_central.email
    assert user_view["phone"] == pure_central.phone
    assert user_view["designation"] == getattr(pure_central, "designation", "")
    assert user_view["crmAccess"] is True

    # 8. Deactivate CRM Membership
    res_deact = client.post(f"/api/v1/crm/users/{pure_central.id}/access", json={"enabled": False}, headers=headers)
    assert res_deact.status_code == 200
    assert res_deact.json()["user"]["crmAccess"] is False

    # 9. Remove CRM Membership entirely (without deleting Central User)
    res_del = client.delete(f"/api/v1/crm/users/{pure_central.id}/membership", headers=headers)
    assert res_del.status_code == 200

    # Verify Central User still exists and is untouched
    db = SessionLocal()
    try:
        user_in_db = db.query(User).filter(User.id == pure_central.id).first()
        assert user_in_db is not None, "Removing CRM membership must NEVER delete the central user"
        assert user_in_db.username == pure_central.username

        # Membership is removed
        crm_mod = db.query(Module).filter(Module.code == "CRM").first()
        mem_in_db = db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == pure_central.id,
            UserModuleMembership.module_id == crm_mod.id
        ).first()
        assert mem_in_db is None
    finally:
        db.close()
