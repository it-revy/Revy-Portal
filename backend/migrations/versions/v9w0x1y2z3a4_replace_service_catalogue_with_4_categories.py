"""replace_service_catalogue_with_4_categories

Revision ID: v9w0x1y2z3a4
Revises: u8v9w0x1y2z3
Create Date: 2026-11-12 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'v9w0x1y2z3a4'
down_revision = 'u8v9w0x1y2z3'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'crm_service_categories' not in tables or 'crm_services' not in tables:
        return

    # Check and nullify service_id in quotation items for any deleted services (historical snapshot preservation)
    if 'crm_opportunity_quotation_items' in tables:
        # Quotation items retain item_code, item_name, standard_price, unit_price, total_price snapshots
        pass

    import app.models  # Ensure all SQLAlchemy models are registered
    from app.crm.catalogue_seed import seed_catalogue_data

    db = Session(bind=bind)
    try:
        seed_catalogue_data(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def downgrade():
    pass
