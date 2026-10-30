import httpx

client = httpx.Client(base_url="http://127.0.0.1:5001/api/v1", timeout=60.0)
res = client.post("/auth/login", json={"username": "stg4_sales_exec", "password": "Pass123!"})
data = res.json()
print("Login status:", res.status_code, "token:", bool(data.get("token")))
token = data.get("token")
headers = {"Authorization": f"Bearer {token}"}

res2 = client.get("/crm/opportunities", headers=headers)
opps = res2.json()
print("Opportunities count:", opps.get("count"), "totalCount:", opps.get("totalCount"))
if opps.get("opportunities"):
    for o in opps["opportunities"][:5]:
        print("Opp:", o.get("id"), o.get("name"), o.get("stage"), o.get("status"), "Quotations:", len(o.get("quotations", [])))

res3 = client.get("/crm/opportunities/pipeline-summary", headers=headers)
print("Pipeline summary:", res3.json())
