import sys
from sqlalchemy import create_engine, inspect
from app.core.config import settings
from app.core.database import Base
import app.models  # Register all models

def audit_schema():
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    print(f"Connected to DB: {engine.url.render_as_string(hide_password=True)}")
    print(f"Total tables in DB: {len(db_tables)}")
    print(f"Total model tables in Base.metadata: {len(Base.metadata.tables)}")

    missing_tables = []
    missing_columns = []
    audit_summary = []

    for table_name, table in sorted(Base.metadata.tables.items()):
        if table_name not in db_tables:
            missing_tables.append(table_name)
            print(f"[MISSING TABLE] {table_name}")
            continue

        db_cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        table_missing_cols = []

        for col in table.columns:
            if col.name not in db_cols:
                table_missing_cols.append({
                    "table": table_name,
                    "model_field": col.name,
                    "expected_type": str(col.type),
                    "nullable": col.nullable,
                    "default": str(col.default.arg) if col.default is not None else None,
                    "status": "MISSING"
                })
                missing_columns.append((table_name, col.name))
            else:
                db_col = db_cols[col.name]
                audit_summary.append({
                    "table": table_name,
                    "column": col.name,
                    "model_type": str(col.type),
                    "db_type": str(db_col["type"]),
                    "model_nullable": col.nullable,
                    "db_nullable": db_col["nullable"],
                    "status": "OK"
                })

        if table_missing_cols:
            print(f"[TABLE {table_name}] Missing columns: {[c['model_field'] for c in table_missing_cols]}")

    print("\n" + "="*60)
    print("AUDIT RESULTS SUMMARY:")
    print(f"Total Tables Checked: {len(Base.metadata.tables)}")
    print(f"Missing Tables: {len(missing_tables)}")
    print(f"Missing Columns: {len(missing_columns)}")
    print("="*60)

    if missing_tables:
        print("\nMissing Tables Details:")
        for t in missing_tables:
            print(f"  - {t}")

    if missing_columns:
        print("\nMissing Columns Details:")
        for t, c in missing_columns:
            print(f"  - {t}.{c}")
        return False
    else:
        print("\nPERFECT MATCH: 100% of all model tables and columns exist in the database!")
        return True

if __name__ == "__main__":
    success = audit_schema()
    sys.exit(0 if success else 1)
