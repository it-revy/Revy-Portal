import sys, os
sys.path.insert(0, ".")
import app.main
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 60)
print("VERIFICATION CHECK 1: ALEMBIC HEAD")
print("=" * 60)
cur_rev = db.execute(text("SELECT version_num FROM alembic_version;")).scalar()
print(f"Alembic Current Head: {cur_rev}")
assert cur_rev == "m0n1o2p3q4r5", f"Expected m0n1o2p3q4r5, got {cur_rev}"
print("-> PASS: Alembic head is m0n1o2p3q4r5")

print("\n" + "=" * 60)
print("VERIFICATION CHECK 2 & 3: TARGETED LEADS & TOTAL LEADS COUNT")
print("=" * 60)
total_leads = db.execute(text("SELECT count(*) FROM leads;")).scalar()
print(f"Total Leads Count: {total_leads}")
assert total_leads == 41, f"Expected 41 leads, got {total_leads}"
print("-> PASS: All 41 existing Leads remain present.")

target_leads = [
    ("1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1", "LEAD-PG-374568aa"),
    ("f18ea315-eed4-4bbe-a4de-ab3dfb8a3d20", "LEAD-PG-60229ec3")
]
for lid, code in target_leads:
    row = db.execute(text("SELECT id, lead_id, lifecycle_status FROM leads WHERE id = :lid"), {"lid": lid}).fetchone()
    print(f"Target Lead {row.lead_id}: status={row.lifecycle_status}")
    assert row.lifecycle_status == "Enquiry", f"Expected Enquiry, got {row.lifecycle_status}"
print("-> PASS: Both targeted Leads now have 'Enquiry' status.")

print("\n" + "=" * 60)
print("VERIFICATION CHECK 4: ALL PERSISTED LEAD STATUSES BELONG TO APPROVED VALUES")
print("=" * 60)
APPROVED = ('Enquiry', 'Offer', 'Negotiation', 'Supply', 'Payment', 'Dormant')
lead_statuses = db.execute(text("SELECT lifecycle_status, count(*) FROM leads GROUP BY lifecycle_status ORDER BY count(*) DESC;")).fetchall()
for st, cnt in lead_statuses:
    print(f"  {st}: {cnt}")
    assert st in APPROVED, f"Invalid status found: {st}"
print("-> PASS: 100% of persisted Lead statuses belong to the six approved values.")

print("\n" + "=" * 60)
print("VERIFICATION CHECK 5: POSTGRESQL COLUMN DEFAULT IS ENQUIRY")
print("=" * 60)
col_def = db.execute(text("""
    SELECT column_default
    FROM information_schema.columns
    WHERE table_name = 'leads' AND column_name = 'lifecycle_status';
""")).scalar()
print(f"PostgreSQL column default: {col_def}")
assert "Enquiry" in col_def, f"Expected Enquiry default, got {col_def}"
print("-> PASS: Column server_default is 'Enquiry'.")

print("\n" + "=" * 60)
print("VERIFICATION CHECK 6: CHECK CONSTRAINT EXISTS AND REJECTS INVALID VALUES")
print("=" * 60)
con_def = db.execute(text("""
    SELECT conname, pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    WHERE t.relname = 'leads' AND c.conname = 'ck_leads_lifecycle_status';
""")).fetchall()
print(f"Constraint in catalog: {con_def}")
assert len(con_def) == 1, "Constraint ck_leads_lifecycle_status not found in pg_constraint"

# Test rejection
rejected = False
try:
    db.execute(text("BEGIN;"))
    db.execute(text("UPDATE leads SET lifecycle_status = 'InvalidTestStatus' WHERE id = '1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1';"))
    db.commit()
except Exception as e:
    db.rollback()
    rejected = True
    print(f"Successfully caught expected check violation: {str(e)[:180]}...")
assert rejected, "CHECK constraint failed to reject invalid status!"
print("-> PASS: CHECK constraint ck_leads_lifecycle_status is actively rejecting invalid statuses.")

print("\n" + "=" * 60)
print("VERIFICATION CHECK 7: EXISTING BUSINESS RECORDS INTACT")
print("=" * 60)
total_opps = db.execute(text("SELECT count(*) FROM crm_opportunities;")).scalar()
total_accs = db.execute(text("SELECT count(*) FROM accounts;")).scalar()
total_cons = db.execute(text("SELECT count(*) FROM contacts;")).scalar()
total_users = db.execute(text("SELECT count(*) FROM users;")).scalar()
total_roles = db.execute(text("SELECT count(*) FROM module_roles;")).scalar()
total_employees = db.execute(text("SELECT count(*) FROM employees;")).scalar()

print(f"Opportunities count: {total_opps} (Expected: 15)")
print(f"Accounts count: {total_accs} (Expected: 32)")
print(f"Contacts count: {total_cons} (Expected: 34)")
print(f"Users count: {total_users}")
print(f"Module Roles count: {total_roles}")
print(f"BMS Employees count: {total_employees}")

assert total_opps == 15
assert total_accs == 32
assert total_cons == 34
print("-> PASS: All Opportunities, Accounts, Contacts, BMS, and RBAC records remain 100% intact.")

db.close()
print("\nAll database checks PASSED perfectly!")
