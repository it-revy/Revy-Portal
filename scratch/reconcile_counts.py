import sys
from urllib.parse import urlparse
from sqlalchemy import create_engine, text

backend_dir = r"e:\IT Development\REVY Portal\Revy-Portal\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings

# 1. Safe diagnostic without exposing credentials
raw_url = settings.DATABASE_URL
parsed = urlparse(raw_url)
safe_host = parsed.hostname or "unknown"
safe_db = parsed.path.lstrip("/") if parsed.path else "unknown"

print("==================================================")
print("PHASE B & D: SAFE DATABASE & COUNT RECONCILIATION")
print("==================================================")
print(f"Target Database Host: {safe_host}")
print(f"Target Database Name: {safe_db}")
print(f"Connection Protocol: {parsed.scheme}")

eng = create_engine(raw_url)
with eng.connect() as conn:
    # 2. Check Alembic revision
    try:
        rev = conn.execute(text("SELECT version_num FROM alembic_version;")).scalar()
        print(f"Alembic Current Revision: {rev}")
    except Exception as e:
        print(f"Alembic Version Check Failed: {e}")

    # 3. Check accounts.site_name column
    col_check = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'accounts' AND column_name = 'site_name';
    """)).fetchone()
    print(f"Column 'accounts.site_name' exists: {col_check is not None} ({col_check})")

    # 4. Count breakdown of Leads by lifecycle status
    lead_status_counts = conn.execute(text("""
        SELECT lifecycle_status, count(*) 
        FROM leads 
        GROUP BY lifecycle_status 
        ORDER BY lifecycle_status;
    """)).fetchall()
    total_leads = sum(row[1] for row in lead_status_counts)
    print("\n[Leads Count by Lifecycle Status]")
    for st, count in lead_status_counts:
        print(f"  {st}: {count}")
    print(f"  Total Leads in DB: {total_leads}")

    # 5. Accounts, Contacts, Opportunities count
    total_accounts = conn.execute(text("SELECT count(*) FROM accounts;")).scalar()
    total_contacts = conn.execute(text("SELECT count(*) FROM contacts;")).scalar()
    total_opps = conn.execute(text("SELECT count(*) FROM crm_opportunities;")).scalar()
    print(f"\nTotal Accounts in DB: {total_accounts}")
    print(f"Total Contacts in DB: {total_contacts}")
    print(f"Total Opportunities in DB: {total_opps}")

    # 6. Test records inspection (Phase H)
    test_leads = conn.execute(text("""
        SELECT id, lead_id, company_name, first_name, last_name, lifecycle_status, created_at 
        FROM leads 
        WHERE lead_id IN ('LEAD-00030', 'LEAD-00031') 
           OR company_name LIKE '%CleanPower%' 
           OR company_name LIKE '%Test%'
        ORDER BY created_at DESC;
    """)).fetchall()
    print(f"\n[Phase H: Potential Test Leads Identified in Neon ({len(test_leads)})]")
    for tl in test_leads:
        print(f"  Lead: {tl[1]} | Company: {tl[2]} | Contact: {tl[3]} {tl[4]} | Status: {tl[5]} | Created: {tl[6]} | ID: {tl[0]}")

    test_opps = conn.execute(text("""
        SELECT id, opportunity_id, name, stage, status, created_at 
        FROM crm_opportunities 
        WHERE opportunity_id IN ('OPP-00011', 'OPP-00012') 
           OR name LIKE '%CleanPower%'
        ORDER BY created_at DESC;
    """)).fetchall()
    print(f"\n[Phase H: Potential Test Opportunities in Neon ({len(test_opps)})]")
    for to in test_opps:
        print(f"  Opp: {to[1]} | Name: {to[2]} | Stage: {to[3]} | Status: {to[4]} | Created: {to[5]} | ID: {to[0]}")

    test_accounts = conn.execute(text("""
        SELECT id, account_id, name, site_name, created_at 
        FROM accounts 
        WHERE name LIKE '%CleanPower%'
        ORDER BY created_at DESC;
    """)).fetchall()
    print(f"\n[Phase H: Potential Test Accounts in Neon ({len(test_accounts)})]")
    for ta in test_accounts:
        print(f"  Account: {ta[1]} | Name: {ta[2]} | Site: {ta[3]} | Created: {ta[4]} | ID: {ta[0]}")
