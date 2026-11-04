import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import app.models
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    sql = """
    SELECT pid, state, query_start, now() - query_start AS duration, query 
    FROM pg_stat_activity 
    WHERE query NOT LIKE '%pg_stat_activity%' AND state != 'idle';
    """
    rows = db.execute(text(sql)).fetchall()
    print("Non-idle connections in Neon:", len(rows))
    for r in rows:
        print(f"PID: {r[0]}, State: {r[1]}, Duration: {r[3]}, Query: {r[4][:80] if r[4] else None}")
        # Terminate any hung idle in transaction
        if "idle in transaction" in str(r[1]).lower():
            print(f"Terminating hung PID {r[0]}...")
            db.execute(text(f"SELECT pg_terminate_backend({r[0]})"))
            db.commit()
finally:
    db.close()

