import os
import sys

# Point to ep-silent-sound
with open(r"backend/.env", "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("#postgresql://") and "ep-silent-sound" in line:
            os.environ["DATABASE_URL"] = line.lstrip("#")
            break

backend_dir = r"e:\IT Development\REVY Portal\Revy-Portal\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.core.database import get_engine
from sqlalchemy import text

client = TestClient(app)

engine = get_engine()
with engine.connect() as conn:
    user = conn.execute(text("SELECT id, username, email FROM users WHERE username = 'vasudev';")).fetchone()
    print(f"Audit testing with IT Admin user: {user.username} (id={user.id})")

token = create_access_token({
    "userId": user.id,
    "username": user.username,
    "roles": ["IT_ADMIN"]
})
headers = {
    "Authorization": f"Bearer {token}",
    "X-Role-Used": "IT_ADMIN"
}

results = []

def run_check(name, method, url, json_body=None, params=None, expected_status=200):
    try:
        if method == "GET":
            r = client.get(url, headers=headers, params=params)
        elif method == "POST":
            r = client.post(url, headers=headers, json=json_body)
        elif method == "PUT":
            r = client.put(url, headers=headers, json=json_body)
        elif method == "DELETE":
            r = client.delete(url, headers=headers)
        
        passed = (r.status_code == expected_status)
        details = ""
        if passed and r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                # Summary of keys and lengths
                counts = {k: len(data[k]) if isinstance(data[k], list) else data[k] for k in list(data.keys())[:8]}
                details = str(counts)
            elif isinstance(data, list):
                details = f"List of {len(data)} items"
        else:
            details = f"Status {r.status_code}: {r.text[:200]}"
            
        results.append({
            "test": name,
            "url": url,
            "status": r.status_code,
            "passed": passed,
            "details": details
        })
        print(f"[{'PASS' if passed else 'FAIL'}] {name} ({url}) -> Status {r.status_code}")
        if not passed:
            print(f"   Details: {details}")
        return r
    except Exception as e:
        results.append({
            "test": name,
            "url": url,
            "status": "EXCEPTION",
            "passed": False,
            "details": str(e)
        })
        print(f"[FAIL] {name} ({url}) -> EXCEPTION: {e}")
        return None

print("\n=== 1. DASHBOARD & METRICS ===")
run_check("Dashboard Metrics", "GET", "/api/crm/dashboard/metrics")

print("\n=== 2. LEADS ===")
r_leads = run_check("List Leads (Open)", "GET", "/api/crm/leads", params={"view": "open"})
run_check("List Leads (All)", "GET", "/api/crm/leads", params={"view": "all"})
run_check("List Leads (Search)", "GET", "/api/crm/leads", params={"view": "all", "search": "waste"})
first_lead_id = None
if r_leads and r_leads.status_code == 200:
    leads_data = r_leads.json().get("leads", [])
    if leads_data:
        first_lead_id = leads_data[0]["id"]
        print(f"Testing with Lead: id={first_lead_id}, leadId={leads_data[0].get('leadId')}")
        run_check("Get Lead By ID", "GET", f"/api/crm/leads/{first_lead_id}")
        run_check("Lead Communications", "GET", f"/api/crm/leads/{first_lead_id}/communications")
        run_check("Lead Qualification Matches", "GET", f"/api/crm/leads/{first_lead_id}/qualification-matches")

print("\n=== 3. ACCOUNTS ===")
r_accs = run_check("List Accounts", "GET", "/api/crm/accounts")
run_check("Account Matches", "GET", "/api/crm/accounts/matches", params={"name": "Tata"})
if r_accs and r_accs.status_code == 200:
    accs = r_accs.json().get("accounts", [])
    if accs:
        run_check("Get Account By ID", "GET", f"/api/crm/accounts/{accs[0]['id']}")

print("\n=== 4. CONTACTS ===")
r_conts = run_check("List Contacts", "GET", "/api/crm/contacts")
run_check("Contact Matches", "GET", "/api/crm/contacts/matches", params={"name": "Sharma"})
if r_conts and r_conts.status_code == 200:
    conts = r_conts.json().get("contacts", [])
    if conts:
        run_check("Get Contact By ID", "GET", f"/api/crm/contacts/{conts[0]['id']}")

print("\n=== 5. OPPORTUNITIES & PIPELINE ===")
run_check("Pipeline Summary", "GET", "/api/crm/opportunities/pipeline-summary")
r_opps = run_check("List Opportunities", "GET", "/api/crm/opportunities")
if r_opps and r_opps.status_code == 200:
    opps = r_opps.json().get("opportunities", [])
    if opps:
        opp_id = opps[0]["id"]
        print(f"Testing with Opportunity: id={opp_id}, oppId={opps[0].get('opportunityId')}")
        run_check("Get Opportunity By ID", "GET", f"/api/crm/opportunities/{opp_id}")
        run_check("Opportunity Workstreams", "GET", f"/api/crm/opportunities/{opp_id}/workstreams")
        run_check("Opportunity Milestones", "GET", f"/api/crm/opportunities/{opp_id}/milestones")

print("\n=== 6. MILESTONES ===")
run_check("Upcoming Milestones", "GET", "/api/crm/milestones/upcoming")

print("\n=== 7. CRM USER HUB & ASSIGNEES ===")
run_check("List Eligible Assignees", "GET", "/api/crm/assignees")
run_check("CRM Users Hub", "GET", "/api/crm/users")
run_check("CRM Roles List", "GET", "/api/crm/roles")

print("\n" + "="*60)
passed_cnt = sum(1 for r in results if r["passed"])
failed_cnt = sum(1 for r in results if not r["passed"])
print(f"AUDIT SUMMARY: {passed_cnt} PASSED, {failed_cnt} FAILED out of {len(results)} checks")
print("="*60)
