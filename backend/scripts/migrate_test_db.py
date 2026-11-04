import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "test_isolated_suite.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(lead_communications)")
cols = [c[1] for c in cursor.fetchall()]

if "subject" not in cols:
    cursor.execute("ALTER TABLE lead_communications ADD COLUMN subject VARCHAR(255)")
    print("Added subject column")

if "interaction_source" not in cols:
    cursor.execute("ALTER TABLE lead_communications ADD COLUMN interaction_source VARCHAR(50) DEFAULT 'Manual'")
    print("Added interaction_source column")

if "nurturing_activity_id" not in cols:
    cursor.execute("ALTER TABLE lead_communications ADD COLUMN nurturing_activity_id VARCHAR(36)")
    print("Added nurturing_activity_id column")

if "updated_at" not in cols:
    cursor.execute("ALTER TABLE lead_communications ADD COLUMN updated_at TIMESTAMP")
    print("Added updated_at column")

conn.commit()
conn.close()
print("Migration of test_isolated_suite.db completed!")

conftest_path = os.path.join(os.path.dirname(__file__), "..", "tests", "conftest.py")
with open(conftest_path, "r", encoding="utf-8") as f:
    code = f.read()

target = '            acc_cols = conn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()'
replacement = '''            comm_cols = conn.exec_driver_sql("PRAGMA table_info(lead_communications)").fetchall()
            if comm_cols and not any(c[1] == 'subject' for c in comm_cols):
                conn.exec_driver_sql("ALTER TABLE lead_communications ADD COLUMN subject VARCHAR(255)")
            if comm_cols and not any(c[1] == 'interaction_source' for c in comm_cols):
                conn.exec_driver_sql("ALTER TABLE lead_communications ADD COLUMN interaction_source VARCHAR(50) DEFAULT 'Manual'")
            if comm_cols and not any(c[1] == 'nurturing_activity_id' for c in comm_cols):
                conn.exec_driver_sql("ALTER TABLE lead_communications ADD COLUMN nurturing_activity_id VARCHAR(36)")
            if comm_cols and not any(c[1] == 'updated_at' for c in comm_cols):
                conn.exec_driver_sql("ALTER TABLE lead_communications ADD COLUMN updated_at TIMESTAMP")
            conn.commit()

            acc_cols = conn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()'''

if target in code:
    code = code.replace(target, replacement, 1)
    with open(conftest_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("Updated conftest.py successfully!")
else:
    print("Target not found in conftest.py!")

