import pytest

def test_holidays_crud(client, auth_headers):
    # 1. Create public holiday
    res_create = client.post(
        "/api/v1/holidays",
        json={"date": "2026-12-25", "name": "Christmas Day"},
        headers=auth_headers
    )
    assert res_create.status_code == 200
    hol_id = res_create.json()["holiday"]["holidayId"]

    # 2. List holidays
    res_list = client.get("/api/v1/holidays", headers=auth_headers)
    assert res_list.status_code == 200
    assert any(h["date"] == "2026-12-25" for h in res_list.json()["holidays"])

    # 3. Delete holiday
    res_del = client.delete(f"/api/v1/holidays/{hol_id}", headers=auth_headers)
    assert res_del.status_code == 200

def test_settings_crud(client, auth_headers):
    # 1. Get settings
    res_get = client.get("/api/v1/settings", headers=auth_headers)
    assert res_get.status_code == 200
    assert "cutoffTime" in res_get.json()["settings"]

    # 2. Update settings
    res_upd = client.put(
        "/api/v1/settings",
        json={"cutoffTime": "11:30"},
        headers=auth_headers
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["settings"]["cutoffTime"] == "11:30"

    # Revert back
    client.put("/api/v1/settings", json={"cutoffTime": "12:00"}, headers=auth_headers)

def test_reports_endpoints(client, auth_headers):
    # 1. Available years
    res_years = client.get("/api/v1/reports/years", headers=auth_headers)
    assert res_years.status_code == 200
    assert "years" in res_years.json()

    # 2. Monthly report data
    res_monthly = client.get("/api/v1/reports/monthly", headers=auth_headers)
    assert res_monthly.status_code == 200
    m_data = res_monthly.json()
    assert "monthlySummary" in m_data
    assert "employeeReport" in m_data
    assert "yearlyTotal" in m_data

    # 3. Export Excel binary stream
    res_excel = client.get("/api/v1/reports/export-excel", headers=auth_headers)
    assert res_excel.status_code == 200
    assert res_excel.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(res_excel.content) > 1000

    # 4. CEO Report
    res_ceo = client.get("/api/v1/reports/ceo", headers=auth_headers)
    assert res_ceo.status_code == 200
    ceo_data = res_ceo.json()
    assert "executiveSummary" in ceo_data
    assert "dailyTrend" in ceo_data

def test_audit_logs(client, auth_headers):
    res = client.get("/api/v1/audit-logs", headers=auth_headers)
    assert res.status_code == 200
    logs = res.json()["logs"]
    assert len(logs) > 0
