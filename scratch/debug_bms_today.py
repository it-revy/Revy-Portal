import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///backend/test_isolated_suite.db"

import app.models
from fastapi.testclient import TestClient
from app.main import app

from seed.seed_development import seed_database
seed_database()

with TestClient(app) as client:
    # 1. Login as IT admin to create user
    admin_res = client.post("/api/v1/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    admin_token = admin_res.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create user without BMS
    u_res = client.post("/api/users", headers=headers, json={
        "name": "Test Nobody",
        "username": "test_nobody_1",
        "email": "test_nobody_1@example.com",
        "password": "Password123!",
        "status": "active"
    })
    print("Create user response:", u_res.status_code, u_res.json().get("name"))

    # 3. Login as test_nobody_1
    login_res = client.post("/api/auth/login", json={"username": "test_nobody_1", "password": "Password123!"})
    print("Login response user:", login_res.json().get("user"))
    u_token = login_res.json()["token"]
    u_headers = {"Authorization": f"Bearer {u_token}"}

    # 4. Call /api/breakfast/today
    bms_res = client.get("/api/breakfast/today", headers=u_headers)
    print("BMS /api/breakfast/today response:", bms_res.status_code, bms_res.text[:200])

    # 5. Call /api/v1/breakfast/today
    bms_v1_res = client.get("/api/v1/breakfast/today", headers=u_headers)
    print("BMS /api/v1/breakfast/today response:", bms_v1_res.status_code, bms_v1_res.text[:200])
