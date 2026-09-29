import pytest

def test_daily_entry_and_additional_order_workflow(client, breakfast_admin_headers):
    target_date = "2026-10-15"

    # 1. Fetch daily entry data
    res_get_de = client.get(f"/api/v1/breakfast/daily-entry?date={target_date}", headers=breakfast_admin_headers)
    assert res_get_de.status_code == 200
    assert "applicableEmployees" in res_get_de.json()

    # 1.5 Provide funds into ledger so daily entry expense is covered
    res_fund = client.post(
        "/api/v1/breakfast/money/receive",
        json={"amount": 500.0, "source": "Finance Advance", "note": "Funds for daily entry"},
        headers=breakfast_admin_headers
    )
    assert res_fund.status_code == 200

    # 2. Save Daily Entry
    res_save_de = client.post(
        "/api/v1/breakfast/daily-entry",
        json={
            "businessDate": target_date,
            "breakfastItems": [
                {"name": "Poha", "unitPrice": 30.0, "quantity": 5}
            ],
            "commonItems": [
                {"name": "Milk Packet", "unitPrice": 40.0, "quantity": 1}
            ]
        },
        headers=breakfast_admin_headers
    )
    assert res_save_de.status_code == 200
    entry = res_save_de.json()["entry"]
    assert entry["totalCost"] == (30.0 * 5) + 40.0

    # 3. Create Additional Order
    res_add_ord = client.post(
        "/api/v1/breakfast/additional-orders",
        json={
            "businessDate": target_date,
            "orderTitle": "Evening Samosa",
            "breakfastItems": [
                {"name": "Samosa", "unitPrice": 15.0, "quantity": 10}
            ]
        },
        headers=breakfast_admin_headers
    )
    assert res_add_ord.status_code == 200
    add_order = res_add_ord.json()["order"]
    assert add_order["totalCost"] == 150.0

    # 4. Check unified All Orders endpoint
    res_all = client.get(f"/api/v1/breakfast/orders?startDate={target_date}&endDate={target_date}", headers=breakfast_admin_headers)
    assert res_all.status_code == 200
    orders_data = res_all.json()
    assert orders_data["summary"]["totalOrders"] >= 2
    assert orders_data["summary"]["dailyCount"] >= 1
    assert orders_data["summary"]["additionalCount"] >= 1

    # 5. Delete Additional Order (reverses expense into ledger)
    res_del = client.delete(f"/api/v1/breakfast/additional-orders/{add_order['orderId']}", headers=breakfast_admin_headers)
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

def test_purchase_orders_workflow(client, breakfast_admin_headers):
    target_date = "2026-10-16"

    # Create purchase order with individual items
    res = client.post(
        "/api/v1/orders",
        json={
            "businessDate": target_date,
            "vendorName": "Bansiwala Caterers",
            "notes": "Morning catering order",
            "items": [
                {"orderType": "INDIVIDUAL", "employeeId": "EMP-0004", "itemName": "Idli Vada", "price": 45.0, "quantity": 1},
                {"orderType": "COMMON", "itemName": "Tea Pot", "price": 100.0, "quantity": 1}
            ]
        },
        headers=breakfast_admin_headers
    )
    assert res.status_code == 200
    ord_id = res.json()["order"]["orderId"]

    # Get orders by date
    res_get = client.get(f"/api/v1/orders?date={target_date}", headers=breakfast_admin_headers)
    assert res_get.status_code == 200
    assert res_get.json()["summary"]["grandTotal"] == 145.0

    # Delete order
    res_del = client.delete(f"/api/v1/orders/{ord_id}", headers=breakfast_admin_headers)
    assert res_del.status_code == 200
