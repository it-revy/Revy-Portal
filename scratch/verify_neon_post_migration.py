import sys, os
sys.path.insert(0, ".")
import app.main
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

cur_rev = db.execute(text("SELECT version_num FROM alembic_version;")).scalar()
print("Current alembic revision on Neon:", cur_rev)

lead_statuses = db.execute(text("SELECT lifecycle_status, count(*) FROM leads GROUP BY lifecycle_status ORDER BY count(*) DESC;")).fetchall()
print("Lead statuses on Neon:")
for st, cnt in lead_statuses:
    print(f"  {st}: {cnt}")

total_leads = db.execute(text("SELECT count(*) FROM leads;")).scalar()
print(f"Total Leads: {total_leads}")

total_opps = db.execute(text("SELECT count(*) FROM crm_opportunities;")).scalar()
print(f"Total Opps: {total_opps}")

total_accs = db.execute(text("SELECT count(*) FROM accounts;")).scalar()
print(f"Total Accounts: {total_accs}")

total_cons = db.execute(text("SELECT count(*) FROM contacts;")).scalar()
print(f"Total Contacts: {total_cons}")

# Check targeted leads
target_leads = [
    "1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1",
    "f18ea315-eed4-4bbe-a4de-ab3dfb8a3d20"
]
print("\nTargeted test leads status:")
for lid in target_leads:
    row = db.execute(text("SELECT id, lead_id, lifecycle_status FROM leads WHERE id = :lid"), {"lid": lid}).fetchone()
    print(f"  {row.id} ({row.lead_id}): {row.lifecycle_status}")

# Check constraint
query_constraint = text("""
    SELECT conname, pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    WHERE t.relname = 'leads' AND c.conname = 'ck_leads_lifecycle_status';
""")
con = db.execute(query_constraint).fetchall()
print("\nConstraint definition:")
for c in con:
    print(f"  {c[0]}: {c[1]}")

# Check column default
col_def = db.execute(text("""
    SELECT column_default
    FROM information_schema.columns
    WHERE table_name = 'leads' AND column_name = 'lifecycle_status';
""")).scalar()
print(f"\nColumn server_default: {col_def}")

db.close()
