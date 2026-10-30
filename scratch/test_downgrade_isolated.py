import sys, os
sys.path.insert(0, ".")
import app.main
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

isolated_sqlite_url = "sqlite:///isolated_test.db"
alembic_cfg = Config("alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", isolated_sqlite_url)
alembic_cfg.cmd_opts = type("CmdOpts", (), {"x": [f"sqlalchemy.url={isolated_sqlite_url}"]})()

print("Testing downgrade logic on isolated database...")
try:
    # Upgrade to head
    command.upgrade(alembic_cfg, "head")
    print("Isolated upgrade succeeded.")
    
    # Test downgrade to l9m0n1o2p3q4
    command.downgrade(alembic_cfg, "l9m0n1o2p3q4")
    print("Isolated downgrade to l9m0n1o2p3q4 succeeded.")
    
    # Re-upgrade to head
    command.upgrade(alembic_cfg, "head")
    print("Isolated re-upgrade to head succeeded.")
finally:
    if os.path.exists("isolated_test.db"):
        os.remove("isolated_test.db")
print("Isolated downgrade verification complete!")
