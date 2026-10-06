import pytest

def test_rbac_matrix_director_analytics_and_ceo_dashboard(client, director_analytics_headers, ceo_headers, finance_headers, employee_headers):
    # 1. Director Analytics role CAN access /reports/director-analytics
    res_dir = client.get("/api/v1/reports/director-analytics", headers=director_analytics_headers)
    assert res_dir.status_code == 200
    assert res_dir.json()["success"] is True
    assert "executiveSummary" in res_dir.json()

    # Director Analytics role CANNOT access /reports/ceo (CEO Dashboard is restricted to CEO)
    res_dir_ceo = client.get("/api/v1/reports/ceo", headers=director_analytics_headers)
    assert res_dir_ceo.status_code == 403

    # 2. CEO role CAN access /reports/ceo (CEO Dashboard)
    res_ceo = client.get("/api/v1/reports/ceo", headers=ceo_headers)
    assert res_ceo.status_code == 200
    assert res_ceo.json()["success"] is True

    # CEO role CANNOT access Director Analytics dashboard API (/reports/director-analytics)
    res_ceo_dir = client.get("/api/v1/reports/director-analytics", headers=ceo_headers)
    assert res_ceo_dir.status_code == 403
    assert "PERMISSION_DENIED" in str(res_ceo_dir.json())

    # 3. Finance Manager CANNOT access Director Analytics or CEO Dashboard
    res_fin_dir = client.get("/api/v1/reports/director-analytics", headers=finance_headers)
    assert res_fin_dir.status_code == 403
    res_fin_ceo = client.get("/api/v1/reports/ceo", headers=finance_headers)
    assert res_fin_ceo.status_code == 403

    # 4. Standard Employee CANNOT access Director Analytics or CEO Dashboard
    res_emp_dir = client.get("/api/v1/reports/director-analytics", headers=employee_headers)
    assert res_emp_dir.status_code == 403
    res_emp_ceo = client.get("/api/v1/reports/ceo", headers=employee_headers)
    assert res_emp_ceo.status_code == 403


def test_rbac_matrix_ceo_can_view_all_orders(client, ceo_headers, director_analytics_headers, finance_headers, employee_headers):
    # 1. CEO CAN view all breakfast orders
    res_orders = client.get("/api/v1/breakfast/orders", headers=ceo_headers)
    assert res_orders.status_code == 200
    data = res_orders.json()
    assert data["success"] is True
    assert "orders" in data
    assert "summary" in data

    # 2. CEO CAN view additional orders
    res_add = client.get("/api/v1/breakfast/additional-orders", headers=ceo_headers)
    assert res_add.status_code == 200
    assert res_add.json()["success"] is True

    # 3. CEO CAN view orders by date
    res_date = client.get("/api/v1/orders", headers=ceo_headers)
    assert res_date.status_code == 200
    assert res_date.json()["success"] is True

    # 4. CEO CAN view company records
    res_rec = client.get("/api/v1/breakfast/records", headers=ceo_headers)
    assert res_rec.status_code == 200
    assert res_rec.json()["success"] is True

    # 5. Director Analytics CANNOT access all orders unless explicitly permitted
    res_dir_orders = client.get("/api/v1/breakfast/orders", headers=director_analytics_headers)
    assert res_dir_orders.status_code == 403

    # 6. Finance Manager CANNOT access all orders
    res_fin_orders = client.get("/api/v1/breakfast/orders", headers=finance_headers)
    assert res_fin_orders.status_code == 403

    # 7. Employee CANNOT access all orders
    res_emp_orders = client.get("/api/v1/breakfast/orders", headers=employee_headers)
    assert res_emp_orders.status_code == 403


def test_rbac_matrix_finance_manager_reports_access(client, finance_headers, ceo_headers):
    # 1. Finance Manager CAN view years
    res_years = client.get("/api/v1/reports/years", headers=finance_headers)
    assert res_years.status_code == 200
    assert res_years.json()["success"] is True

    # 2. Finance Manager CAN view monthly reports
    res_monthly = client.get("/api/v1/reports/monthly", headers=finance_headers)
    assert res_monthly.status_code == 200
    assert res_monthly.json()["success"] is True

    # 3. Finance Manager CAN download reports (export Excel)
    res_export = client.get("/api/v1/reports/export-excel", headers=finance_headers)
    assert res_export.status_code == 200
    assert "spreadsheetml" in res_export.headers.get("content-type", "")

    # 4. CEO keeps existing report permissions
    res_ceo_monthly = client.get("/api/v1/reports/monthly", headers=ceo_headers)
    assert res_ceo_monthly.status_code == 200
    res_ceo_export = client.get("/api/v1/reports/export-excel", headers=ceo_headers)
    assert res_ceo_export.status_code == 200
