import sys, os
sys.path.insert(0, ".")
import app.main
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Target test records
target_leads = [
    {
        "id": "1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1",
        "lead_id": "LEAD-PG-374568aa",
        "opp_id": "95f49909-ab34-4beb-b826-54aa8682ccc5",
        "opp_code": "OPP-00014",
        "account_id": "a6192d62-a71e-41e7-9d09-4d42cfb96819",
        "contact_id": "08f117ad-b9cb-46fa-8e56-a912aaf36c8b"
    },
    {
        "id": "f18ea315-eed4-4bbe-a4de-ab3dfb8a3d20",
        "lead_id": "LEAD-PG-60229ec3",
        "opp_id": "5d23390d-d12f-45b4-828f-ab17747257d5",
        "opp_code": "OPP-00015",
        "account_id": "70e26e7c-e02e-43da-bf05-76eba4ac6740",
        "contact_id": "e43fc35d-a854-4315-9d3e-d84285210bd1"
    }
]

print("=== VERIFYING TARGET TEST LEADS ===")
for expected in target_leads:
    row = db.execute(text("""
        SELECT l.id, l.lead_id, l.lifecycle_status, l.account_id, l.contact_id, l.opportunity_id,
               o.opportunity_id as opp_code, a.account_id as acc_code, c.contact_id as con_code
        FROM leads l
        LEFT JOIN crm_opportunities o ON l.opportunity_id = o.id
        LEFT JOIN accounts a ON l.account_id = a.id
        LEFT JOIN contacts c ON l.contact_id = c.id
        WHERE l.id = :lid
    """), {"lid": expected["id"]}).fetchone()
    
    if not row:
        print(f"FAILED: Lead {expected['id']} not found!")
        sys.exit(1)
        
    print(f"Lead ID {row.id}: code={row.lead_id}, status={row.lifecycle_status}, opp={row.opp_code}, acc_id={row.account_id}, con_id={row.contact_id}")
    assert str(row.id) == expected["id"]
    assert row.lead_id == expected["lead_id"]
    assert str(row.opportunity_id) == expected["opp_id"]
    assert str(row.account_id) == expected["account_id"]
    assert str(row.contact_id) == expected["contact_id"]
    assert row.lifecycle_status == "Open"

print("All target test records verified exactly!")

print("\n=== VERIFYING NO OTHER UNAPPROVED STATUSES EXIST ===")
APPROVED = ('Enquiry', 'Offer', 'Negotiation', 'Supply', 'Payment', 'Dormant')
unapproved_rows = db.execute(text("""
    SELECT id, lead_id, lifecycle_status
    FROM leads
    WHERE id NOT IN (:id1, :id2)
      AND lifecycle_status NOT IN ('Enquiry', 'Offer', 'Negotiation', 'Supply', 'Payment', 'Dormant')
"""), {
    "id1": target_leads[0]["id"],
    "id2": target_leads[1]["id"]
}).fetchall()

if unapproved_rows:
    print(f"FAILED: Found {len(unapproved_rows)} unexpected rows with unapproved statuses:")
    for r in unapproved_rows:
        print(f"  {r.id} ({r.lead_id}): {r.lifecycle_status}")
    sys.exit(1)
else:
    print("Precondition satisfied: Zero other unapproved rows exist.")

db.close()
