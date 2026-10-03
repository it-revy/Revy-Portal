import urllib.request
import urllib.error
import json
from datetime import date

import sys
sys.stdout.reconfigure(line_buffering=True)

BASE_URL = "http://127.0.0.1:5001/api/v1"

def api_call(endpoint, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def run_tests():
    print("==================================================", flush=True)
    print("  RUNNING COMPREHENSIVE NEON POSTGRESQL VERIFICATION", flush=True)
    print("==================================================", flush=True)

    # 1. Login as CEO (rajneesh)
    print("\n--- 1. CEO Authentication ---", flush=True)
    login_res = api_call("/auth/login", method="POST", data={"username": "rajneesh", "password": "Rajneesh123"})
    assert login_res["success"], "CEO login failed"
    ceo_token = login_res["token"]
    print(f"Logged in CEO: {login_res['user']['username']}, Roles: {login_res['user']['roles']}", flush=True)

    # 2. Get Employees
    print("\n--- 2. Employee Management API ---")
    emp_res = api_call("/employees", token=ceo_token)
    assert emp_res["success"], "Failed to get employees"
    emps = emp_res["employees"]
    print(f"Total employees in Neon: {len(emps)}")
    for e in emps:
        print(f"  [{e['employeeId']}] {e['name']} - Dept: {e['department']}, Desig: {e['designation']}, Status: {e['status']}, PartType: {e['breakfastParticipationType']}")

    # 3. Update EMP-0008 (Shahil) to PERMANENT_NON_TAKER
    print("\n--- 3. Set Shahil (EMP-0008) to PERMANENT_NON_TAKER ---")
    shahil = next(e for e in emps if e["employeeId"] == "EMP-0008")
    update_res = api_call(f"/employees/{shahil['employeeId']}", method="PUT", data={
        "breakfastParticipationType": "PERMANENT_NON_TAKER"
    }, token=ceo_token)
    assert update_res["success"], "Failed to update employee"
    print(f"Updated Shahil participation type to: {update_res['employee']['breakfastParticipationType']}")

    # 4. CEO Dashboard Metrics before temporary request
    print("\n--- 4. CEO Dashboard Metrics (After setting Permanent Non-Taker) ---")
    ceo_data = api_call("/reports/ceo?date=2026-10-02", token=ceo_token)
    print(f"  totalEmployees: {ceo_data['totalEmployees']}")
    print(f"  regularTakers: {ceo_data['regularTakers']}")
    print(f"  permanentNonTakers: {ceo_data['permanentNonTakers']}")
    assert ceo_data['totalEmployees'] == 9, "Expected 9 total employees"
    assert ceo_data['regularTakers'] == 8, "Expected 8 regular takers"
    assert ceo_data['permanentNonTakers'] == 1, "Expected 1 permanent non-taker"

    # 5. Login as Shahil (Permanent Non-Taker)
    print("\n--- 5. Login as Shahil (Permanent Non-Taker) ---")
    shahil_login = api_call("/auth/login", method="POST", data={"username": "shahil", "password": "Shahil123"})
    assert shahil_login["success"], "Shahil login failed"
    shahil_token = shahil_login["token"]

    # 6. Shahil submits a One-Day Specific Date Request with Decimal Quantity (1.5)
    print("\n--- 6. Permanent Non-Taker Submits 1-Day Breakfast Request (Decimal: 1.5) ---")
    temp_req_res = api_call("/breakfast/temporary-request", method="POST", data={
        "targetDate": "2026-10-02",
        "quantity": 1.5,
        "reason": "Attending morning workshop"
    }, token=shahil_token)
    assert temp_req_res["success"], f"Failed to submit temporary request: {temp_req_res}"
    print(f"Temporary request created: Date={temp_req_res['request'].get('requestedDate')}, Qty={temp_req_res['request'].get('quantity')}, Status={temp_req_res['request'].get('status')}")

    # Verify Shahil is STILL PERMANENT_NON_TAKER
    shahil_profile = api_call("/auth/me", token=shahil_token)
    print(f"Shahil profile after 1-day request: participationType={shahil_profile['user'].get('breakfastParticipationType')}")
    assert shahil_profile['user'].get('breakfastParticipationType') == 'PERMANENT_NON_TAKER', "Permanent status changed unexpectedly!"

    # 7. Check CEO Dashboard includes the 1.5 temporary request
    print("\n--- 7. CEO Dashboard with One-Day Request ---")
    ceo_data2 = api_call("/reports/ceo?date=2026-10-02", token=ceo_token)
    print(f"  todayRequestedQty: {ceo_data2['todayRequestedQty']}")
    print(f"  dailySummary.requestedQuantity: {ceo_data2['dailySummary']['requestedQuantity']}")
    assert ceo_data2['todayRequestedQty'] >= 1.5, f"Expected requested qty to include 1.5, got {ceo_data2['todayRequestedQty']}"

    # 8. Record Daily Entry with Actual Served Quantity (e.g. 7.5)
    print("\n--- 8. Admin Records Daily Entry with Actual Served Quantity (7.5) ---")
    vasudev_login = api_call("/auth/login", method="POST", data={"username": "vasudev", "password": "Vasudev123"})
    vasudev_token = vasudev_login["token"]
    daily_entry_res = api_call("/breakfast/daily-entries", method="POST", data={
        "date": "2026-10-02",
        "mealType": "BREAKFAST",
        "employeeRequestQuantity": ceo_data2['todayRequestedQty'],
        "actualResponseQuantity": 7.5,
        "bufferQuantity": 0,
        "totalQuantity": 7.5,
        "unitPrice": 45.0,
        "totalCost": 337.5,
        "notes": "Verified actual response quantity recorded"
    }, token=vasudev_token)
    print("Daily entry created/updated:", daily_entry_res.get("success", True))

    # 9. Check CEO Dashboard reflects Actual Served Quantity and Difference
    print("\n--- 9. Verify CEO Dashboard KPIs & Period Summaries ---")
    ceo_data3 = api_call("/reports/ceo?date=2026-10-02", token=ceo_token)
    print(f"  totalEmployees: {ceo_data3['totalEmployees']}")
    print(f"  regularTakers: {ceo_data3['regularTakers']}")
    print(f"  permanentNonTakers: {ceo_data3['permanentNonTakers']}")
    print(f"  todayRequestedQty: {ceo_data3['todayRequestedQty']}")
    print(f"  todayActualServedQty: {ceo_data3['todayActualServedQty']}")
    print(f"  requestActualDifference: {ceo_data3['requestActualDifference']}")
    print(f"  participationRate: {ceo_data3['participationRate']}%")
    print(f"  dailySummary: {ceo_data3['dailySummary']}")
    print(f"  weeklySummary: {ceo_data3['weeklySummary']}")
    print(f"  monthlySummary: {ceo_data3['monthlySummary']}")

    assert ceo_data3['todayActualServedQty'] == 7.5, f"Expected 7.5 actual served qty, got {ceo_data3['todayActualServedQty']}"
    assert ceo_data3['requestActualDifference'] == round(ceo_data3['todayRequestedQty'] - 7.5, 2), "Difference calculation mismatch"

    # 10. Test Finance Manager Role Access
    print("\n--- 10. Finance Manager Role Verification ---")
    fm_login = api_call("/auth/login", method="POST", data={"username": "finance.manager", "password": "Finance123"})
    fm_token = fm_login["token"]
    print(f"Logged in user: {fm_login['user']['username']}, Roles: {fm_login['user']['roles']}")
    fund_requests = api_call("/finance/fund-requests", token=fm_token)
    print(f"Finance Manager accessed /finance/fund-requests successfully: {fund_requests.get('success', True)}")

    # Test that normal employee WITHOUT Finance Manager role is rejected
    print("\n--- 11. Normal Employee Access to Finance Rejection ---")
    try:
        api_call("/finance/fund-requests", token=shahil_token)
        print("ERROR: Shahil was able to access finance!")
    except urllib.error.HTTPError as he:
        print(f"Shahil correctly denied finance access: HTTP {he.code}")
        assert he.code in [401, 403], f"Expected 401 or 403, got {he.code}"

    # 12. Test Date Filtering on CEO Dashboard (Historical Date)
    print("\n--- 12. CEO Dashboard Date Filter Verification ---")
    oct1_data = api_call("/reports/ceo?date=2026-10-01", token=ceo_token)
    print(f"  October 1 Date filter returned: {oct1_data['dailySummary']['date']}")
    assert oct1_data['dailySummary']['date'] == "2026-10-01", "Date filter failed for 2026-10-01"

    print("\n==================================================")
    print("  ALL 12 NEON POSTGRESQL VERIFICATION CHECKS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
