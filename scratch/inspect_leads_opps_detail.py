import os
import sys
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.abspath("backend"))
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("=== 15 QUALIFIED LEADS ===")
    res = conn.execute(text("""
        SELECT l.id, l.lead_id, l.company_name, l.lifecycle_status, l.opportunity_id, o.opportunity_id as opp_code, o.stage, o.status as opp_status
        FROM leads l
        LEFT JOIN crm_opportunities o ON l.opportunity_id = o.id
        WHERE l.lifecycle_status = 'Qualified'
        ORDER BY l.lead_id;
    """)).fetchall()
    for row in res:
        print(f"  {row[1]}: {row[2]} | opp_fk: {row[4]} (Opp Code: {row[5]}, Stage: {row[6]}, Status: {row[7]})")

    print("\n=== SAMPLE OF 24 OPEN LEADS ===")
    res = conn.execute(text("""
        SELECT lead_id, company_name, lifecycle_status, requested_product_service, created_at
        FROM leads
        WHERE lifecycle_status = 'Open'
        ORDER BY lead_id
        LIMIT 10;
    """)).fetchall()
    for row in res:
        print(f"  {row[0]}: {row[1]} | req: {row[3]} | created: {row[4]}")

    print("\n=== OPPORTUNITY STAGES IN DETAIL ===")
    res = conn.execute(text("""
        SELECT opportunity_id, name, stage, status, originating_lead_id
        FROM crm_opportunities
        ORDER BY opportunity_id;
    """)).fetchall()
    for row in res:
        print(f"  {row[0]}: {row[1]} | Stage: {row[2]} | Status: {row[3]} | Originating Lead: {row[4]}")
