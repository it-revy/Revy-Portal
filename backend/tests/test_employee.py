import pytest

def test_list_employees(client, auth_headers):
    res = client.get("/api/v1/employees", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["count"] >= 9
    assert any(e["username"] == "vasudev" for e in data["employees"])

def test_create_and_update_employee(client, auth_headers):
    import uuid
    uid = uuid.uuid4().hex[:6]
    # 1. Create employee
    new_emp_data = {
        "username": f"test_emp_{uid}",
        "name": "Test Employee",
        "email": f"test_emp_{uid}@company.com",
        "password": "Password123!",
        "department": "Engineering",
        "designation": "Junior Engineer",
        "roles": ["EMPLOYEE"]
    }
    res = client.post("/api/v1/employees", json=new_emp_data, headers=auth_headers)
    assert res.status_code == 200
    emp_id = res.json()["employee"]["employeeId"]

    # 2. Get details
    res_get = client.get(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["employee"]["name"] == "Test Employee"

    # 3. Update employee
    res_upd = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"designation": "Senior Engineer", "phone": "1234567890"},
        headers=auth_headers
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["employee"]["designation"] == "Senior Engineer"

    # 4. Soft deactivate
    res_deact = client.delete(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert res_deact.status_code == 200
    assert res_deact.json()["employee"]["status"] == "inactive"
