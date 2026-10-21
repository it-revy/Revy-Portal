import os
import sys
import uuid

sys.path.insert(0, os.path.abspath("backend"))
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///backend/test_isolated_suite.db"

import app.models
from fastapi.testclient import TestClient
from app.main import app
from seed.seed_development import seed_database

seed_database()

with TestClient(app) as client:
    # Login as admin
    admin_res = client.post("/api/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    admin_token = admin_res.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    uid = uuid.uuid4().hex[:6]
    emp_username = f"user_{uid}"

    user_res = client.post("/api/users", headers=headers, json={
        "name": f"Employee {uid.upper()}",
        "username": emp_username,
        "email": f"{emp_username}@example.com",
        "phone": "+91 8888877777",
        "password": "Password123!",
        "status": "active"
    })
    print("User created:", user_res.status_code, user_res.json())

    user_login_res = client.post("/api/auth/login", json={
        "username": emp_username,
        "password": "Password123!"
    })
    user_token = user_login_res.json()["token"]
    print("Login token payload roles:", user_login_res.json()["user"]["roles"])
    print("Login token payload modules:", user_login_res.json()["user"]["modules"])

    user_headers = {"Authorization": f"Bearer {user_token}"}
    bms_res = client.get("/api/breakfast/today", headers=user_headers)
    print("bms_res status:", bms_res.status_code)
    print("bms_res body:", bms_res.text)
