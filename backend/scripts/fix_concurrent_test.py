import os

test_file = os.path.join(os.path.dirname(__file__), "..", "tests", "test_crm_core_services_and_apis.py")
with open(test_file, "r", encoding="utf-8") as f:
    code = f.read()

target = """    def attempt_create_lead(idx):
        return client.post("/api/v1/crm/leads", json={
            "leadName": f"Concurrent Lead Attempt {idx}",
            "businessArea": "WWT",
            "requirementType": "Direct Product/Service",
            "requestedProductService": same_product,
            "contactId": con_id,
            "accountId": acc_id
        }, headers=headers)"""

replacement = """    def attempt_create_lead(idx):
        with TestClient(app) as local_client:
            return local_client.post("/api/v1/crm/leads", json={
                "leadName": f"Concurrent Lead Attempt {idx}",
                "businessArea": "WWT",
                "requirementType": "Direct Product/Service",
                "requestedProductService": same_product,
                "contactId": con_id,
                "accountId": acc_id
            }, headers=headers)"""

if target in code:
    code = code.replace(target, replacement, 1)
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(code)
    print("Updated test_crm_core_services_and_apis.py successfully!")
else:
    print("Target not found in test_crm_core_services_and_apis.py")

