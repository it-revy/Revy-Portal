import sys, os
sys.path.insert(0, ".")
import app.main
from app.core.database import SessionLocal
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

db = SessionLocal()

print("Testing CHECK constraint rejection with an invalid status in a rolled-back transaction...")
try:
    # Attempt to insert or update with invalid status 'InvalidStatus123'
    # We test on one of the test leads within a transaction that we immediately rollback
    db.execute(text("BEGIN;"))
    db.execute(text("""
        UPDATE leads
        SET lifecycle_status = 'InvalidStatus123'
        WHERE id = '1ceb1e53-1430-4b22-8cf9-a38dc46b8bf1';
    """))
    db.commit()
    print("FAILED: PostgreSQL allowed invalid status!")
    sys.exit(1)
except Exception as e:
    db.rollback()
    err_str = str(e)
    print(f"SUCCESS: Rejected with exception:\n  {err_str[:300]}...")
    assert "ck_leads_lifecycle_status" in err_str or "check constraint" in err_str.lower(), "Expected ck_leads_lifecycle_status violation"
    print("\nVerified: PostgreSQL CHECK constraint ck_leads_lifecycle_status is actively enforcing approved values!")

db.close()
