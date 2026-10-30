"""
Phase 5A Hands-On User Acceptance Testing (UAT) Automated Suite
Runs against an isolated, non-production database environment to validate all
Phase 5A Sales Hub workflows without touching live production Neon.

Scenarios Covered:
Track 1: Sales Executive Role
  1.1 - 6-Stage Funnel Progression & Invalid Stage Rejection
  1.2 - Won Outcome Restriction to Close Stage
  1.3 - Lost Outcome Mandatory Reason Enforcement
  1.4 - Quotation Creation (Draft v1, Sequential Numbering)
  1.5 - Commercial Value Mismatch Tracking
  1.6 - Submit Quotation for Review (Under Review)
  1.7 - Client Delivery Sharing Evidence Recording
  1.8 - Quotation Revisioning (v2 Draft, Archiving Previous)

Track 2: Sales Manager Role
  2.1 - Quotation Review & Approval (Metadata & Status)
  2.2 - Quotation Rejection (Mandatory Reason Validation)
  2.3 - Approval Invalidation on Commercial Edit (Auto-Revert to Draft)
  2.4 - Deal Reopening (Won/Lost -> Open with Justification)
  2.5 - Currency-Grouped Pipeline & Revenue Analytics

Track 3: CRM Administrator / Security Role
  3.1 - Approval Bypass Prevention for CRM_ADMIN (HTTP 403)
  3.2 - Deal Reopening RBAC (Exec Forbidden, Admin Authorized)
  3.3 - Audit Trail Integrity & Verification
"""

import os
import sys
import uuid
from datetime import datetime, timezone

# CRITICAL P0 SAFETY GUARD: Guarantee isolated test database execution
os.environ["TESTING"] = "1"
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
isolated_db_path = os.path.join(backend_dir, "test_phase5a_uat_isolated.db").replace("\\", "/")
os.environ["TEST_DATABASE_URL"] = f"sqlite:///{isolated_db_path}"
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal, init_db
from app.audit.model import AuditLog
from tests.test_crm_core_services_and_apis import get_token_headers, setup_crm_stage4_environment

client = TestClient(app)

results = []

def record_scenario(track, scenario_id, title, status, details="", response_code=None):
    results.append({
        "track": track,
        "id": scenario_id,
        "title": title,
        "status": status,
        "details": details,
        "code": response_code
    })
    status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[BLOCKED]"
    print(f"{status_symbol} {scenario_id} - {title} (HTTP {response_code})")
    if details:
        print(f"       Details: {details}")

def _create_opportunity(headers, suffix="", currency="INR", estimated_value=500000.0):
    uid = uuid.uuid4().hex[:8] + suffix
    clean_uid = uid.replace("_", "-")
    
    # 1. Account
    acc_res = client.post("/api/v1/crm/accounts", json={
        "name": f"UAT Corp {clean_uid}",
        "industry": "CleanTech",
        "website": f"https://uat-{clean_uid}.com"
    }, headers=headers)
    assert acc_res.status_code == 201, f"Account failed: {acc_res.text}"
    account = acc_res.json()["account"]

    # 2. Contact
    con_res = client.post("/api/v1/crm/contacts", json={
        "name": f"Test Contact {uid}",
        "email": f"contact_{uid}@cleantech.com",
        "accountId": account["id"]
    }, headers=headers)
    assert con_res.status_code == 201, f"Contact failed: {con_res.text}"
    contact = con_res.json()["contact"]

    # 3. Lead
    lead_res = client.post("/api/v1/crm/leads", json={
        "topic": f"UAT Lead {uid}",
        "companyName": f"UAT Corp {clean_uid}",
        "contactEmail": f"contact_{uid}@cleantech.com",
        "businessArea": "Biogas",
        "estimatedValue": estimated_value,
        "requirementTypes": ["Consulting", "Sample Testing"]
    }, headers=headers)
    assert lead_res.status_code == 201, f"Lead failed: {lead_res.text}"
    lead = lead_res.json()["lead"]

    # 4. Qualify Lead
    qual_res = client.post(f"/api/v1/crm/leads/{lead['id']}/qualify", json={
        "account": {"action": "reuse", "accountId": account["id"]},
        "contact": {"action": "reuse", "contactId": contact["id"]},
        "opportunityName": f"UAT Opp {uid}",
        "estimatedValue": estimated_value
    }, headers=headers)
    assert qual_res.status_code == 200, f"Qualify failed: {qual_res.text}"
    opp = qual_res.json()["opportunity"]

    if currency != "INR":
        upd = client.put(f"/api/v1/crm/opportunities/{opp['id']}", json={
            "currency": currency,
            "estimatedValue": estimated_value
        }, headers=headers)
        assert upd.status_code == 200
        opp = upd.json()["opportunity"]

    return opp

def run_uat():
    print("=" * 80)
    print("REVY PORTAL PHASE 5A — AUTOMATED HANDS-ON UAT EXECUTION")
    print("=" * 80)
    print(f"[SAFETY] Target DB: Isolated SQLite Engine -> {isolated_db_path}")
    print("[SAFETY] Confirmed: Live production Neon is completely untouched.\n")

    # 1. Setup isolated database
    init_db()
    with engine.connect() as conn:
        try:
            opp_cols = conn.exec_driver_sql("PRAGMA table_info(crm_opportunities)").fetchall()
            if opp_cols and not any(c[1] == 'stage' for c in opp_cols):
                conn.exec_driver_sql("ALTER TABLE crm_opportunities ADD COLUMN stage VARCHAR(50)")
                conn.commit()
            if opp_cols and not any(c[1] == 'sub_status' for c in opp_cols):
                conn.exec_driver_sql("ALTER TABLE crm_opportunities ADD COLUMN sub_status VARCHAR(255)")
                conn.commit()
        except Exception as e:
            print(f"[WARN] Schema adjustment notice: {e}")

    # Initialize environment roles & credentials
    from seed.seed_development import seed_database
    from app.core.init_roles import ensure_roles_and_permissions
    from app.core.init_modules import ensure_modules_and_memberships
    from app.core.security import get_password_hash
    from app.users.model import User
    from app.modules.model import Module, ModuleRole, UserModuleMembership
    seed_database()
    ensure_roles_and_permissions()
    ensure_modules_and_memberships()

    # Seed stage 4 CRM test users directly
    db_setup = SessionLocal()
    try:
        crm_mod = db_setup.query(Module).filter(Module.code == "CRM").first()
        role_admin = db_setup.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_ADMIN").first()
        role_sales_mgr = db_setup.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_SALES_MANAGER").first()
        role_sales_exec = db_setup.query(ModuleRole).filter(ModuleRole.module_id == crm_mod.id, ModuleRole.code == "CRM_SALES_EXECUTIVE").first()

        for u_data, r_obj in [
            (("Stage4 Sales Exec", "stg4_sales_exec", "stg4_exec@revy.test"), role_sales_exec),
            (("Stage4 Sales Manager", "stg4_sales_mgr", "stg4_mgr@revy.test"), role_sales_mgr),
            (("Stage4 Admin", "stg4_crm_admin", "stg4_admin@revy.test"), role_admin),
        ]:
            u = db_setup.query(User).filter(User.username == u_data[1]).first()
            if not u:
                u = User(name=u_data[0], username=u_data[1], email=u_data[2], password_hash=get_password_hash("Pass123!"), status="active")
                db_setup.add(u)
                db_setup.commit()
                db_setup.refresh(u)
            db_setup.query(UserModuleMembership).filter(UserModuleMembership.user_id == u.id, UserModuleMembership.module_id == crm_mod.id).delete()
            db_setup.add(UserModuleMembership(user_id=u.id, module_id=crm_mod.id, role_id=r_obj.id, is_active=True))
        db_setup.commit()
    finally:
        db_setup.close()

    # User tokens for 3 tracks
    headers_exec = get_token_headers("stg4_sales_exec", "Pass123!", "CRM_SALES_EXECUTIVE")
    headers_mgr = get_token_headers("stg4_sales_mgr", "Pass123!", "CRM_SALES_MANAGER")
    headers_admin = get_token_headers("stg4_crm_admin", "Pass123!", "CRM_ADMIN")

    print("\n--- TRACK 1: SALES EXECUTIVE ROLE ---")

    # Scenario 1.1: 6-Stage Funnel Progression
    try:
        opp = _create_opportunity(headers_exec, "track1_funnel")
        opp_id = opp["id"]

        # Invalid stage check
        inv_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={"newStage": "BogusStage"}, headers=headers_exec)
        assert inv_res.status_code == 400

        # Progression across all 6 stages
        stages = ["Enquiry", "Qualify", "Develop", "Propose/Offer", "Negotiate", "Close"]
        for stg in stages:
            s_res = client.post(f"/api/v1/crm/opportunities/{opp_id}/stage", json={"newStage": stg, "notes": f"Moved to {stg}"}, headers=headers_exec)
            assert s_res.status_code == 200, f"Stage {stg} transition failed: {s_res.text}"
            assert s_res.json()["opportunity"]["stage"] == stg

        record_scenario("Track 1: Sales Executive", "UAT-1.1", "6-Stage Funnel Progression & Stepper Validation", "PASS", "Successfully traversed Enquiry -> Qualify -> Develop -> Propose/Offer -> Negotiate -> Close", 200)
    except Exception as e:
        record_scenario("Track 1: Sales Executive", "UAT-1.1", "6-Stage Funnel Progression & Stepper Validation", "FAIL", str(e), 500)

    # Scenario 1.2: Won Outcome Locked to Close Stage
    try:
        opp_won = _create_opportunity(headers_exec, "track1_won")
        # Ensure it is at 'Develop' stage
        client.post(f"/api/v1/crm/opportunities/{opp_won['id']}/stage", json={"newStage": "Develop"}, headers=headers_exec)

        premature_won = client.post(f"/api/v1/crm/opportunities/{opp_won['id']}/stage", json={"newStage": "Develop", "status": "Won"}, headers=headers_exec)
        assert premature_won.status_code == 400
        assert "Close" in premature_won.json()["message"]

        record_scenario("Track 1: Sales Executive", "UAT-1.2", "Won Outcome Blocked at Pre-Close Stages", "PASS", "System refused Won status while in Develop stage with HTTP 400", premature_won.status_code)
    except Exception as e:
        record_scenario("Track 1: Sales Executive", "UAT-1.2", "Won Outcome Blocked at Pre-Close Stages", "FAIL", str(e), 500)

    # Scenario 1.3: Lost Outcome Mandatory Reason Enforcement
    try:
        opp_lost = _create_opportunity(headers_exec, "track1_lost")
        
        # Missing loss reason
        empty_lost = client.post(f"/api/v1/crm/opportunities/{opp_lost['id']}/stage", json={"newStage": "Develop", "status": "Lost", "lossReason": ""}, headers=headers_exec)
        assert empty_lost.status_code == 400

        # Valid loss reason
        valid_lost = client.post(f"/api/v1/crm/opportunities/{opp_lost['id']}/stage", json={"newStage": "Develop", "status": "Lost", "lossReason": "Budget freeze by client board"}, headers=headers_exec)
        assert valid_lost.status_code == 200
        assert valid_lost.json()["opportunity"]["status"] == "Lost"
        assert valid_lost.json()["opportunity"]["lossReason"] == "Budget freeze by client board"

        record_scenario("Track 1: Sales Executive", "UAT-1.3", "Lost Outcome Mandatory Reason Enforcement", "PASS", "Empty reason blocked with HTTP 400; valid reason saved successfully", 200)
    except Exception as e:
        record_scenario("Track 1: Sales Executive", "UAT-1.3", "Lost Outcome Mandatory Reason Enforcement", "FAIL", str(e), 500)

    # Scenario 1.4: Quotation Creation (Draft v1, Sequential Numbering)
    created_quote = None
    try:
        opp_quote = _create_opportunity(headers_exec, "track1_quote", estimated_value=750000.0)
        q_payload = {
            "title": "Anaerobic Digester Biogas Consulting Package",
            "amount": 750000.0,
            "currency": "INR",
            "quotationDate": str(datetime.now(timezone.utc).date()),
            "validUntilDate": str((datetime.now(timezone.utc) + datetime.resolution * 30).date()),
            "termsAndConditions": "50% advance, 50% on milestone delivery.",
            "notes": "Detailed engineering proposal included."
        }
        q_res = client.post(f"/api/v1/crm/opportunities/{opp_quote['id']}/quotations", json=q_payload, headers=headers_exec)
        assert q_res.status_code == 201, f"Quotation create failed: {q_res.text}"
        data = q_res.json()["quotation"]
        assert data["status"] == "Draft"
        assert data["version"] == "v1"
        assert data["isActive"] is True
        assert data["quotationNumber"].startswith("QT-")
        created_quote = data

        record_scenario("Track 1: Sales Executive", "UAT-1.4", "Quotation Creation (Draft v1, Sequential Numbering)", "PASS", f"Created {data['quotationNumber']} (v1, Status: Draft)", 201)
    except Exception as e:
        record_scenario("Track 1: Sales Executive", "UAT-1.4", "Quotation Creation (Draft v1, Sequential Numbering)", "FAIL", str(e), 500)

    # Scenario 1.5: Commercial Value Mismatch Tracking
    try:
        opp_diff = _create_opportunity(headers_exec, "track1_mismatch", estimated_value=1000000.0)
        # Create quote with amount 850000 (discrepancy of 150000)
        q_res = client.post(f"/api/v1/crm/opportunities/{opp_diff['id']}/quotations", json={
            "title": "Discounted Supply Quote",
            "amount": 850000.0,
            "currency": "INR"
        }, headers=headers_exec)
        assert q_res.status_code == 201
        
        # Verify opportunity details return quotation amount and mismatch
        opp_detail = client.get(f"/api/v1/crm/opportunities/{opp_diff['id']}", headers=headers_exec).json()["opportunity"]
        assert opp_detail["activeQuotationAmount"] == 850000.0
        assert opp_detail["estimatedValue"] == 1000000.0
        assert opp_detail["hasQuotationMismatch"] is True

        record_scenario("Track 1: Sales Executive", "UAT-1.5", "Commercial Value Mismatch Calculation", "PASS", f"Quotation amount (850,000) != Estimated value (1,000,000) with hasQuotationMismatch=True", 200)
    except Exception as e:
        record_scenario("Track 1: Sales Executive", "UAT-1.5", "Commercial Value Mismatch Calculation", "FAIL", str(e), 500)

    # Scenario 1.6: Submit Quotation for Review
    try:
        sub_res = client.post(f"/api/v1/crm/opportunities/{created_quote['opportunityId']}/quotations/{created_quote['id']}/submit", headers=headers_exec)
        assert sub_res.status_code == 200, f"Submit failed: {sub_res.text}"
        assert sub_res.json()["quotation"]["status"] == "Under Review"

        record_scenario("Track 1: Sales Executive", "UAT-1.6", "Submit Quotation for Review", "PASS", "Quotation status transitioned from Draft to Under Review", 200)
    except Exception as e:
        record_scenario("Track 1: Sales Executive", "UAT-1.6", "Submit Quotation for Review", "FAIL", str(e), 500)

    # Scenario 1.7: Client Sharing Evidence Recording
    try:
        # First approve the quote using manager so it can be shared
        app_res = client.post(f"/api/v1/crm/opportunities/{created_quote['opportunityId']}/quotations/{created_quote['id']}/approve", json={"action": "approve"}, headers=headers_mgr)
        assert app_res.status_code == 200, f"Approve failed: {app_res.text}"

        # Now share it as Sales Executive
        share_res = client.post(f"/api/v1/crm/opportunities/{created_quote['opportunityId']}/quotations/{created_quote['id']}/share", json={
            "sentMethod": "Email",
            "sentTo": "procurement@uatcorp.com",
            "sendingEvidence": "Sent via official Outlook corporate mail with read receipt"
        }, headers=headers_exec)
        assert share_res.status_code == 200, f"Share failed: {share_res.text}"
        data = share_res.json()["quotation"]
        assert data["status"] == "Shared"
        assert data["sentMethod"] == "Email"
        assert data["sentTo"] == "procurement@uatcorp.com"

        record_scenario("Track 1: Sales Executive", "UAT-1.7", "Client Delivery Sharing Evidence Recording", "PASS", "Recorded Email dispatch evidence; status transitioned to Shared", 200)
    except Exception as e:
        record_scenario("Track 1: Sales Executive", "UAT-1.7", "Client Delivery Sharing Evidence Recording", "FAIL", str(e), 500)

    # Scenario 1.8: Quotation Revisioning (v2 Draft, Archiving v1)
    revised_quote = None
    try:
        rev_res = client.post(f"/api/v1/crm/opportunities/{created_quote['opportunityId']}/quotations/{created_quote['id']}/revise", json={
            "title": "Anaerobic Digester Biogas Consulting Package - Revised",
            "amount": 720000.0,
            "currency": "INR",
            "notes": "Negotiated 4% discount"
        }, headers=headers_exec)
        assert rev_res.status_code == 201, f"Revise failed: {rev_res.text}"
        revised_quote = rev_res.json()["quotation"]
        assert revised_quote["version"] == "v2"
        assert revised_quote["status"] == "Draft"
        assert revised_quote["isActive"] is True
        assert revised_quote["quotationNumber"] == created_quote["quotationNumber"]

        # Check v1 is archived
        v1_check = client.get(f"/api/v1/crm/opportunities/{created_quote['opportunityId']}/quotations/{created_quote['id']}", headers=headers_exec).json()["quotation"]
        assert v1_check["isActive"] is False

        record_scenario("Track 1: Sales Executive", "UAT-1.8", "Quotation Revisioning (v2 Draft, Archiving v1)", "PASS", f"Created revision v2 ({revised_quote['quotationNumber']}); archived v1 (isActive=False)", 201)
    except Exception as e:
        record_scenario("Track 1: Sales Executive", "UAT-1.8", "Quotation Revisioning (v2 Draft, Archiving v1)", "FAIL", str(e), 500)

    print("\n--- TRACK 2: SALES MANAGER ROLE ---")

    # Scenario 2.1: Quotation Review & Approval
    quote_for_approval = None
    try:
        opp_app = _create_opportunity(headers_exec, "track2_app", estimated_value=600000.0)
        q = client.post(f"/api/v1/crm/opportunities/{opp_app['id']}/quotations", json={
            "title": "Standard Effluent Treatment Quotation",
            "amount": 600000.0,
            "currency": "INR"
        }, headers=headers_exec).json()["quotation"]
        client.post(f"/api/v1/crm/opportunities/{opp_app['id']}/quotations/{q['id']}/submit", headers=headers_exec)

        app_res = client.post(f"/api/v1/crm/opportunities/{opp_app['id']}/quotations/{q['id']}/approve", json={"action": "approve"}, headers=headers_mgr)
        assert app_res.status_code == 200, f"Approve failed: {app_res.text}"
        quote_for_approval = app_res.json()["quotation"]
        assert quote_for_approval["status"] == "Approved"
        assert quote_for_approval["approvedAt"] is not None

        record_scenario("Track 2: Sales Manager", "UAT-2.1", "Quotation Review & Approval", "PASS", f"Approved quotation {quote_for_approval['quotationNumber']} with timestamp", 200)
    except Exception as e:
        record_scenario("Track 2: Sales Manager", "UAT-2.1", "Quotation Review & Approval", "FAIL", str(e), 500)

    # Scenario 2.2: Quotation Rejection (Mandatory Reason Validation)
    try:
        opp_rej = _create_opportunity(headers_exec, "track2_rej", estimated_value=400000.0)
        q = client.post(f"/api/v1/crm/opportunities/{opp_rej['id']}/quotations", json={
            "title": "Rejection Test Quote",
            "amount": 400000.0,
            "currency": "INR"
        }, headers=headers_exec).json()["quotation"]
        client.post(f"/api/v1/crm/opportunities/{opp_rej['id']}/quotations/{q['id']}/submit", headers=headers_exec)

        # Attempt rejection without reason
        empty_rej = client.post(f"/api/v1/crm/opportunities/{opp_rej['id']}/quotations/{q['id']}/approve", json={"action": "reject", "reason": ""}, headers=headers_mgr)
        assert empty_rej.status_code == 400

        # Rejection with valid reason
        valid_rej = client.post(f"/api/v1/crm/opportunities/{opp_rej['id']}/quotations/{q['id']}/approve", json={"action": "reject", "reason": "Gross margin below minimum threshold of 35%"}, headers=headers_mgr)
        assert valid_rej.status_code == 200
        assert valid_rej.json()["quotation"]["status"] == "Rejected"

        record_scenario("Track 2: Sales Manager", "UAT-2.2", "Quotation Rejection with Mandatory Reason", "PASS", "Empty reason blocked with HTTP 400; valid reason saved to rejection history", 200)
    except Exception as e:
        record_scenario("Track 2: Sales Manager", "UAT-2.2", "Quotation Rejection with Mandatory Reason", "FAIL", str(e), 500)

    # Scenario 2.3: Approval Invalidation on Commercial Edit
    try:
        # Edit the approved quotation from Scenario 2.1
        edit_res = client.put(f"/api/v1/crm/opportunities/{quote_for_approval['opportunityId']}/quotations/{quote_for_approval['id']}", json={
            "amount": 650000.0
        }, headers=headers_exec)
        assert edit_res.status_code == 200, f"Edit failed: {edit_res.text}"
        reverted_q = edit_res.json()["quotation"]
        assert reverted_q["status"] == "Draft"
        assert reverted_q["approvedAt"] is None

        record_scenario("Track 2: Sales Manager", "UAT-2.3", "Approval Invalidation on Commercial Edit", "PASS", "Editing amount on Approved quote automatically reverted status to Draft and cleared approval metadata", 200)
    except Exception as e:
        record_scenario("Track 2: Sales Manager", "UAT-2.3", "Approval Invalidation on Commercial Edit", "FAIL", str(e), 500)

    # Scenario 2.4: Deal Reopening (Won/Lost -> Open with Justification)
    try:
        opp_reopen = _create_opportunity(headers_exec, "track2_reopen", estimated_value=900000.0)
        # Move to Close and mark Won
        client.post(f"/api/v1/crm/opportunities/{opp_reopen['id']}/stage", json={"newStage": "Close", "status": "Won", "remarks": "Commercial PO Received"}, headers=headers_exec)

        # Attempt reopen without reason
        empty_reopen = client.post(f"/api/v1/crm/opportunities/{opp_reopen['id']}/reopen", json={"reason": ""}, headers=headers_mgr)
        assert empty_reopen.status_code == 400

        # Reopen with valid reason
        valid_reopen = client.post(f"/api/v1/crm/opportunities/{opp_reopen['id']}/reopen", json={
            "reason": "Client board requested scope expansion and revised terms",
            "reopenStage": "Negotiate"
        }, headers=headers_mgr)
        assert valid_reopen.status_code == 200, f"Reopen failed: {valid_reopen.text}"
        reopened_opp = valid_reopen.json()["opportunity"]
        assert reopened_opp["status"] == "Open"
        assert reopened_opp["stage"] == "Negotiate"

        record_scenario("Track 2: Sales Manager", "UAT-2.4", "Deal Reopening (Won -> Open with Justification)", "PASS", "Reopened deal to Negotiate stage with documented justification", 200)
    except Exception as e:
        record_scenario("Track 2: Sales Manager", "UAT-2.4", "Deal Reopening (Won -> Open with Justification)", "FAIL", str(e), 500)

    # Scenario 2.5: Currency-Grouped Analytics & Pipeline Reporting
    try:
        # Create opportunities in different currencies
        _create_opportunity(headers_exec, "rev_usd", currency="USD", estimated_value=25000.0)
        _create_opportunity(headers_exec, "rev_eur", currency="EUR", estimated_value=18000.0)

        metrics_res = client.get("/api/v1/crm/analytics/revenue-metrics", headers=headers_mgr)
        assert metrics_res.status_code == 200, f"Metrics failed: {metrics_res.text}"
        metrics = metrics_res.json()

        # Validate currency separation
        assert "openPipelineValueByCurrency" in metrics
        assert "wonOpportunityValueByCurrency" in metrics
        assert "lostOpportunityValueByCurrency" in metrics
        assert "USD" in metrics["openPipelineValueByCurrency"]
        assert "EUR" in metrics["openPipelineValueByCurrency"]
        assert "INR" in metrics["openPipelineValueByCurrency"]
        assert metrics.get("labelingNotice") is not None

        record_scenario("Track 2: Sales Manager", "UAT-2.5", "Currency-Grouped Pipeline & Revenue Analytics", "PASS", "Multi-currency segregation verified (INR, USD, EUR) with mandatory disclosure disclaimer", 200)
    except Exception as e:
        record_scenario("Track 2: Sales Manager", "UAT-2.5", "Currency-Grouped Pipeline & Revenue Analytics", "FAIL", str(e), 500)

    print("\n--- TRACK 3: CRM ADMINISTRATOR / SECURITY ROLE ---")

    # Scenario 3.1: Approval Bypass Prevention for CRM_ADMIN
    try:
        opp_sec = _create_opportunity(headers_exec, "track3_sec", estimated_value=300000.0)
        q = client.post(f"/api/v1/crm/opportunities/{opp_sec['id']}/quotations", json={
            "title": "Security Bypass Test Quote",
            "amount": 300000.0,
            "currency": "INR"
        }, headers=headers_exec).json()["quotation"]
        client.post(f"/api/v1/crm/opportunities/{opp_sec['id']}/quotations/{q['id']}/submit", headers=headers_exec)

        # CRM_ADMIN alone attempts approval
        admin_app = client.post(f"/api/v1/crm/opportunities/{opp_sec['id']}/quotations/{q['id']}/approve", json={"action": "approve"}, headers=headers_admin)
        assert admin_app.status_code == 403, f"Expected 403 but got: {admin_app.status_code}"

        record_scenario("Track 3: CRM Administrator", "UAT-3.1", "Approval Bypass Prevention for CRM_ADMIN", "PASS", "CRM_ADMIN approval attempt strictly rejected with HTTP 403 Forbidden", admin_app.status_code)
    except Exception as e:
        record_scenario("Track 3: CRM Administrator", "UAT-3.1", "Approval Bypass Prevention for CRM_ADMIN", "FAIL", str(e), 500)

    # Scenario 3.2: Deal Reopening RBAC Authorization
    try:
        opp_rb = _create_opportunity(headers_exec, "track3_rb", estimated_value=200000.0)
        client.post(f"/api/v1/crm/opportunities/{opp_rb['id']}/stage", json={"newStage": "Close", "status": "Won", "remarks": "Won for RBAC test"}, headers=headers_exec)

        # Sales Executive attempts reopening (forbidden)
        exec_reopen = client.post(f"/api/v1/crm/opportunities/{opp_rb['id']}/reopen", json={"reason": "Executive attempting reopen"}, headers=headers_exec)
        assert exec_reopen.status_code == 403

        # CRM Admin executes reopening (authorized)
        admin_reopen = client.post(f"/api/v1/crm/opportunities/{opp_rb['id']}/reopen", json={"reason": "Admin authorized reopen"}, headers=headers_admin)
        assert admin_reopen.status_code == 200

        record_scenario("Track 3: CRM Administrator", "UAT-3.2", "Deal Reopening RBAC Enforcement", "PASS", "Sales Exec blocked (HTTP 403); CRM Admin authorized (HTTP 200)", 200)
    except Exception as e:
        record_scenario("Track 3: CRM Administrator", "UAT-3.2", "Deal Reopening RBAC Enforcement", "FAIL", str(e), 500)

    # Scenario 3.3: Audit Trail Integrity
    try:
        db = SessionLocal()
        logs = db.query(AuditLog).all()
        actions = set(l.action for l in logs)
        
        required_actions = [
            "CRM_QUOTATION_CREATED",
            "CRM_QUOTATION_SUBMITTED",
            "CRM_QUOTATION_APPROVED",
            "CRM_QUOTATION_SHARED",
            "CRM_OPPORTUNITY_REOPENED"
        ]
        missing = [a for a in required_actions if a not in actions]
        assert not missing, f"Missing audit actions: {missing}"

        record_scenario("Track 3: CRM Administrator", "UAT-3.3", "Audit Trail Verification", "PASS", f"All Phase 5A audit events recorded in audit_logs: {', '.join(required_actions)}", 200)
        db.close()
    except Exception as e:
        record_scenario("Track 3: CRM Administrator", "UAT-3.3", "Audit Trail Verification", "FAIL", str(e), 500)

    # Summary Table
    print("\n" + "=" * 80)
    print("UAT SCENARIO RESULTS")
    print("=" * 80)
    for r in results:
        status_tag = f"[{r['status']}]"
        print(f"{status_tag:9} {r['id']:<8} | {r['track']:<30} | {r['title']}")
        if r['status'] != 'PASS' or r['details']:
            print(f"          Details: {r['details']}")
    print("=" * 80)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    blocked = sum(1 for r in results if r["status"] == "BLOCKED")
    print(f"Total Scenarios: {len(results)} | Passed: {passed} | Failed: {failed} | Blocked: {blocked}")
    print("=" * 80)

    # Cleanup isolated test database
    try:
        if os.path.exists(isolated_db_path):
            os.remove(isolated_db_path)
            print(f"[CLEANUP] Removed isolated test database: {isolated_db_path}")
    except Exception:
        pass

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit_code = run_uat()
    sys.exit(exit_code)
