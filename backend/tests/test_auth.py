import pytest

def test_login_success(client):
    res = client.post("/api/v1/auth/login", json={"username": "vasudev", "password": "Vasudev123"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["username"] == "vasudev"
    assert "IT_ADMIN" in data["user"]["roles"]

def test_login_invalid_password(client):
    res = client.post("/api/v1/auth/login", json={"username": "vasudev", "password": "WrongPassword"})
    assert res.status_code == 401
    assert res.json()["success"] is False

def test_login_nonexistent_user(client):
    res = client.post("/api/v1/auth/login", json={"username": "unknown_user", "password": "Password123"})
    assert res.status_code == 401
    assert res.json()["success"] is False

def test_get_me(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["user"]["username"] == "vasudev"
    assert "permissions" in data["user"]

def test_change_password(client, auth_headers):
    # Change password
    res = client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "Vasudev123", "newPassword": "VasudevNew123", "confirmPassword": "VasudevNew123"},
        headers=auth_headers
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Revert password back for test consistency
    res2 = client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "VasudevNew123", "newPassword": "Vasudev123", "confirmPassword": "Vasudev123"},
        headers=auth_headers
    )
    assert res2.status_code == 200
