import sys, os
sys.path.insert(0, os.path.abspath("."))
import app.main
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
query = text("""
    SELECT conname, pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    JOIN pg_namespace n ON t.relnamespace = n.oid
    WHERE t.relname = 'leads' AND n.nspname = 'public';
""")
rows = db.execute(query).fetchall()
print("Constraints on leads table:")
for name, defn in rows:
    print(f"  {name}: {defn}")

# Also check column definition of lifecycle_status
col_query = text("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'leads' AND column_name IN ('lifecycle_status', 'legacy_lifecycle_status');
""")
cols = db.execute(col_query).fetchall()
print("\nColumns:")
for col in cols:
    print(f"  {col}")

db.close()
