import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import app.models
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    sql = """
    SELECT pid, state, query_start, now() - query_start AS duration, wait_event_type, wait_event, query 
    FROM pg_stat_activity 
    WHERE query NOT LIKE '%pg_stat_activity%';
    """
    rows = db.execute(text(sql)).fetchall()
    print("Total connections in Neon:", len(rows))
    for r in rows:
        print(f"PID: {r[0]}, State: {r[1]}, Wait: {r[4]}/{r[5]}, Duration: {r[3]}, Query: {r[6][:100] if r[6] else None}")
finally:
    db.close()

