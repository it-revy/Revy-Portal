import sys
import httpx

backend_dir = r"e:\IT Development\REVY Portal\Revy-Portal\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import get_engine
from app.core.security import create_access_token
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    user = conn.execute(text("SELECT id, username, email FROM users WHERE username = 'vasudev';")).fetchone()

token = create_access_token({
    "userId": user.id,
    "username": user.username,
    "roles": ["IT_ADMIN"]
})

headers = {
    "Authorization": f"Bearer {token}",
    "X-Role-Used": "IT_ADMIN"
}

base_url = "http://127.0.0.1:5001/api"

endpoints = [
    ("/crm/leads", "Leads"),
    ("/crm/accounts", "Accounts"),
    ("/crm/contacts", "Contacts"),
    ("/crm/opportunities", "Opportunities"),
    ("/crm/opportunities/pipeline-summary", "Pipeline Summary"),
    ("/crm/dashboard/metrics", "Dashboard Metrics")
]

print("=== ACTUAL HTTP ENDPOINT VERIFICATION (http://127.0.0.1:5001) ===")
all_passed = True
for path, name in endpoints:
    url = f"{base_url}{path}"
    try:
        r = httpx.get(url, headers=headers, timeout=15)
        print(f"\n[{name}] {url}")
        print(f"  HTTP Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Success: {data.get('success')}")
            if "leads" in data:
                print(f"  Record Count: {len(data['leads'])} (total: {data.get('total')})")
            elif "accounts" in data:
                print(f"  Record Count: {len(data['accounts'])} (count: {data.get('count')})")
            elif "contacts" in data:
                print(f"  Record Count: {len(data['contacts'])} (count: {data.get('count')})")
            elif "opportunities" in data:
                print(f"  Record Count: {len(data['opportunities'])} (totalCount: {data.get('totalCount')})")
            else:
                print(f"  Response keys: {list(data.keys())}")
        else:
            print(f"  FAILED: {r.status_code} - {r.text}")
            all_passed = False
    except Exception as e:
        print(f"  ERROR calling {url}: {e}")
        all_passed = False

print(f"\nFinal Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
