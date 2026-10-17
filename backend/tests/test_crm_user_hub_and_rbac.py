import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import SessionLocal
from app.users.model import User
from app.roles.model import Role, Permission
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.crm.model import Lead, Contact
from app.core.security import get_password_hash
from app.audit.model import AuditLog
from app.core.init_roles import ensure_roles_and_permissions
from app.core.init_modules import ensure_modules_and_memberships

client = TestClient(app)


_TOKEN_CACHE = {}


@pytest.fixture(scope="module")
def setup_crm_test_environment():
    """Seed dedicated test users for CRM User Hub RBAC testing."""
    db = SessionLocal()
    try:
        crm_mod = db.query(Module).filter(Module.code == "CRM").first()
        if not crm_mod:
            ensure_roles_and_permissions()
            ensure_modules_and_memberships()
            crm_mod = db.query(Module).filter(Module.code == "CRM").first()
        assert crm_mod is not None, "CRM module must exist"

        crm_admin_role = db.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_ADMIN").first()
        crm_sales_mgr_role = db.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_SALES_MANAGER").first()

        # 1. CRM Admin User
        crm_admin = db.query(User).filter(User.username == "test_crm_admin_user").first()
        if not crm_admin:
            crm_admin = User(
                name="CRM Admin User",
                username="test_crm_admin_user",
                email="crm_admin@revy.test",
                password_hash=get_password_hash("CrmAdmin123!"),
                status="active"
            )
            db.add(crm_admin)
            db.commit()
            db.refresh(crm_admin)
        crm_admin.roles = []
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == crm_admin.id).delete()
        db.add(UserModuleMembership(user_id=crm_admin.id, module_id=crm_mod.id, role_id=crm_admin_role.id, is_active=True))
        db.commit()

        # 2. CRM Sales Manager User
        sales_mgr = db.query(User).filter(User.username == "test_crm_sales_mgr_user").first()
        if not sales_mgr:
            sales_mgr = User(
                name="CRM Sales Manager User",
                username="test_crm_sales_mgr_user",
                email="sales_mgr@revy.test",
                password_hash=get_password_hash("SalesMgr123!"),
                status="active"
            )
            db.add(sales_mgr)
            db.commit()
            db.refresh(sales_mgr)
        sales_mgr.roles = []
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == sales_mgr.id).delete()
        db.add(UserModuleMembership(user_id=sales_mgr.id, module_id=crm_mod.id, role_id=crm_sales_mgr_role.id, is_active=True))
        db.commit()

        # 3. Target User (to be managed via CRM User Hub)
        target_user = db.query(User).filter(User.username == "test_crm_target_candidate").first()
        if not target_user:
            target_user = User(
                name="Candidate For CRM",
                username="test_crm_target_candidate",
                email="candidate_crm@revy.test",
                password_hash=get_password_hash("Target123!"),
                status="active"
            )
            db.add(target_user)
            db.commit()
            db.refresh(target_user)
        # Ensure starts without active CRM membership
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == target_user.id, UserModuleMembership.module_id == crm_mod.id).delete()
        db.commit()

        # 4. User without CRM access (BMS only)
        bms_mod = db.query(Module).filter(Module.code == "BMS").first()
        bms_emp_role = db.query(ModuleRole).filter(ModuleRole.module_id == bms_mod.id, ModuleRole.code == "BMS_EMPLOYEE").first()
        bms_user = db.query(User).filter(User.username == "test_bms_only_no_crm").first()
        if not bms_user:
            bms_user = User(
                name="BMS Only User",
                username="test_bms_only_no_crm",
                email="bms_only@revy.test",
                password_hash=get_password_hash("BmsOnly123!"),
                status="active"
            )
            db.add(bms_user)
            db.commit()
            db.refresh(bms_user)
        bms_user.roles = []
        db.query(UserModuleMembership).filter(UserModuleMembership.user_id == bms_user.id).delete()
        db.add(UserModuleMembership(user_id=bms_user.id, module_id=bms_mod.id, role_id=bms_emp_role.id, is_active=True))
        db.commit()

        return True
    finally:
        db.close()


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


# =========================================================================
# 1. CRM USER HUB AUTHORIZATION & ACCESS TESTS
# =========================================================================

def test_crm_admin_can_list_crm_users(setup_crm_test_environment):
    headers = get_token_headers("test_crm_admin_user", "CrmAdmin123!", "CRM_ADMIN")
    res = client.get("/api/v1/crm/users", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "users" in data
    assert data["count"] > 0
    usernames = [u["username"] for u in data["users"]]
    assert "test_crm_admin_user" in usernames
    assert "test_crm_target_candidate" in usernames


def test_crm_sales_manager_cannot_access_user_hub(setup_crm_test_environment):
    headers = get_token_headers("test_crm_sales_mgr_user", "SalesMgr123!", "CRM_SALES_MANAGER")
    
    # List users
    res_list = client.get("/api/v1/crm/users", headers=headers)
    assert res_list.status_code == 403

    # Grant access
    res_access = client.post("/api/v1/crm/users/some-user-id/access", json={"enabled": True}, headers=headers)
    assert res_access.status_code == 403

    # Update role
    res_role = client.put("/api/v1/crm/users/some-user-id/role", json={"roleCode": "CRM_SALES_EXECUTIVE"}, headers=headers)
    assert res_role.status_code == 403


def test_unauthorized_user_without_crm_cannot_access_crm_endpoints(setup_crm_test_environment):
    headers = get_token_headers("test_bms_only_no_crm", "BmsOnly123!", "BMS_EMPLOYEE")
    
    # Status check rejected (no CRM membership)
    res_status = client.get("/api/v1/crm/status", headers=headers)
    assert res_status.status_code == 403

    # User Hub rejected
    res_users = client.get("/api/v1/crm/users", headers=headers)
    assert res_users.status_code == 403


def test_crm_admin_can_manage_user_access_and_roles(setup_crm_test_environment):
    headers = get_token_headers("test_crm_admin_user", "CrmAdmin123!", "CRM_ADMIN")
    
    db = SessionLocal()
    target_user = db.query(User).filter(User.username == "test_crm_target_candidate").first()
    target_id = target_user.id
    db.close()

    # 1. Enable CRM access with role CRM_SALES_EXECUTIVE
    res_enable = client.post(
        f"/api/v1/crm/users/{target_id}/access",
        json={"enabled": True, "roleCode": "CRM_SALES_EXECUTIVE"},
        headers=headers
    )
    assert res_enable.status_code == 200
    res_data = res_enable.json()
    assert res_data["success"] is True
    assert res_data["user"]["crmAccess"] is True
    assert res_data["user"]["crmRoleCode"] == "CRM_SALES_EXECUTIVE"

    # 2. Change role to CRM_SALES_COORDINATOR
    res_role = client.put(
        f"/api/v1/crm/users/{target_id}/role",
        json={"roleCode": "CRM_SALES_COORDINATOR"},
        headers=headers
    )
    assert res_role.status_code == 200
    assert res_role.json()["user"]["crmRoleCode"] == "CRM_SALES_COORDINATOR"

    # 3. Disable CRM access
    res_disable = client.post(
        f"/api/v1/crm/users/{target_id}/access",
        json={"enabled": False},
        headers=headers
    )
    assert res_disable.status_code == 200
    assert res_disable.json()["user"]["crmAccess"] is False


def test_crm_admin_cannot_assign_invalid_or_cross_module_role(setup_crm_test_environment):
    headers = get_token_headers("test_crm_admin_user", "CrmAdmin123!", "CRM_ADMIN")
    
    db = SessionLocal()
    target_user = db.query(User).filter(User.username == "test_crm_target_candidate").first()
    target_id = target_user.id
    db.close()

    # Invalid non-existent role
    res_invalid = client.put(
        f"/api/v1/crm/users/{target_id}/role",
        json={"roleCode": "NON_EXISTENT_ROLE"},
        headers=headers
    )
    assert res_invalid.status_code in [400, 422]

    # Cross-module role escalation (BMS_ADMIN)
    res_cross = client.put(
        f"/api/v1/crm/users/{target_id}/role",
        json={"roleCode": "BMS_ADMIN"},
        headers=headers
    )
    assert res_cross.status_code in [400, 403, 422]

    # Global admin role escalation (IT_ADMIN)
    res_global = client.put(
        f"/api/v1/crm/users/{target_id}/role",
        json={"roleCode": "IT_ADMIN"},
        headers=headers
    )
    assert res_global.status_code in [400, 403, 422]


def test_nonexistent_user_id_returns_404(setup_crm_test_environment):
    headers = get_token_headers("test_crm_admin_user", "CrmAdmin123!", "CRM_ADMIN")
    fake_id = "00000000-0000-0000-0000-000000000000"

    res_access = client.post(f"/api/v1/crm/users/{fake_id}/access", json={"enabled": True}, headers=headers)
    assert res_access.status_code == 404

    res_role = client.put(f"/api/v1/crm/users/{fake_id}/role", json={"roleCode": "CRM_SALES_EXECUTIVE"}, headers=headers)
    assert res_role.status_code == 404


def test_crm_admin_cannot_modify_own_crm_access_or_escalate_self(setup_crm_test_environment):
    headers = get_token_headers("test_crm_admin_user", "CrmAdmin123!", "CRM_ADMIN")
    
    db = SessionLocal()
    admin_user = db.query(User).filter(User.username == "test_crm_admin_user").first()
    admin_id = admin_user.id
    db.close()

    res_self = client.post(
        f"/api/v1/crm/users/{admin_id}/access",
        json={"enabled": False},
        headers=headers
    )
    assert res_self.status_code == 403


def test_disabling_crm_access_preserves_historical_leads(setup_crm_test_environment):
    headers = get_token_headers("test_crm_admin_user", "CrmAdmin123!", "CRM_ADMIN")
    
    db = SessionLocal()
    target_user = db.query(User).filter(User.username == "test_crm_target_candidate").first()
    target_id = target_user.id
    
    # Create contact & historical lead assigned to this user
    contact = Contact(
        contact_id="CON-TEST-HIST",
        name="Historical Contact",
        email="hist@client.com",
        mobile_number="+91 9999988888"
    )
    db.add(contact)
    db.flush()

    lead = Lead(
        lead_id="LEAD-TEST-HIST",
        lead_name="Historical Lead Test",
        business_area="Biogas",
        requirement_type="Direct Product/Service",
        requested_product_service="Bio-Culture 500L",
        contact_id=contact.id,
        assigned_to_user_id=target_id,
        lifecycle_status="Open"
    )
    db.add(lead)
    db.commit()
    lead_id = lead.id
    db.close()

    try:
        # Disable CRM access for target user
        res = client.post(f"/api/v1/crm/users/{target_id}/access", json={"enabled": False}, headers=headers)
        assert res.status_code == 200

        # Verify historical lead is NOT deleted and still assigned to target_id
        db_check = SessionLocal()
        preserved_lead = db_check.query(Lead).filter(Lead.id == lead_id).first()
        assert preserved_lead is not None
        assert preserved_lead.assigned_to_user_id == target_id
        db_check.close()
    finally:
        # Clean up test lead and contact
        db_cleanup = SessionLocal()
        db_cleanup.query(Lead).filter(Lead.lead_id == "LEAD-TEST-HIST").delete()
        db_cleanup.query(Contact).filter(Contact.contact_id == "CON-TEST-HIST").delete()
        db_cleanup.commit()
        db_cleanup.close()


def test_audit_logs_recorded_for_crm_user_hub_actions(setup_crm_test_environment):
    headers = get_token_headers("test_crm_admin_user", "CrmAdmin123!", "CRM_ADMIN")
    
    db = SessionLocal()
    target_user = db.query(User).filter(User.username == "test_crm_target_candidate").first()
    target_id = target_user.id
    db.close()

    # Trigger CRM access grant
    res = client.post(f"/api/v1/crm/users/{target_id}/access", json={"enabled": True, "roleCode": "CRM_SALES_EXECUTIVE"}, headers=headers)
    assert res.status_code == 200

    # Verify audit log was created
    db_audit = SessionLocal()
    log = db_audit.query(AuditLog).filter(
        AuditLog.action == "CRM_USER_ACCESS_GRANTED",
        AuditLog.target_employee_id == target_id
    ).order_by(AuditLog.timestamp.desc()).first()
    assert log is not None
    assert "CRM_SALES_EXECUTIVE" in (log.details or "")
    db_audit.close()


def test_permission_and_module_seeding_is_idempotent():
    """Ensure repeatedly running ensure_roles_and_permissions and ensure_modules_and_memberships creates no duplicates."""
    ensure_roles_and_permissions()
    ensure_modules_and_memberships()
    ensure_roles_and_permissions()
    ensure_modules_and_memberships()

    db = SessionLocal()
    try:
        crm_mod = db.query(Module).filter(Module.code == "CRM").first()
        assert crm_mod is not None

        # Verify unique roles in CRM
        roles = db.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id).all()
        role_codes = [r.code for r in roles]
        assert len(role_codes) == len(set(role_codes)), "CRM role codes must be unique"

        # Verify unique permissions for CRM_ADMIN
        admin_role = next(r for r in roles if r.code == "CRM_ADMIN")
        perm_codes = [p.code for p in admin_role.permissions]
        assert len(perm_codes) == len(set(perm_codes)), "Role permissions must not contain duplicates"
    finally:
        db.close()
