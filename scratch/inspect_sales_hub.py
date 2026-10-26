import os
import sys
from collections import Counter
from sqlalchemy import create_engine, text

# Load config
sys.path.insert(0, os.path.abspath("backend"))
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("=== DATABASE CONNECTION ===")
    print("Host:", engine.url.host)
    print("Database:", engine.url.database)

    print("\n=== LEADS LIFECYCLE STATUS COUNTS ===")
    res = conn.execute(text("SELECT lifecycle_status, count(*) FROM leads GROUP BY lifecycle_status;")).fetchall()
    for row in res:
        print(f"  lifecycle_status: '{row[0]}' -> count: {row[1]}")

    print("\n=== LEADS OPPORTUNITY_ID USAGE ===")
    res = conn.execute(text("SELECT count(*) FROM leads WHERE opportunity_id IS NOT NULL;")).scalar()
    total_leads = conn.execute(text("SELECT count(*) FROM leads;")).scalar()
    print(f"  Leads with opportunity_id set: {res} / {total_leads}")

    print("\n=== OPPORTUNITIES ORIGINATING_LEAD_ID USAGE ===")
    res = conn.execute(text("SELECT count(*) FROM crm_opportunities WHERE originating_lead_id IS NOT NULL;")).scalar()
    total_opps = conn.execute(text("SELECT count(*) FROM crm_opportunities;")).scalar()
    print(f"  Opportunities with originating_lead_id set: {res} / {total_opps}")

    print("\n=== OPPORTUNITY STAGES & STATUSES ===")
    res = conn.execute(text("SELECT stage, status, count(*) FROM crm_opportunities GROUP BY stage, status;")).fetchall()
    for row in res:
        print(f"  stage: '{row[0]}', status: '{row[1]}' -> count: {row[2]}")

    print("\n=== COLUMNS IN LEADS ===")
    res = conn.execute(text("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'leads' 
        ORDER BY ordinal_position;
    """)).fetchall()
    for row in res:
        print(f"  {row[0]} ({row[1]}, nullable={row[2]})")

    print("\n=== COLUMNS IN CRM_OPPORTUNITIES ===")
    res = conn.execute(text("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'crm_opportunities' 
        ORDER BY ordinal_position;
    """)).fetchall()
    for row in res:
        print(f"  {row[0]} ({row[1]}, nullable={row[2]})")
