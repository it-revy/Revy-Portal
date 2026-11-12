import os
import sys
import pytest
from fastapi.testclient import TestClient

os.environ["TESTING"] = "1"

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, SessionLocal, engine, get_db, init_db
from app.main import app
from seed.seed_development import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    with engine.connect() as conn:
        try:
            res = conn.exec_driver_sql("PRAGMA table_info(leads)").fetchall()
            needs_lead_recreate = False
            lead_name_col = next((c for c in res if c[1] == 'lead_name'), None)
            if lead_name_col and lead_name_col[3] == 1:
                needs_lead_recreate = True
            if res and not any(c[1] == 'connected_date' for c in res):
                needs_lead_recreate = True
            if res and not any(c[1] == 'company_name' for c in res):
                needs_lead_recreate = True
            contact_id_col = next((c for c in res if c[1] == 'contact_id'), None)
            if contact_id_col and contact_id_col[3] == 1:
                needs_lead_recreate = True

            if needs_lead_recreate:
                conn.exec_driver_sql("DROP TABLE IF EXISTS lead_contact_methods")
                conn.exec_driver_sql("DROP TABLE IF EXISTS lead_additional_contacts")
                conn.exec_driver_sql("DROP TABLE IF EXISTS lead_requirement_types")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_testing_charges")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_sample_test_requests")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_sample_submissions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_product_transactions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_consulting_engagements")
                conn.exec_driver_sql("DROP TABLE IF EXISTS lead_communications")
                conn.exec_driver_sql("DROP TABLE IF EXISTS lead_communication_history")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_opportunities")
                conn.exec_driver_sql("DROP TABLE IF EXISTS leads")
                conn.commit()

            chg_cols = conn.exec_driver_sql("PRAGMA table_info(crm_testing_charges)").fetchall()
            if chg_cols and not any(c[1] == 'agreed_unit_rate' for c in chg_cols):
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_testing_charges")
                conn.commit()

            opp_cols = conn.exec_driver_sql("PRAGMA table_info(crm_opportunities)").fetchall()
            opp_acc_col = next((c for c in opp_cols if c[1] == 'account_id'), None)
            if opp_cols and (not any(c[1] == 'stage' for c in opp_cols) or (opp_acc_col and opp_acc_col[3] == 1)):
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_opportunity_quotations")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_milestones")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_product_transactions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_sample_submissions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_consulting_engagements")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_opportunities")
                conn.commit()

            if opp_cols and not any(c[1] == 'sub_status' for c in opp_cols):
                conn.exec_driver_sql("ALTER TABLE crm_opportunities ADD COLUMN sub_status VARCHAR(255)")
                conn.commit()

            lead_cols = conn.exec_driver_sql("PRAGMA table_info(leads)").fetchall()
            if lead_cols and not any(c[1] == 'legacy_lifecycle_status' for c in lead_cols):
                conn.exec_driver_sql("ALTER TABLE leads ADD COLUMN legacy_lifecycle_status VARCHAR(50)")
                conn.commit()

            comm_cols = conn.exec_driver_sql("PRAGMA table_info(lead_communications)").fetchall()
            if comm_cols and not any(c[1] == 'subject' for c in comm_cols):
                conn.exec_driver_sql("ALTER TABLE lead_communications ADD COLUMN subject VARCHAR(255)")
            if comm_cols and not any(c[1] == 'interaction_source' for c in comm_cols):
                conn.exec_driver_sql("ALTER TABLE lead_communications ADD COLUMN interaction_source VARCHAR(50) DEFAULT 'Manual'")
            if comm_cols and not any(c[1] == 'nurturing_activity_id' for c in comm_cols):
                conn.exec_driver_sql("ALTER TABLE lead_communications ADD COLUMN nurturing_activity_id VARCHAR(36)")
            if comm_cols and not any(c[1] == 'updated_at' for c in comm_cols):
                conn.exec_driver_sql("ALTER TABLE lead_communications ADD COLUMN updated_at TIMESTAMP")
            conn.commit()

            acc_cols = conn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()
            existing_acc = [c[1] for c in acc_cols]
            for col, col_type in [
                ("site_name", "VARCHAR(255)"),
                ("business_area", "VARCHAR(50)"),
                ("country", "VARCHAR(100)"),
                ("state", "VARCHAR(100)"),
                ("city", "VARCHAR(100)"),
                ("billing_address", "TEXT"),
                ("shipping_address", "TEXT"),
                ("gst_number", "VARCHAR(30)"),
                ("pan_number", "VARCHAR(20)"),
                ("parent_account_id", "VARCHAR(36)"),
                ("created_by_id", "VARCHAR(36)"),
                ("updated_by_id", "VARCHAR(36)"),
            ]:
                if acc_cols and col not in existing_acc:
                    conn.exec_driver_sql(f"ALTER TABLE accounts ADD COLUMN {col} {col_type}")
            conn.commit()

            con_cols = conn.exec_driver_sql("PRAGMA table_info(contacts)").fetchall()
            existing_con = [c[1] for c in con_cols]
            for col, col_type in [
                ("first_name", "VARCHAR(100)"),
                ("last_name", "VARCHAR(100)"),
                ("whatsapp_number", "VARCHAR(30)"),
                ("is_primary", "BOOLEAN DEFAULT 0"),
                ("created_by_id", "VARCHAR(36)"),
                ("updated_by_id", "VARCHAR(36)"),
            ]:
                if con_cols and col not in existing_con:
                    conn.exec_driver_sql(f"ALTER TABLE contacts ADD COLUMN {col} {col_type}")
            conn.commit()

            if lead_cols:
                existing_lead = [c[1] for c in lead_cols]
                for col, col_type in [
                    ("disqualification_reason", "TEXT"),
                    ("converted_at", "DATETIME"),
                    ("converted_by_id", "VARCHAR(36)"),
                ]:
                    if col not in existing_lead:
                        conn.exec_driver_sql(f"ALTER TABLE leads ADD COLUMN {col} {col_type}")
                conn.commit()

            if opp_cols:
                existing_opp = [c[1] for c in opp_cols]
                for col, col_type in [
                    ("won_reason", "TEXT"),
                    ("closed_by_id", "VARCHAR(36)"),
                    ("reopened_at", "DATETIME"),
                    ("reopened_by_id", "VARCHAR(36)"),
                ]:
                    if col not in existing_opp:
                        conn.exec_driver_sql(f"ALTER TABLE crm_opportunities ADD COLUMN {col} {col_type}")
                conn.commit()

            srv_cols = conn.exec_driver_sql("PRAGMA table_info(crm_services)").fetchall()
            if srv_cols and any(c[1] == 'subcategory_id' for c in srv_cols):
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_quotation_items")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_package_components")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_package_versions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_packages")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_service_price_history")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_services")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_service_subcategories")
                conn.commit()
        except Exception:
            pass
    init_db()
    if os.getenv("RUN_SEED") == "1":
        seed_database()
        from app.core.init_roles import ensure_roles_and_permissions
        from app.core.init_modules import ensure_modules_and_memberships
        ensure_roles_and_permissions()
        ensure_modules_and_memberships()
    yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(client):
    # Log in as IT Admin
    res = client.post("/api/v1/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "IT_ADMIN"
    }

@pytest.fixture
def employee_headers(client):
    # Log in as normal employee Jyoti
    res = client.post("/api/v1/auth/login", json={"username": "jyoti", "password": "Jyoti123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "EMPLOYEE"
    }

@pytest.fixture
def finance_headers(client):
    # Log in as Finance Manager
    res = client.post("/api/v1/auth/login", json={"username": "finance.manager", "password": "Finance123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "FINANCE_MANAGER"
    }

@pytest.fixture
def breakfast_admin_headers(client):
    # Log in as Breakfast Admin Faiz
    res = client.post("/api/v1/auth/login", json={"username": "faiz", "password": "Faiz123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "BREAKFAST_ADMIN"
    }

@pytest.fixture
def ceo_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "rajneesh", "password": "Rajneesh123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "CEO"
    }




