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

            if needs_lead_recreate:
                conn.exec_driver_sql("DROP TABLE IF EXISTS lead_additional_contacts")
                conn.exec_driver_sql("DROP TABLE IF EXISTS lead_requirement_types")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_testing_charges")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_sample_test_requests")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_sample_submissions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_product_transactions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_consulting_engagements")
                conn.exec_driver_sql("DROP TABLE IF EXISTS lead_communication_history")
                conn.exec_driver_sql("DROP TABLE IF EXISTS leads")
                conn.commit()

            chg_cols = conn.exec_driver_sql("PRAGMA table_info(crm_testing_charges)").fetchall()
            if chg_cols and not any(c[1] == 'agreed_unit_rate' for c in chg_cols):
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_testing_charges")
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




