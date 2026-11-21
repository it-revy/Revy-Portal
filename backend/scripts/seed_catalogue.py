
import logging

import app.models
from app.core.database import SessionLocal
from app.crm.catalogue_seed import seed_catalogue_data

logging.basicConfig(level=logging.INFO)

def main():
    db = SessionLocal()

    try:
        print("Starting CRM catalogue seed...")

        seed_catalogue_data(db)
        db.commit()

        print("SUCCESS: CRM catalogue seed completed.")
        print("4 categories and 61 predefined services processed.")

    except Exception as e:
        db.rollback()
        print(f"ERROR: Catalogue seed failed: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
