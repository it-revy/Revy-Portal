import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, SessionLocal, engine, get_db
from app.main import app
from seed.seed_development import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    if os.getenv("RUN_SEED") == "1":
        seed_database()
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
