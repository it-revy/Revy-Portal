import sys, os, tempfile
sys.path.insert(0, ".")
import app.main
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

test_db_path = os.path.abspath("scratch/isolated_migration_test.db")
if os.path.exists(test_db_path):
    os.remove(test_db_path)

test_url = f"sqlite:///{test_db_path}"
print(f"Testing migration on isolated SQLite DB: {test_url}")

# Setup Alembic Config pointing to isolated DB
alembic_cfg = Config("alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", test_url)

print("1. Running alembic upgrade head on isolated DB...")
command.upgrade(alembic_cfg, "head")

engine = create_engine(test_url)
with engine.connect() as conn:
    # Check current revision in alembic_version table
    cur_rev = conn.execute(text("SELECT version_num FROM alembic_version;")).scalar()
    print(f"Current revision in isolated DB: {cur_rev}")
    assert cur_rev == "m0n1o2p3q4r5", f"Expected m0n1o2p3q4r5, got {cur_rev}"

    # Check table info
    cols = conn.execute(text("PRAGMA table_info(leads);")).fetchall()
    status_col = next((c for c in cols if c[1] == "lifecycle_status"), None)
    print(f"lifecycle_status column info: {status_col}")
    # Default should be Enquiry
    assert "Enquiry" in str(status_col[4]), f"Expected Enquiry server_default, got {status_col[4]}"

print("2. Testing downgrade to l9m0n1o2p3q4...")
command.downgrade(alembic_cfg, "l9m0n1o2p3q4")

with engine.connect() as conn:
    down_rev = conn.execute(text("SELECT version_num FROM alembic_version;")).scalar()
    print(f"Revision after downgrade: {down_rev}")
    assert down_rev == "l9m0n1o2p3q4"

print("3. Re-running upgrade head...")
command.upgrade(alembic_cfg, "head")

with engine.connect() as conn:
    final_rev = conn.execute(text("SELECT version_num FROM alembic_version;")).scalar()
    print(f"Revision after re-upgrade: {final_rev}")
    assert final_rev == "m0n1o2p3q4r5"

print("Isolated migration and downgrade test PASSED 100%!")
engine.dispose()
if os.path.exists(test_db_path):
    os.remove(test_db_path)
