"""Add PI Issued opportunity stage and stage transition history

Revision ID: z3a4b5c6d7e8
Revises: y2z3a4b5c6d7
Create Date: 2026-11-16 00:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'z3a4b5c6d7e8'
down_revision: Union[str, None] = 'y2z3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPROVED_OPPORTUNITY_STAGES = (
    'Enquiry',
    'Offer',
    'Negotiation',
    'PI Issued',
    'Supply',
    'Payment',
    'Dormant'
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    tables = inspector.get_table_names()

    # 1. Update check constraint on crm_opportunities
    if 'crm_opportunities' in tables:
        opp_stages_sql = ", ".join([f"'{s}'" for s in APPROVED_OPPORTUNITY_STAGES])
        if is_sqlite:
            with op.batch_alter_table('crm_opportunities') as batch_op:
                try:
                    batch_op.drop_constraint('ck_crm_opportunities_stage', type_='check')
                except Exception:
                    pass
                batch_op.create_check_constraint('ck_crm_opportunities_stage', f"stage IN ({opp_stages_sql})")
        else:
            op.execute(sa.text("ALTER TABLE crm_opportunities DROP CONSTRAINT IF EXISTS ck_crm_opportunities_stage;"))
            op.create_check_constraint(
                'ck_crm_opportunities_stage',
                'crm_opportunities',
                f"stage IN ({opp_stages_sql})"
            )

    # 2. Create crm_opportunity_stage_history table
    if 'crm_opportunity_stage_history' not in tables:
        op.create_table(
            'crm_opportunity_stage_history',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('previous_stage', sa.String(length=50), nullable=True),
            sa.Column('new_stage', sa.String(length=50), nullable=False),
            sa.Column('triggering_event', sa.String(length=100), nullable=False),
            sa.Column('triggering_user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('triggering_user_name', sa.String(length=255), nullable=True),
            sa.Column('remarks', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_crm_opp_stage_hist_opp_id', 'crm_opportunity_stage_history', ['opportunity_id'])
        op.create_index('ix_crm_opp_stage_hist_new_stage', 'crm_opportunity_stage_history', ['new_stage'])
        op.create_index('ix_crm_opp_stage_hist_event', 'crm_opportunity_stage_history', ['triggering_event'])
        op.create_index('ix_crm_opp_stage_hist_created_at', 'crm_opportunity_stage_history', ['created_at'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    tables = inspector.get_table_names()

    if 'crm_opportunity_stage_history' in tables:
        op.drop_table('crm_opportunity_stage_history')

    PREVIOUS_OPPORTUNITY_STAGES = (
        'Enquiry',
        'Offer',
        'Negotiation',
        'Supply',
        'Payment',
        'Dormant'
    )
    if 'crm_opportunities' in tables:
        opp_stages_sql = ", ".join([f"'{s}'" for s in PREVIOUS_OPPORTUNITY_STAGES])
        if is_sqlite:
            with op.batch_alter_table('crm_opportunities') as batch_op:
                try:
                    batch_op.drop_constraint('ck_crm_opportunities_stage', type_='check')
                except Exception:
                    pass
                batch_op.create_check_constraint('ck_crm_opportunities_stage', f"stage IN ({opp_stages_sql})")
        else:
            op.execute(sa.text("ALTER TABLE crm_opportunities DROP CONSTRAINT IF EXISTS ck_crm_opportunities_stage;"))
            op.create_check_constraint(
                'ck_crm_opportunities_stage',
                'crm_opportunities',
                f"stage IN ({opp_stages_sql})"
            )
