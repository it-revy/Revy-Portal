import os
import sys
from urllib.parse import urlparse

# Ensure backend directory is in sys.path
backend_dir = r"e:\IT Development\REVY Portal\Revy-Portal\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.core.database import get_engine
from sqlalchemy import text, inspect

def check_db():
    raw_url = settings.DATABASE_URL
    parsed = urlparse(raw_url)
    
    # Safe printing: NO credentials
    safe_user = "***" if parsed.username else None
    safe_netloc = f"{safe_user}:***@{parsed.hostname}" if parsed.hostname else parsed.netloc
    if parsed.port:
        safe_netloc += f":{parsed.port}"
    
    print("=== DATABASE CONFIGURATION ===")
    print(f"Scheme: {parsed.scheme}")
    print(f"Host: {parsed.hostname}")
    print(f"Port: {parsed.port}")
    print(f"Database Name: {parsed.path.lstrip('/')}")
    print(f"Sanitized URL: {parsed.scheme}://{safe_netloc}{parsed.path}")
    
    engine = get_engine()
    print(f"Engine Dialect: {engine.dialect.name}")
    
    with engine.connect() as conn:
        print("\n=== LIVE DATABASE CONNECTION ===")
        # Check current database info
        if engine.dialect.name == "postgresql":
            db_info = conn.execute(text("SELECT current_database(), current_user, version();")).fetchone()
            print(f"Connected to DB: {db_info[0]}")
            print(f"Current DB User: {db_info[1]}")
            print(f"PostgreSQL Version: {db_info[2][:60]}...")
        else:
            print(f"Non-postgres dialect: {engine.dialect.name}")
            
        # Check Alembic version
        print("\n=== ALEMBIC REVISION ===")
        try:
            alembic_rev = conn.execute(text("SELECT version_num FROM alembic_version;")).fetchall()
            print(f"alembic_version: {[r[0] for r in alembic_rev]}")
        except Exception as e:
            print(f"Error querying alembic_version: {e}")

        # Check accounts table columns
        print("\n=== ACCOUNTS TABLE INSPECTION ===")
        inspector = inspect(conn)
        tables = inspector.get_table_names()
        print(f"Tables count: {len(tables)}")
        crm_tables = [t for t in tables if "lead" in t or "account" in t or "contact" in t or "opp" in t]
        print(f"Relevant CRM tables: {crm_tables}")
        
        if "accounts" in tables:
            columns = inspector.get_columns("accounts")
            col_names = [c["name"] for c in columns]
            has_site_name = "site_name" in col_names
            print(f"accounts has 'site_name': {has_site_name}")
            if has_site_name:
                site_name_col = next(c for c in columns if c["name"] == "site_name")
                print(f"site_name column details: {site_name_col}")
            print(f"All accounts columns: {col_names}")
        else:
            print("Table 'accounts' does NOT exist in database!")

        # Check record counts
        print("\n=== CRM RECORD COUNTS ===")
        for tbl in ["leads", "accounts", "contacts", "opportunities", "crm_opportunities"]:
            if tbl in tables:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl};")).scalar()
                print(f"Table '{tbl}': {cnt} records")
            else:
                print(f"Table '{tbl}': [table does not exist]")

if __name__ == "__main__":
    check_db()
