"""add opportunity_id to lead_communications and client_name to breakfast_orders

Revision ID: y2z3a4b5c6d7
Revises: x1y2z3a4b5c6
Create Date: 2026-11-14 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'y2z3a4b5c6d7'
down_revision: Union[str, None] = 'x1y2z3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    tables = inspector.get_table_names()

    # 1. lead_communications: add opportunity_id and FK/Index
    if 'lead_communications' in tables:
        comm_cols = [c['name'] for c in inspector.get_columns('lead_communications')]
        existing_indexes = [ix['name'] for ix in inspector.get_indexes('lead_communications')]

        if 'opportunity_id' not in comm_cols:
            if is_sqlite:
                with op.batch_alter_table('lead_communications') as batch_op:
                    batch_op.add_column(sa.Column('opportunity_id', sa.String(length=36), nullable=True))
                    if 'crm_opportunities' in tables:
                        batch_op.create_foreign_key(
                            'fk_lead_comms_opportunity_id',
                            'crm_opportunities',
                            ['opportunity_id'],
                            ['id'],
                            ondelete='CASCADE'
                        )
                    batch_op.create_index('ix_lead_comms_opportunity_id', ['opportunity_id'])
            else:
                op.add_column('lead_communications', sa.Column('opportunity_id', sa.String(length=36), nullable=True))
                if 'crm_opportunities' in tables:
                    op.create_foreign_key(
                        'fk_lead_comms_opportunity_id',
                        'lead_communications',
                        'crm_opportunities',
                        ['opportunity_id'],
                        ['id'],
                        ondelete='CASCADE'
                    )
                if 'ix_lead_comms_opportunity_id' not in existing_indexes:
                    op.create_index('ix_lead_comms_opportunity_id', 'lead_communications', ['opportunity_id'])
        else:
            if not is_sqlite and 'ix_lead_comms_opportunity_id' not in existing_indexes:
                op.create_index('ix_lead_comms_opportunity_id', 'lead_communications', ['opportunity_id'])

    # 2. breakfast_orders: add client_name
    if 'breakfast_orders' in tables:
        order_cols = [c['name'] for c in inspector.get_columns('breakfast_orders')]
        if 'client_name' not in order_cols:
            if is_sqlite:
                with op.batch_alter_table('breakfast_orders') as batch_op:
                    batch_op.add_column(sa.Column('client_name', sa.String(length=255), nullable=True))
            else:
                op.add_column('breakfast_orders', sa.Column('client_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    tables = inspector.get_table_names()

    if 'breakfast_orders' in tables:
        order_cols = [c['name'] for c in inspector.get_columns('breakfast_orders')]
        if 'client_name' in order_cols:
            if is_sqlite:
                with op.batch_alter_table('breakfast_orders') as batch_op:
                    batch_op.drop_column('client_name')
            else:
                op.drop_column('breakfast_orders', 'client_name')

    if 'lead_communications' in tables:
        comm_cols = [c['name'] for c in inspector.get_columns('lead_communications')]
        if 'opportunity_id' in comm_cols:
            if is_sqlite:
                with op.batch_alter_table('lead_communications') as batch_op:
                    batch_op.drop_index('ix_lead_comms_opportunity_id')
                    try:
                        batch_op.drop_constraint('fk_lead_comms_opportunity_id', type_='foreignkey')
                    except Exception:
                        pass
                    batch_op.drop_column('opportunity_id')
            else:
                try:
                    op.drop_index('ix_lead_comms_opportunity_id', table_name='lead_communications')
                except Exception:
                    pass
                try:
                    op.drop_constraint('fk_lead_comms_opportunity_id', 'lead_communications', type_='foreignkey')
                except Exception:
                    pass
                op.drop_column('lead_communications', 'opportunity_id')
