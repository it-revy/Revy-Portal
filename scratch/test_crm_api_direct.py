import sys
import json
backend_dir = r"e:\IT Development\REVY Portal\Revy-Portal\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_engine
from app.core.security import create_access_token
from sqlalchemy import text

client = TestClient(app)

# 1. Fetch user vasudev to generate valid token
engine = get_engine()
with engine.connect() as conn:
    user = conn.execute(text("SELECT id, username, email FROM users WHERE username = 'vasudev';")).fetchone()
    if not user:
        user = conn.execute(text("SELECT id, username, email FROM users WHERE username = 'crm.admin';")).fetchone()
    
    print(f"Testing with user: {user.username} (id={user.id})")

token = create_access_token({
    "userId": user.id,
    "username": user.username,
    "roles": ["IT_ADMIN"]
})
headers = {
    "Authorization": f"Bearer {token}",
    "X-Role-Used": "IT_ADMIN"
}

endpoints = [
    ("/api/crm/leads", "Leads"),
    ("/api/crm/accounts", "Accounts"),
    ("/api/crm/contacts", "Contacts"),
    ("/api/crm/opportunities", "Opportunities"),
    ("/api/crm/opportunities/pipeline-summary", "Pipeline Summary"),
    ("/api/crm/dashboard/metrics", "Dashboard Metrics")
]

print("\n" + "="*50)
print("TESTING CRM API ENDPOINTS AGAINST POSTGRESQL")
print("="*50)

all_passed = True
for url, name in endpoints:
    try:
        resp = client.get(url, headers=headers)
        print(f"\n[{name}] {url}")
        print(f"  HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            success = data.get("success", False)
            print(f"  Success Flag: {success}")
            if "leads" in data:
                print(f"  Returned Leads Count: {len(data['leads'])} (total: {data.get('total', 'N/A')})")
                if len(data['leads']) > 0:
                    sample = data['leads'][0]
                    print(f"  Sample Lead: id={sample.get('id')}, name={sample.get('leadName')}, siteName={sample.get('siteName')}")
            elif "accounts" in data:
                print(f"  Returned Accounts Count: {len(data['accounts'])} (count field: {data.get('count', 'N/A')})")
                if len(data['accounts']) > 0:
                    sample = data['accounts'][0]
                    print(f"  Sample Account: id={sample.get('id')}, name={sample.get('name')}, siteName={sample.get('siteName')}")
            elif "contacts" in data:
                print(f"  Returned Contacts Count: {len(data['contacts'])} (count field: {data.get('count', 'N/A')})")
                if len(data['contacts']) > 0:
                    sample = data['contacts'][0]
                    print(f"  Sample Contact: id={sample.get('id')}, name={sample.get('fullName')}, accountId={sample.get('accountId')}")
            elif "opportunities" in data:
                print(f"  Returned Opportunities Count: {len(data['opportunities'])} (totalCount: {data.get('totalCount', 'N/A')})")
                if len(data['opportunities']) > 0:
                    sample = data['opportunities'][0]
                    print(f"  Sample Opportunity: id={sample.get('id')}, name={sample.get('name')}, stage={sample.get('stage')}, siteName={sample.get('account', {}).get('siteName') if sample.get('account') else None}")
            else:
                print(f"  Keys in Response: {list(data.keys())}")
        else:
            print(f"  Error Response: {resp.text}")
            all_passed = False
    except Exception as e:
        print(f"  EXCEPTION on {name}: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

print("\n" + "="*50)
print(f"ALL ENDPOINTS PASSED: {all_passed}")
print("="*50)
