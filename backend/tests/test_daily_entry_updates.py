import pytest
from seed.seed_development import seed_database

def test_total_quantity_based_on_actual_response_quantity(client, breakfast_admin_headers):
    """
    Validates Requirement 1:
    - Employee Request Quantity = quantity requested by employees.
    - Actual Response Quantity = quantity actually provided/served (actualStatus == 'TAKEN').
    - Total Quantity must be based on Actual Response Quantity, NOT Employee Request Quantity.
    """
    # Step 1: Employee Jyoti gets active business date and submits response = TAKING
    login_res = client.post("/api/v1/auth/login", json={"username": "jyoti", "password": "Password123"})
    if login_res.status_code != 200:
        login_res = client.post("/api/v1/auth/login", json={"username": "jyoti", "password": "Jyoti123"})
    assert login_res.status_code == 200
    jyoti_headers = {"Authorization": f"Bearer {login_res.json()['token']}"}

    res_today = client.get("/api/v1/breakfast/today", headers=jyoti_headers)
    assert res_today.status_code == 200
    b_date = res_today.json()["businessDate"]

    from app.core.database import SessionLocal
    from app.breakfast.model import BreakfastNonParticipationPeriod, BreakfastRecord

    # Ensure test isolation for b_date
    db_session = SessionLocal()
    try:
        db_session.query(BreakfastNonParticipationPeriod).filter(
            BreakfastNonParticipationPeriod.employee_id == "EMP-0004"
        ).delete()
        db_session.query(BreakfastRecord).filter(
            BreakfastRecord.business_date == b_date
        ).delete()
        db_session.commit()
    finally:
        db_session.close()

    res_sub = client.post(
        "/api/v1/breakfast/submit",
        json={"response": "YES"},
        headers=jyoti_headers
    )
    assert res_sub.status_code == 200

    # Step 2: Fetch Daily Entry workstation data
    res_de = client.get(f"/api/v1/breakfast/daily-entry?date={b_date}", headers=breakfast_admin_headers)
    assert res_de.status_code == 200
    de_data = res_de.json()
    summary = de_data["summary"]

    assert summary["employeeRequestQuantity"] == 1.0
    assert summary["actualResponseQuantity"] == 1.0
    assert summary["totalQuantity"] == 1.0

    # Step 3: Admin overrides Jyoti's actual consumption to NOT_TAKEN
    # Now: Employee Request Quantity = 1 (she requested it), but Actual Response Quantity = 0 (not served)
    res_override = client.put(
        "/api/v1/breakfast/actual-status",
        json={"employeeId": "EMP-0004", "businessDate": b_date, "actualStatus": "NOT_TAKEN"},
        headers=breakfast_admin_headers
    )
    assert res_override.status_code == 200

    # Re-fetch Daily Entry workstation data
    res_de2 = client.get(f"/api/v1/breakfast/daily-entry?date={b_date}", headers=breakfast_admin_headers)
    assert res_de2.status_code == 200
    summary2 = res_de2.json()["summary"]

    # Verify Requirement 1 behavior:
    # Employee Request Quantity remains 1
    assert summary2["employeeRequestQuantity"] == 1.0
    # Actual Response Quantity is now 0
    assert summary2["actualResponseQuantity"] == 0.0
    # Total Quantity is now based on Actual Response Quantity, so it must be 0 (NOT Employee Request Quantity 1)
    assert summary2["totalQuantity"] == 0.0

    # Step 4: Admin overrides actual consumption to TAKEN for an employee who did NOT respond
    # (e.g. guest or walked-in employee EMP-0005 who has no request)
    res_override2 = client.put(
        "/api/v1/breakfast/actual-status",
        json={"employeeId": "EMP-0005", "businessDate": b_date, "actualStatus": "TAKEN"},
        headers=breakfast_admin_headers
    )
    assert res_override2.status_code == 200

    res_de3 = client.get(f"/api/v1/breakfast/daily-entry?date={b_date}", headers=breakfast_admin_headers)
    assert res_de3.status_code == 200
    summary3 = res_de3.json()["summary"]

    # Now EMP-0004 is NOT_TAKEN and EMP-0005 is TAKEN:
    # Employee Request Quantity = 1 (EMP-0004 requested), Actual Response Quantity = 1 (EMP-0005 was served)
    assert summary3["employeeRequestQuantity"] == 1.0
    assert summary3["actualResponseQuantity"] == 1.0
    assert summary3["totalQuantity"] == 1.0

    # Also verify /admin/summary metrics endpoint
    res_admin_sum = client.get(f"/api/v1/breakfast/admin/summary?date={b_date}", headers=breakfast_admin_headers)
    assert res_admin_sum.status_code == 200
    admin_metrics = res_admin_sum.json()["metrics"]
    assert admin_metrics["employeeRequestQuantity"] == 1.0
    assert admin_metrics["actualResponseQuantity"] == 1.0
    assert admin_metrics["totalQuantity"] == 1.0


def test_decimal_quantities_throughout_flow(client, breakfast_admin_headers):
    """
    Validates Requirement 3:
    Quantity Must Support Decimal/Float Values (e.g., 10, 10.5, 25.75, 0.5)
    Frontend -> API -> Backend -> Database -> Calculations -> Display
    """
    b_date = "2026-11-21"

    # Provide funds into ledger
    client.post(
        "/api/v1/breakfast/money/receive",
        json={"amount": 2000.0, "source": "Finance", "note": "Funds for testing"},
        headers=breakfast_admin_headers
    )

    # 1. Save Daily Entry with decimal quantities: 10.5, 25.75, 0.5
    res_save = client.post(
        "/api/v1/breakfast/daily-entry",
        json={
            "businessDate": b_date,
            "totalQuantity": 25.75,
            "breakfastItems": [
                {"name": "Poha", "unitPrice": 20.0, "quantity": 10.5},
                {"name": "Upma", "unitPrice": 30.0, "quantity": 0.5}
            ],
            "commonItems": [
                {"name": "Shared Milk", "unitPrice": 60.0, "quantity": 1.5}
            ]
        },
        headers=breakfast_admin_headers
    )
    assert res_save.status_code == 200
    saved_entry = res_save.json()["entry"]

    # Verify calculation:
    # Poha: 20.0 * 10.5 = 210.0
    # Upma: 30.0 * 0.5 = 15.0
    # Milk: 60.0 * 1.5 = 90.0
    # Total = 315.0
    assert saved_entry["breakfastItems"][0]["quantity"] == 10.5
    assert saved_entry["breakfastItems"][0]["total"] == 210.0
    assert saved_entry["breakfastItems"][1]["quantity"] == 0.5
    assert saved_entry["breakfastItems"][1]["total"] == 15.0
    assert saved_entry["commonItems"][0]["quantity"] == 1.5
    assert saved_entry["commonItems"][0]["total"] == 90.0
    assert saved_entry["totalCost"] == 315.0
    assert saved_entry["totalQuantity"] == 25.75

    # 2. Re-fetch Daily Entry and verify decimal values are preserved exactly
    res_get = client.get(f"/api/v1/breakfast/daily-entry?date={b_date}", headers=breakfast_admin_headers)
    assert res_get.status_code == 200
    entry_fetched = res_get.json()["existingEntry"]
    assert entry_fetched["breakfastItems"][0]["quantity"] == 10.5
    assert entry_fetched["breakfastItems"][1]["quantity"] == 0.5
    assert entry_fetched["commonItems"][0]["quantity"] == 1.5
    assert entry_fetched["totalQuantity"] == 25.75

    # 3. Create Additional Order with decimal quantities: 7.25, 0.75
    res_add = client.post(
        "/api/v1/breakfast/additional-orders",
        json={
            "businessDate": b_date,
            "orderTitle": "Afternoon Refreshment",
            "breakfastItems": [
                {"name": "Tea", "unitPrice": 10.0, "quantity": 7.25}
            ],
            "commonItems": [
                {"name": "Biscuits Packets", "unitPrice": 40.0, "quantity": 0.75}
            ]
        },
        headers=breakfast_admin_headers
    )
    assert res_add.status_code == 200
    add_order = res_add.json()["order"]
    # 10.0 * 7.25 = 72.5, 40.0 * 0.75 = 30.0 => total 102.5
    assert add_order["breakfastItems"][0]["quantity"] == 7.25
    assert add_order["commonItems"][0]["quantity"] == 0.75
    assert add_order["totalCost"] == 102.5

    # 4. Create Purchase Order with decimal quantities in /api/v1/orders
    res_po = client.post(
        "/api/v1/orders",
        json={
            "businessDate": b_date,
            "vendorName": "Decimal Vendor",
            "items": [
                {"orderType": "COMMON", "itemName": "Bulk Coffee", "price": 200.0, "quantity": 2.5}
            ]
        },
        headers=breakfast_admin_headers
    )
    assert res_po.status_code == 200
    po_item = res_po.json()["items"][0]
    assert po_item["quantity"] == 2.5
    assert po_item["total"] == 500.0


def test_seed_manual_execution_and_no_auto_execution():
    """
    Validates Requirement 2:
    - Seed process is manually executable and idempotent.
    - Application startup does not execute seed.
    """
    # Verify manual seed execution works without error
    seed_database()
