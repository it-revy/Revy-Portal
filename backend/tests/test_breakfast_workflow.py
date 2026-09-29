import pytest

def test_full_breakfast_response_workflow(client, employee_headers, breakfast_admin_headers):
    # 1. Get today status as normal employee
    res_today = client.get("/api/v1/breakfast/today", headers=employee_headers)
    assert res_today.status_code == 200
    today_data = res_today.json()
    assert today_data["success"] is True
    b_date = today_data["businessDate"]

    # 2. Submit daily response YES (TAKING)
    res_submit = client.post(
        "/api/v1/breakfast/submit",
        json={"response": "YES"},
        headers=employee_headers
    )
    assert res_submit.status_code == 200
    assert res_submit.json()["record"]["response"] == "YES"

    # 3. Change to NO with reason
    res_no = client.post(
        "/api/v1/breakfast/submit",
        json={"response": "NO", "reasonCode": "FASTING"},
        headers=employee_headers
    )
    assert res_no.status_code == 200
    assert res_no.json()["record"]["response"] == "NO"
    assert res_no.json()["record"]["reasonCode"] == "FASTING"

    # 4. Check admin summary reflects the response
    res_summary = client.get(f"/api/v1/breakfast/admin/summary?date={b_date}", headers=breakfast_admin_headers)
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert summary_data["metrics"]["notTakingBreakfastCount"] >= 1

    # 5. Check admin daily records
    res_records = client.get(f"/api/v1/breakfast/admin/records?date={b_date}", headers=breakfast_admin_headers)
    assert res_records.status_code == 200
    records_list = res_records.json()["allList"]
    jyoti_rec = next((r for r in records_list if r["username"] == "jyoti"), None)
    assert jyoti_rec is not None
    assert jyoti_rec["employeeResponse"] == "NOT_TAKING"

    # 6. Admin overrides actual consumption status
    res_override = client.put(
        "/api/v1/breakfast/actual-status",
        json={"employeeId": jyoti_rec["employeeId"], "businessDate": b_date, "actualStatus": "TAKEN"},
        headers=breakfast_admin_headers
    )
    assert res_override.status_code == 200
    assert res_override.json()["record"]["actualStatus"] == "TAKEN"
    assert res_override.json()["record"]["actualStatusSource"] == "ADMIN_OVERRIDE"

def test_multi_day_absence(client, employee_headers):
    res = client.post(
        "/api/v1/breakfast/multi-day-absence",
        json={
            "fromDate": "2026-10-01",
            "toDate": "2026-10-03",
            "reasonCode": "ON_LEAVE"
        },
        headers=employee_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["datesCount"] == 3

    # Check history
    res_hist = client.get("/api/v1/breakfast/history", headers=employee_headers)
    assert res_hist.status_code == 200
    assert any(p["reasonCode"] == "ON_LEAVE" for p in res_hist.json()["periods"])
