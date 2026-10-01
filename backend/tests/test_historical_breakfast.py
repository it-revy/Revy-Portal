import pytest

def test_create_historical_record_with_null_employee(client, breakfast_admin_headers):
    # 1. Reject CURRENT record without employee_id
    res_bad = client.post(
        "/api/v1/breakfast/records",
        json={
            "date": "2026-06-20",
            "employeeId": None,
            "recordType": "CURRENT",
            "snack": "Poha"
        },
        headers=breakfast_admin_headers
    )
    assert res_bad.status_code == 400, f"Expected 400 for CURRENT without employee, got {res_bad.status_code}: {res_bad.text}"

    # 2. Accept HISTORICAL record with employee_id = None and string quantities
    payload = {
        "date": "2026-06-20",
        "employeeId": None,
        "recordType": "HISTORICAL",
        "snack": "Dalwada",
        "snackQuantity": "400GM",
        "snackCost": 80.0,
        "fruit": "Mango",
        "fruitQuantity": "1kg",
        "fruitCost": 60.0,
        "totalCost": 140.0,
        "paidBy": "Faiz",
        "paymentType": "GPay",
        "source": "HISTORICAL_IMPORT",
        "sourceId": "HIST-TEST-2026-06-20-001"
    }

    res = client.post(
        "/api/v1/breakfast/records",
        json=payload,
        headers=breakfast_admin_headers
    )
    assert res.status_code == 201, f"Failed to create historical record: {res.text}"
    data = res.json()["record"]

    assert data["employeeId"] is None
    assert data["recordType"] == "HISTORICAL"
    assert data["isHistorical"] is True
    assert data["employeeName"] == "Not Recorded"
    assert data["snack"] == "Dalwada"
    assert data["snackQuantity"] == "400GM"
    assert data["snackCost"] == 80.0
    assert data["fruit"] == "Mango"
    assert data["fruitQuantity"] == "1kg"
    assert data["fruitCost"] == 60.0
    assert data["totalCost"] == 140.0
    assert data["paidBy"] == "Faiz"
    assert data["paymentType"] == "GPay"
    assert data["sourceId"] == "HIST-TEST-2026-06-20-001"

    # Clean up created record
    rec_id = data["recordId"]
    client.delete(f"/api/v1/breakfast/records/{rec_id}", headers=breakfast_admin_headers)

def test_update_historical_record(client, breakfast_admin_headers):
    # Create record
    res_create = client.post(
        "/api/v1/breakfast/records",
        json={
            "date": "2026-06-21",
            "employeeId": None,
            "recordType": "HISTORICAL",
            "snack": "Poha",
            "snackQuantity": "500GM",
            "snackCost": 100.0,
            "fruit": "Banana",
            "fruitQuantity": "12pcs",
            "fruitCost": 60.0,
            "totalCost": 160.0,
            "paidBy": "Faiz",
            "paymentType": "Cash",
            "sourceId": "HIST-TEST-2026-06-21-001"
        },
        headers=breakfast_admin_headers
    )
    assert res_create.status_code == 201
    rec = res_create.json()["record"]
    rec_id = rec["recordId"]

    # Update record
    res_update = client.put(
        f"/api/v1/breakfast/records/{rec_id}",
        json={
            "snack": "Thepla",
            "snackQuantity": "10pkt",
            "snackCost": 120.0,
            "fruit": "Apple",
            "fruitQuantity": "1kg",
            "fruitCost": 80.0,
            "totalCost": 200.0,
            "paidBy": "Office Cash",
            "paymentType": "Direct Cash"
        },
        headers=breakfast_admin_headers
    )
    assert res_update.status_code == 200, f"Update failed: {res_update.text}"
    updated = res_update.json()["record"]

    assert updated["employeeId"] is None
    assert updated["employeeName"] == "Not Recorded"
    assert updated["snack"] == "Thepla"
    assert updated["snackQuantity"] == "10pkt"
    assert updated["snackCost"] == 120.0
    assert updated["fruit"] == "Apple"
    assert updated["fruitQuantity"] == "1kg"
    assert updated["fruitCost"] == 80.0
    assert updated["totalCost"] == 200.0
    assert updated["paidBy"] == "Office Cash"
    assert updated["paymentType"] == "Direct Cash"

    # Clean up
    client.delete(f"/api/v1/breakfast/records/{rec_id}", headers=breakfast_admin_headers)

def test_batch_historical_seed_and_idempotency(client, breakfast_admin_headers):
    # Clean up any leftover records from prior test runs
    client.delete("/api/v1/breakfast/records/HIST-TEST-2026-07-01-001", headers=breakfast_admin_headers)
    client.delete("/api/v1/breakfast/records/HIST-TEST-2026-07-01-002", headers=breakfast_admin_headers)

    batch_payload = {
        "records": [
            {
                "date": "2026-07-01",
                "employeeId": None,
                "recordType": "HISTORICAL",
                "snack": "Samosa",
                "snackQuantity": "20pcs",
                "snackCost": 200.0,
                "fruit": "Watermelon",
                "fruitQuantity": "2kg",
                "fruitCost": 100.0,
                "totalCost": 300.0,
                "paidBy": "Faiz",
                "paymentType": "GPay",
                "source": "HISTORICAL_IMPORT",
                "sourceId": "HIST-TEST-2026-07-01-001"
            },
            {
                "date": "2026-07-01",
                "employeeId": None,
                "recordType": "HISTORICAL",
                "snack": "Kachori",
                "snackQuantity": "10pcs",
                "snackCost": 150.0,
                "totalCost": 150.0,
                "paidBy": "Faiz",
                "paymentType": "GPay",
                "source": "HISTORICAL_IMPORT",
                "sourceId": "HIST-TEST-2026-07-01-002"
            }
        ]
    }

    # 1. Initial batch insert
    res1 = client.post("/api/v1/breakfast/records/batch", json=batch_payload, headers=breakfast_admin_headers)
    assert res1.status_code == 200, f"Batch insert failed: {res1.text}"
    data1 = res1.json()
    summary1 = data1["summary"]
    assert summary1["inserted"] == 2
    assert summary1["skipped"] == 0
    assert summary1["errors"] == 0

    # 2. Re-run identical batch - must be skipped idempotently
    res2 = client.post("/api/v1/breakfast/records/batch", json=batch_payload, headers=breakfast_admin_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    summary2 = data2["summary"]
    assert summary2["inserted"] == 0
    assert summary2["skipped"] == 2

    # 3. Verify orders endpoint lists them
    res_orders = client.get("/api/v1/breakfast/orders?type=HISTORICAL", headers=breakfast_admin_headers)
    assert res_orders.status_code == 200
    orders = res_orders.json()["orders"]
    hist_orders = [o for o in orders if o["orderType"] == "HISTORICAL"]
    assert len(hist_orders) >= 2

    # Clean up test records
    client.delete("/api/v1/breakfast/records/HIST-TEST-2026-07-01-001", headers=breakfast_admin_headers)
    client.delete("/api/v1/breakfast/records/HIST-TEST-2026-07-01-002", headers=breakfast_admin_headers)

def test_historical_records_excluded_from_employee_consumption(client, breakfast_admin_headers, auth_headers):
    # Insert a historical record
    res = client.post(
        "/api/v1/breakfast/records",
        json={
            "date": "2026-06-25",
            "employeeId": None,
            "recordType": "HISTORICAL",
            "snack": "Idli Sambhar",
            "snackQuantity": "4plt",
            "snackCost": 120.0,
            "totalCost": 120.0,
            "paidBy": "Faiz",
            "paymentType": "GPay",
            "sourceId": "HIST-TEST-2026-06-25-001"
        },
        headers=breakfast_admin_headers
    )
    assert res.status_code == 201

    # Check monthly employee report
    res_rep = client.get("/api/v1/reports/monthly?year=2026&month=06&department=ALL", headers=auth_headers)
    assert res_rep.status_code == 200
    rep_data = res_rep.json()

    # Individual employees must NOT have their taken count incremented by null employee records
    for emp in rep_data.get("employeeReport", []):
        # Verify employeeId is not None/null
        assert emp["employeeId"] is not None
        assert emp["employeeId"] != "Not Recorded"

    # Monthly financial summary includes historical expenses in totalSpent
    monthly_summary = rep_data.get("monthlySummary", [])
    june_row = next((m for m in monthly_summary if m.get("monthNumber") == 6 or m.get("yearMonth") == "2026-06"), None)
    if june_row:
        assert june_row["historicalSpent"] >= 120.0

    # Clean up
    client.delete("/api/v1/breakfast/records/HIST-TEST-2026-06-25-001", headers=breakfast_admin_headers)
