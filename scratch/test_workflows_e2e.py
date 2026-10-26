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

token = create_access_token({
    "userId": user.id,
    "username": user.username,
    "roles": ["IT_ADMIN"]
})
headers = {
    "Authorization": f"Bearer {token}",
    "X-Role-Used": "IT_ADMIN"
}
import uuid
uid = uuid.uuid4().hex[:6]
comp_name = f"CleanPower Solutions {uid} Pvt Ltd"
comp_email = f"info_{uid}@cleanpower-test.com"
comp_phone = f"+91 11 {uid[:4]} 6789"
con_name = f"Arun Verma {uid}"
con_email = f"arun_{uid}@cleanpower-test.com"
con_phone = f"+91 98{uid[:4]} 4321"

print("==================================================")
print("CRM BUSINESS WORKFLOW AUDIT & VALIDATION")
print("==================================================")

# 1. CREATE TEST LEAD
lead_payload = {
    "leadName": f"Audit Clean Energy Lead {uid}",
    "firstName": "Arun",
    "lastName": f"Verma {uid}",
    "jobTitle": "Head of Engineering",
    "contactEmail": con_email,
    "mobilePhone": con_phone,
    "companyName": comp_name,
    "companyEmail": comp_email,
    "businessPhone": comp_phone,
    "websiteLink": f"https://www.cleanpower-{uid}.com",
    "location": "Pune, Maharashtra",
    "siteName": f"Chakan Facility {uid}",
    "industry": "Renewable Energy",
    "businessArea": "Biogas",
    "requirementTypes": ["Consulting", "Sample Testing", "Product"],
    "requirementSummary": "Anaerobic digestion efficiency testing and bacterial inoculant supply",
    "contactMethods": ["Email", "Phone Call"]
}

r_create = client.post("/api/crm/leads", headers=headers, json=lead_payload)
assert r_create.status_code in [200, 201], f"Lead creation failed: {r_create.text}"
created_lead = r_create.json()["lead"]
lead_id = created_lead["id"]
print(f"[PASS] 1. Created Lead: id={lead_id}, leadId={created_lead['leadId']}")

# 2. STATUS TRANSITION: Open -> Disqualified
r_disqualify = client.post(f"/api/crm/leads/{lead_id}/status", headers=headers, json={
    "status": "Disqualified",
    "remarks": "Testing disqualification workflow"
})
assert r_disqualify.status_code == 200, f"Disqualification failed: {r_disqualify.text}"
print(f"[PASS] 2. Disqualified Lead: status={r_disqualify.json()['lead']['lifecycleStatus']}")

# 3. VERIFY DISQUALIFIED CANNOT BE QUALIFIED DIRECTLY
qualify_payload = {
    "account": {
        "action": "create",
        "name": comp_name,
        "siteName": f"Chakan Facility {uid}",
        "industry": "Renewable Energy",
        "website": f"https://www.cleanpower-{uid}.com",
        "phone": comp_phone,
        "email": comp_email,
        "address": "Pune, Maharashtra"
    },
    "contact": {
        "action": "create",
        "name": con_name,
        "email": con_email,
        "mobileNumber": con_phone,
        "designation": "Head of Engineering"
    },
    "opportunityName": f"CleanPower Biogas Modernization {uid}",
    "estimatedValue": 750000.0,
    "opportunityDescription": "Turnkey assessment and microbial dosing"
}

r_qual_fail = client.post(f"/api/crm/leads/{lead_id}/qualify", headers=headers, json=qualify_payload)
assert r_qual_fail.status_code in [400, 422], f"Expected rejection of disqualified lead: {r_qual_fail.status_code} {r_qual_fail.text}"
print(f"[PASS] 3. Direct qualification of Disqualified lead correctly rejected: {r_qual_fail.status_code}")

# 4. REOPEN LEAD TO OPEN
r_reopen = client.post(f"/api/crm/leads/{lead_id}/status", headers=headers, json={
    "status": "Open",
    "remarks": "Reopening lead for qualification"
})
assert r_reopen.status_code == 200, f"Reopen failed: {r_reopen.text}"
print(f"[PASS] 4. Reopened Lead: status={r_reopen.json()['lead']['lifecycleStatus']}")

# 5. QUALIFY LEAD (ATOMIC TRANSACTION)
r_qual = client.post(f"/api/crm/leads/{lead_id}/qualify", headers=headers, json=qualify_payload)
assert r_qual.status_code == 200, f"Qualification failed: {r_qual.text}"
qual_res = r_qual.json()
opp = qual_res["opportunity"]
account = qual_res["account"]
contact = qual_res["contact"]
opp_id = opp["id"]
print(f"[PASS] 5. Successfully Qualified Lead! Created Opp: {opp['opportunityId']} (id={opp_id})")
print(f"       Account: {account.get('name')} | siteName: {account.get('siteName')} (id={account.get('id')})")
print(f"       Contact: {contact.get('name')} | desig: {contact.get('designation')} | mobile: {contact.get('mobileNumber')}")

# 6. VERIFY FIELD MAPPINGS AND BOUNDARIES
assert account["name"] == comp_name
assert account.get("siteName") == f"Chakan Facility {uid}"
assert account["phone"] == comp_phone  # company phone
assert account["email"] == comp_email  # company email
assert contact["name"] == con_name
assert contact["mobileNumber"] == con_phone  # contact mobile
assert contact["email"] == con_email  # contact email
assert contact["mobileNumber"] != account["phone"], "Company phone leaked to contact mobile!"
assert contact["email"] != account["email"], "Company email leaked to contact personal email!"
print("[PASS] 6. Field mapping verified without cross-boundary data leakage!")

# 7. REQUIREMENT ROUTING & IDEMPOTENCY
r_route = client.post(f"/api/crm/opportunities/{opp_id}/route-requirements", headers=headers, json={
    "requirementTypes": ["Consulting", "Sample Testing", "Product"]
})
assert r_route.status_code == 200, f"Requirement routing failed: {r_route.text}"
route_res = r_route.json()
print(f"[PASS] 7a. Routed requirements: {route_res.get('message')}")
routed_list = route_res.get("routedWorkstreams", [])
assert len(routed_list) == 3, f"Expected 3 newly routed workstreams, got {len(routed_list)}"

# Query linked workstreams via GET
r_ws = client.get(f"/api/crm/opportunities/{opp_id}/workstreams", headers=headers)
assert r_ws.status_code == 200
total_ws_1 = len(r_ws.json().get("workstreams", []))
assert total_ws_1 == 3, f"Expected 3 linked workstreams, got {total_ws_1}"

# Re-run routing to prove idempotency
r_route_repeat = client.post(f"/api/crm/opportunities/{opp_id}/route-requirements", headers=headers, json={
    "requirementTypes": ["Consulting", "Sample Testing", "Product"]
})
assert r_route_repeat.status_code == 200
route_res_2 = r_route_repeat.json()
assert "already routed" in route_res_2.get("message", "")
ws_ids_2 = {w["id"] for w in route_res_2.get("routedWorkstreams", [])}
ws_ids_1 = {w["id"] for w in route_res.get("routedWorkstreams", [])}
assert ws_ids_1 == ws_ids_2, f"Repeated routing generated duplicate/divergent workstream IDs! {ws_ids_1} vs {ws_ids_2}"

r_ws_2 = client.get(f"/api/crm/opportunities/{opp_id}/workstreams", headers=headers)
assert r_ws_2.status_code == 200
total_ws_2 = len(r_ws_2.json().get("workstreams", []))
assert total_ws_2 == 3, f"Repeated routing resulted in workstream count {total_ws_2} instead of 3!"
print(f"[PASS] 7b. Requirement routing is strictly IDEMPOTENT (workstream count remains {total_ws_2})")

# 8. OPPORTUNITY PIPELINE STAGE TRANSITIONS
stages = ["Develop", "Propose", "Close"]
for stg in stages:
    payload = {"newStage": stg, "remarks": f"Advancing to {stg}"}
    if stg == "Close":
        payload["status"] = "Won"
    r_stg = client.post(f"/api/crm/opportunities/{opp_id}/stage", headers=headers, json=payload)
    assert r_stg.status_code == 200, f"Stage transition to {stg} failed: {r_stg.text}"
    updated_opp = r_stg.json()["opportunity"]
    print(f"[PASS] 8. Advanced Opportunity to stage: {updated_opp['stage']}, status: {updated_opp['status']}")

# 9. MILESTONE CREATION & LIFECYCLE
mls_payload = {
    "title": "Initial Lab Sample Analysis",
    "workstreamType": "sample_testing",
    "dueDate": "2026-11-15",
    "description": "Biological oxygen demand and volatile fatty acids analysis"
}
r_mls = client.post(f"/api/crm/opportunities/{opp_id}/milestones", headers=headers, json=mls_payload)
assert r_mls.status_code in [200, 201], f"Milestone creation failed: {r_mls.text}"
mls = r_mls.json()["milestone"]
mls_id = mls["id"]
print(f"[PASS] 9a. Created Milestone: {mls['milestoneId']} (id={mls_id})")

r_mls_stat = client.post(f"/api/crm/milestones/{mls_id}/status", headers=headers, json={
    "status": "Completed",
    "completionNotes": "All assays finished within spec."
})
assert r_mls_stat.status_code == 200, f"Milestone status update failed: {r_mls_stat.text}"
print(f"[PASS] 9b. Completed Milestone: status={r_mls_stat.json()['milestone']['status']}")

# 10. PERSISTENCE VERIFICATION AFTER RETRIEVAL
r_lead_check = client.get(f"/api/crm/leads/{lead_id}", headers=headers)
assert r_lead_check.status_code == 200
retrieved_lead = r_lead_check.json()["lead"]
assert retrieved_lead["lifecycleStatus"] == "Qualified"
assert retrieved_lead["opportunityId"] == opp_id
print(f"[PASS] 10. Complete workflow verified and persisted in PostgreSQL!")

print("==================================================")
print("ALL 10 CRM BUSINESS WORKFLOW CHECKS PASSED!")
print("==================================================")
