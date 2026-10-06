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

@pytest.fixture
def ceo_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "rajneesh", "password": "Rajneesh123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "CEO"
    }

@pytest.fixture
def director_analytics_headers(client):
    db = SessionLocal()
    from app.users.model import User
    from app.roles.model import Role
    from app.employees.model import Employee
    from app.core.security import get_password_hash

    dir_role = db.query(Role).filter(Role.code == "DIRECTOR_ANALYTICS").first()
    u = db.query(User).filter(User.username == "director.analytics").first()
    if not u:
        u = User(
            username="director.analytics",
            email="director.analytics@company.com",
            password_hash=get_password_hash("Director123"),
            status="active"
        )
        if dir_role:
            u.roles = [dir_role]
        db.add(u)
        db.flush()

        emp = Employee(
            user_id=u.id,
            employee_id="EMP-DIR01",
            name="Director Analytics User",
            email="director.analytics@company.com",
            department="Executive Office",
            designation="Director Analytics",
            status="active"
        )
        db.add(emp)
        db.commit()
    elif dir_role and dir_role not in u.roles:
        u.roles.append(dir_role)
        db.commit()
    db.close()

    res = client.post("/api/v1/auth/login", json={"username": "director.analytics", "password": "Director123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Role-Used": "DIRECTOR_ANALYTICS"
    }

