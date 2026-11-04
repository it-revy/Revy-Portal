"""unified_lead_nurturing_and_timeline

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-11-02 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'q4r5s6t7u8v9'
down_revision = 'p3q4r5s6t7u8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    tables = inspector.get_table_names()

    # 1. Enhance lead_communications table
    if 'lead_communications' in tables:
        comm_cols = [c['name'] for c in inspector.get_columns('lead_communications')]

        if 'interaction_source' not in comm_cols:
            if is_sqlite:
                with op.batch_alter_table('lead_communications') as batch_op:
                    batch_op.add_column(sa.Column('interaction_source', sa.String(length=50), nullable=False, server_default='Manual'))
            else:
                op.add_column('lead_communications', sa.Column('interaction_source', sa.String(length=50), nullable=False, server_default='Manual'))

        if 'subject' not in comm_cols:
            if is_sqlite:
                with op.batch_alter_table('lead_communications') as batch_op:
                    batch_op.add_column(sa.Column('subject', sa.String(length=255), nullable=True))
            else:
                op.add_column('lead_communications', sa.Column('subject', sa.String(length=255), nullable=True))

        if 'updated_at' not in comm_cols:
            if is_sqlite:
                with op.batch_alter_table('lead_communications') as batch_op:
                    batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
            else:
                op.add_column('lead_communications', sa.Column('updated_at', sa.DateTime(), nullable=True))

        if 'nurturing_activity_id' not in comm_cols:
            if is_sqlite:
                with op.batch_alter_table('lead_communications') as batch_op:
                    batch_op.add_column(sa.Column('nurturing_activity_id', sa.String(length=36), nullable=True))
                    batch_op.create_foreign_key(
                        'fk_lead_comms_nurturing_act',
                        'crm_nurturing_activities',
                        ['nurturing_activity_id'],
                        ['id'],
                        ondelete='SET NULL'
                    )
                    batch_op.create_unique_constraint('uq_lead_comms_nurturing_act', ['nurturing_activity_id'])
            else:
                op.add_column('lead_communications', sa.Column('nurturing_activity_id', sa.String(length=36), nullable=True))
                op.create_foreign_key(
                    'fk_lead_comms_nurturing_act',
                    'lead_communications',
                    'crm_nurturing_activities',
                    ['nurturing_activity_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
                op.create_unique_constraint('uq_lead_comms_nurturing_act', 'lead_communications', ['nurturing_activity_id'])

        # Indexes on lead_communications
        existing_indexes = [ix['name'] for ix in inspector.get_indexes('lead_communications')]
        if 'ix_lead_comms_source' not in existing_indexes:
            op.create_index('ix_lead_comms_source', 'lead_communications', ['lead_id', 'interaction_source'])

    # 2. Add Unique constraint on crm_lead_nurturing(lead_id) if not present
    if 'crm_lead_nurturing' in tables:
        nurturing_uqs = [uq['name'] for uq in inspector.get_unique_constraints('crm_lead_nurturing')]
        if 'uq_crm_lead_nurturing_lead_id' not in nurturing_uqs:
            if is_sqlite:
                with op.batch_alter_table('crm_lead_nurturing') as batch_op:
                    batch_op.create_unique_constraint('uq_crm_lead_nurturing_lead_id', ['lead_id'])
            else:
                op.create_unique_constraint('uq_crm_lead_nurturing_lead_id', 'crm_lead_nurturing', ['lead_id'])


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    tables = inspector.get_table_names()

    if 'lead_communications' in tables:
        comm_cols = [c['name'] for c in inspector.get_columns('lead_communications')]
        if is_sqlite:
            with op.batch_alter_table('lead_communications') as batch_op:
                if 'nurturing_activity_id' in comm_cols:
                    batch_op.drop_constraint('uq_lead_comms_nurturing_act', type_='unique')
                    batch_op.drop_constraint('fk_lead_comms_nurturing_act', type_='foreignkey')
                    batch_op.drop_column('nurturing_activity_id')
                if 'subject' in comm_cols:
                    batch_op.drop_column('subject')
                if 'interaction_source' in comm_cols:
                    batch_op.drop_column('interaction_source')
                if 'updated_at' in comm_cols:
                    batch_op.drop_column('updated_at')
        else:
            if 'nurturing_activity_id' in comm_cols:
                op.drop_constraint('uq_lead_comms_nurturing_act', 'lead_communications', type_='unique')
                op.drop_constraint('fk_lead_comms_nurturing_act', 'lead_communications', type_='foreignkey')
                op.drop_column('lead_communications', 'nurturing_activity_id')
            if 'subject' in comm_cols:
                op.drop_column('lead_communications', 'subject')
            if 'interaction_source' in comm_cols:
                op.drop_column('lead_communications', 'interaction_source')
            if 'updated_at' in comm_cols:
                op.drop_column('lead_communications', 'updated_at')

