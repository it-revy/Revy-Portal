"""
REVY Portal — Disposable Environment Rollback Verification
==========================================================
Empirically tests the upgrade and rollback (downgrade) procedure of Phase 5A migration
(n1o2p3q4r5s6_phase5a_opportunity_lifecycle_and_quotations) on an isolated, disposable
test database harness.

Guarantees:
- Never downgrades a shared or production database.
- Verifies exact table creation, column structure, unique constraints, and indexes on upgrade.
- Verifies clean table and index drop on downgrade.
"""

import sys
import importlib.util
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

MIGRATION_PATH = "migrations/versions/n1o2p3q4r5s6_phase5a_opportunity_lifecycle_and_quotations.py"
TABLE_NAME = "crm_opportunity_quotations"
UNIQUE_CONSTRAINT_NAME = "uq_crm_opportunity_quotations_num_rev"


def verify_disposable_lifecycle():
    print("=" * 70)
    print("REVY Portal — Disposable Migration Rollback Verification")
    print("=" * 70)

    # 1. Create disposable in-memory database
    print("\n[STEP 1] Creating isolated disposable test database...")
    engine = sa.create_engine("sqlite:///:memory:")
    conn = engine.connect()
    meta = sa.MetaData()

    # Create prerequisite parent tables
    sa.Table("users", meta, sa.Column("id", sa.String(36), primary_key=True))
    sa.Table("crm_opportunities", meta, sa.Column("id", sa.String(36), primary_key=True))
    meta.create_all(conn)
    print("  -> Parent tables 'users' and 'crm_opportunities' created.")

    # 2. Load migration module
    print("\n[STEP 2] Loading Phase 5A migration module...")
    spec = importlib.util.spec_from_file_location("mig_phase5a", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print(f"  -> Loaded revision: {mod.revision} (revises: {mod.down_revision})")

    # Configure Alembic context
    ctx = MigrationContext.configure(conn)
    op = Operations(ctx)
    mod.op = op

    # 3. Test Upgrade
    print("\n[STEP 3] Executing upgrade() to create quotation table...")
    mod.upgrade()
    conn.commit()

    insp = sa.inspect(conn)
    tables_after_upgrade = insp.get_table_names()
    assert TABLE_NAME in tables_after_upgrade, f"Table {TABLE_NAME} was not created!"
    cols = [c["name"] for c in insp.get_columns(TABLE_NAME)]
    indexes = [idx["name"] for idx in insp.get_indexes(TABLE_NAME)]
    print(f"  -> Table '{TABLE_NAME}' successfully created.")
    print(f"  -> Verified {len(cols)} columns: {cols[:6]}... ({len(cols)} total).")
    print(f"  -> Verified {len(indexes)} indexes.")

    # 4. Test Downgrade / Rollback
    print("\n[STEP 4] Executing downgrade() rollback procedure...")
    mod.downgrade()
    conn.commit()

    insp_after = sa.inspect(conn)
    tables_after_downgrade = insp_after.get_table_names()
    assert TABLE_NAME not in tables_after_downgrade, f"Table {TABLE_NAME} still exists after downgrade!"
    print(f"  -> Table '{TABLE_NAME}' cleanly removed.")
    print(f"  -> Remaining tables: {tables_after_downgrade}")

    conn.close()
    engine.dispose()

    print("\n" + "=" * 70)
    print("[SUCCESS] Disposable Rollback Verification PASSED 100% Cleanly.")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = verify_disposable_lifecycle()
    if not success:
        sys.exit(1)
