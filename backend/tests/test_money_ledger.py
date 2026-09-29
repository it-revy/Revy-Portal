import pytest

def test_full_money_fund_and_expense_lifecycle(client, breakfast_admin_headers, finance_headers):
    # 1. Check initial balance
    res_bal = client.get("/api/v1/breakfast/money/balance", headers=breakfast_admin_headers)
    assert res_bal.status_code == 200
    metrics = res_bal.json()["metrics"]
    initial_bal = metrics["currentBalance"]
    fund_limit = metrics["fundLimit"]

    if initial_bal > 1000.0:
        excess = initial_bal - 500.0
        client.post(
            "/api/v1/breakfast/money/expense",
            json={"amount": excess, "description": "Reset test balance", "expenseCategory": "OTHER_BREAKFAST_EXPENSE"},
            headers=breakfast_admin_headers
        )
        res_bal = client.get("/api/v1/breakfast/money/balance", headers=breakfast_admin_headers)
        initial_bal = res_bal.json()["metrics"]["currentBalance"]

    requested_amt = 500.0

    # 2. Breakfast Admin creates a fund request
    res_req = client.post(
        "/api/v1/breakfast/money/requests",
        json={"requestedAmount": requested_amt, "reason": "Replenish breakfast pantry"},
        headers=breakfast_admin_headers
    )
    assert res_req.status_code == 200
    req_id = res_req.json()["fundRequest"]["requestId"]

    # 3. Finance Manager approves fund request
    res_app = client.put(
        f"/api/v1/breakfast/money/requests/{req_id}/approve",
        json={"approvedAmount": requested_amt},
        headers=finance_headers
    )
    assert res_app.status_code == 200
    assert res_app.json()["fundRequest"]["status"] == "APPROVED"

    # 4. Finance Manager provides the money
    res_prov = client.put(
        f"/api/v1/breakfast/money/requests/{req_id}/provide",
        json={"providedAmount": requested_amt, "reference": "BANK-TRF-001", "note": "Transferred cash"},
        headers=finance_headers
    )
    assert res_prov.status_code == 200
    assert res_prov.json()["fundRequest"]["status"] == "RECEIPT_PENDING"

    # 5. Breakfast Admin verifies receipt
    res_ver = client.put(
        f"/api/v1/breakfast/money/requests/{req_id}/verify",
        json={"verifiedAmount": requested_amt, "differenceNote": ""},
        headers=breakfast_admin_headers
    )
    assert res_ver.status_code == 200
    assert res_ver.json()["newBalance"] == initial_bal + requested_amt

    # 6. Record manual expense
    res_exp = client.post(
        "/api/v1/breakfast/money/expense",
        json={
            "amount": 200.0,
            "description": "Biscuits and tea bags",
            "expenseCategory": "OTHER_BREAKFAST_EXPENSE"
        },
        headers=breakfast_admin_headers
    )
    assert res_exp.status_code == 200
    assert res_exp.json()["newBalance"] == initial_bal + requested_amt - 200.0

    # 7. Statements reflect transactions
    res_stmt = client.get("/api/v1/breakfast/money/statement/daily", headers=breakfast_admin_headers)
    assert res_stmt.status_code == 200
    assert res_stmt.json()["statement"]["moneyReceived"] >= requested_amt
    assert res_stmt.json()["statement"]["expenses"] >= 200.0
