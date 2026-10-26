import httpx

base_url = "http://127.0.0.1:5001/api"

# 1. Login
login_res = httpx.post(f"{base_url}/auth/login", json={
    "username": "crm.admin",
    "password": "CrmAdmin123!"
}, timeout=15)

assert login_res.status_code == 200, f"Login failed: {login_res.text}"
token = login_res.json()["token"]

headers = {
    "Authorization": f"Bearer {token}",
    "X-Role-Used": "CRM_ADMIN"
}

endpoints = [
    ("/crm/status", "CRM Status"),
    ("/crm/dashboard/metrics", "Dashboard Metrics"),
    ("/crm/leads", "Leads List"),
    ("/crm/accounts", "Accounts List"),
    ("/crm/contacts", "Contacts List"),
    ("/crm/opportunities", "Opportunities List"),
    ("/crm/opportunities/pipeline-summary", "Pipeline Summary"),
    ("/crm/users", "CRM Users"),
    ("/crm/roles", "CRM Roles"),
    ("/crm/assignees", "CRM Assignees")
]

print("==================================================")
print("LIVE HTTP VERIFICATION ON http://127.0.0.1:5001")
print("==================================================")

passed = 0
for path, name in endpoints:
    url = f"{base_url}{path}"
    try:
        r = httpx.get(url, headers=headers, timeout=15)
        print(f"\n[{name}] {path} -> HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            success = data.get("success")
            extra = ""
            if "leads" in data:
                extra = f"leads count: {len(data['leads'])}, total: {data.get('total')}"
            elif "accounts" in data:
                extra = f"accounts count: {len(data['accounts'])}, total: {data.get('total')}"
            elif "contacts" in data:
                extra = f"contacts count: {len(data['contacts'])}, total: {data.get('total')}"
            elif "opportunities" in data:
                extra = f"opps count: {len(data['opportunities'])}, totalCount: {data.get('totalCount')}"
            elif "totalLeads" in data:
                extra = f"totalLeads: {data.get('totalLeads')}, openLeads: {data.get('openLeads')}"
            elif "users" in data:
                extra = f"users count: {len(data['users'])}"
            elif "roles" in data:
                extra = f"roles count: {len(data['roles'])}"
            elif "assignees" in data:
                extra = f"assignees count: {len(data['assignees'])}"
            print(f"  Result: SUCCESS (success={success}) | {extra}")
            passed += 1
        else:
            print(f"  FAILED: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"  EXCEPTION: {e}")

print("\n==================================================")
print(f"VERIFICATION COMPLETE: {passed}/{len(endpoints)} ENDPOINTS PASSED")
print("==================================================")
