import sys
from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_current_user, CurrentUser
from app.models import User
from app.core.database import SessionLocal

def run_live_crm_api_tests():
    # Setup mock CRM Admin user
    mock_user = CurrentUser(
        user=User(id="test-admin-uuid", username="crmadmin", email="crmadmin@revy.co.in", status="active"),
        active_role="CRM_ADMIN",
        roles=["CRM_ADMIN", "IT_ADMIN"],
        permissions=["*"],
        all_permissions=["*"],
        permissions_by_role={"CRM_ADMIN": ["*"]},
        modules=["CRM"],
        module_roles={"CRM": "CRM_ADMIN"},
        is_global_admin=True
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)

    endpoints_to_test = [
        ("GET", "/api/crm/accounts", 200),
        ("GET", "/api/crm/collateral?view=all", 200),
        ("GET", "/api/crm/collateral?view=quotations", 200),
        ("GET", "/api/crm/collateral?view=invoices", 200),
        ("GET", "/api/crm/opportunities", 200),
        ("GET", "/api/crm/catalogue/services", 200),
        ("GET", "/api/crm/catalogue/packages", 200),
        ("GET", "/api/crm/company-settings", 200),
        ("GET", "/api/crm/catalogue/categories", 200),
        ("GET", "/api/crm/catalogue/tax-configurations", 200),
    ]

    print("Running Live CRM Endpoint Tests Against Neon DB...")
    print("=" * 70)
    failed = 0

    for method, path, expected_status in endpoints_to_test:
        try:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path)

            status = response.status_code
            if status == expected_status:
                data_summary = ""
                try:
                    json_data = response.json()
                    if isinstance(json_data, list):
                        data_summary = f"({len(json_data)} items returned)"
                    elif isinstance(json_data, dict):
                        if "items" in json_data and isinstance(json_data["items"], list):
                            data_summary = f"({len(json_data['items'])} items returned)"
                        elif "data" in json_data and isinstance(json_data["data"], list):
                            data_summary = f"({len(json_data['data'])} items returned)"
                        elif "total" in json_data:
                            data_summary = f"(total: {json_data['total']})"
                        else:
                            data_summary = f"(keys: {list(json_data.keys())[:4]})"
                except Exception:
                    data_summary = "(non-json)"

                print(f"[PASS] {method} {path} -> {status} {data_summary}")
            else:
                print(f"[FAIL] {method} {path} -> Expected {expected_status}, Got {status}: {response.text[:200]}")
                failed += 1
        except Exception as e:
            print(f"[ERROR] {method} {path} -> Exception: {e}")
            failed += 1

    print("=" * 70)
    print(f"Results: {len(endpoints_to_test) - failed}/{len(endpoints_to_test)} endpoints passed.")
    if failed == 0:
        print("ALL CRM ENDPOINTS RECOVERED AND RETURNING 200 OK!")
        return True
    else:
        print(f"{failed} endpoints failed.")
        return False

if __name__ == "__main__":
    success = run_live_crm_api_tests()
    sys.exit(0 if success else 1)
