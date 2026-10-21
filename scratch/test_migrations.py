import shutil
import os
import sys
import subprocess
import sqlite3

src = "backend/breakfast.db"
dst = "backend/test_migration.db"

if os.path.exists(dst):
    os.remove(dst)

shutil.copy2(src, dst)
print(f"Copied {src} to {dst}")

# Run alembic upgrade head using DATABASE_URL pointing to dst
env = os.environ.copy()
abs_dst = os.path.abspath(dst).replace("\\", "/")
env["DATABASE_URL"] = f"sqlite:///{abs_dst}"

result = subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd="backend",
    env=env,
    capture_output=True,
    text=True
)

print("Alembic exit code:", result.returncode)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)

conn = sqlite3.connect(dst)
cur = conn.cursor()
print("Alembic version in DB:", cur.execute("select * from alembic_version").fetchall())
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Total tables now: {len(tables)}")
conn.close()

# Clean up test_migration.db
if os.path.exists(dst):
    os.remove(dst)
    print("Cleaned up test_migration.db")
