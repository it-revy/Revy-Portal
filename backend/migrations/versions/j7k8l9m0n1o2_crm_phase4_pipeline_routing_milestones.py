"""crm phase 4 opportunity pipeline, requirement routing, and milestones

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2026-10-24 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'j7k8l9m0n1o2'
down_revision = 'i6j7k8l9m0n1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    # 1. Update crm_opportunities table with pipeline stage and attributes
    if 'crm_opportunities' in existing_tables:
        opp_cols = [c['name'] for c in inspector.get_columns('crm_opportunities')]
        cols_to_add = [
            ('stage', sa.Column('stage', sa.String(length=50), nullable=False, server_default='Qualify')),
            ('loss_reason', sa.Column('loss_reason', sa.Text(), nullable=True)),
            ('business_area', sa.Column('business_area', sa.String(length=50), nullable=True, server_default='Biogas')),
            ('expected_close_date', sa.Column('expected_close_date', sa.Date(), nullable=True)),
            ('actual_close_date', sa.Column('actual_close_date', sa.DateTime(), nullable=True)),
        ]

        if is_sqlite:
            with op.batch_alter_table('crm_opportunities') as batch_op:
                for col_name, col_def in cols_to_add:
                    if col_name not in opp_cols:
                        batch_op.add_column(col_def)
        else:
            for col_name, col_def in cols_to_add:
                if col_name not in opp_cols:
                    op.add_column('crm_opportunities', col_def)

        existing_indexes = [idx['name'] for idx in inspector.get_indexes('crm_opportunities')]
        if 'ix_crm_opportunities_stage' not in existing_indexes:
            op.create_index('ix_crm_opportunities_stage', 'crm_opportunities', ['stage'], unique=False)
        if 'ix_crm_opportunities_expected_close_date' not in existing_indexes:
            op.create_index('ix_crm_opportunities_expected_close_date', 'crm_opportunities', ['expected_close_date'], unique=False)

    # 2. Add opportunity_id foreign key to downstream tables
    # 2a. crm_consulting_engagements
    if 'crm_consulting_engagements' in existing_tables:
        ce_cols = [c['name'] for c in inspector.get_columns('crm_consulting_engagements')]
        if 'opportunity_id' not in ce_cols:
            if is_sqlite:
                with op.batch_alter_table('crm_consulting_engagements') as batch_op:
                    batch_op.add_column(sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='SET NULL'), nullable=True))
            else:
                op.add_column('crm_consulting_engagements', sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='SET NULL'), nullable=True))
            op.create_index('ix_crm_consulting_engagements_opportunity_id', 'crm_consulting_engagements', ['opportunity_id'], unique=False)

    # 2b. crm_sample_submissions
    if 'crm_sample_submissions' in existing_tables:
        ss_cols = [c['name'] for c in inspector.get_columns('crm_sample_submissions')]
        if 'opportunity_id' not in ss_cols:
            if is_sqlite:
                with op.batch_alter_table('crm_sample_submissions') as batch_op:
                    batch_op.add_column(sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='SET NULL'), nullable=True))
            else:
                op.add_column('crm_sample_submissions', sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='SET NULL'), nullable=True))
            op.create_index('ix_crm_sample_submissions_opportunity_id', 'crm_sample_submissions', ['opportunity_id'], unique=False)

    # 2c. crm_product_transactions
    if 'crm_product_transactions' in existing_tables:
        pt_cols = [c['name'] for c in inspector.get_columns('crm_product_transactions')]
        if 'opportunity_id' not in pt_cols:
            if is_sqlite:
                with op.batch_alter_table('crm_product_transactions') as batch_op:
                    batch_op.add_column(sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='SET NULL'), nullable=True))
            else:
                op.add_column('crm_product_transactions', sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='SET NULL'), nullable=True))
            op.create_index('ix_crm_product_transactions_opportunity_id', 'crm_product_transactions', ['opportunity_id'], unique=False)

    # 3. Create crm_milestones table
    if 'crm_milestones' not in existing_tables:
        op.create_table(
            'crm_milestones',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('milestone_id', sa.String(length=50), nullable=False),
            sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('crm_opportunities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('workstream_type', sa.String(length=50), nullable=True),
            sa.Column('workstream_id', sa.String(length=36), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('planned_start_date', sa.Date(), nullable=True),
            sa.Column('due_date', sa.Date(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='Pending'),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('completion_notes', sa.Text(), nullable=True),
            sa.Column('assigned_to_user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_by_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_crm_milestones_milestone_id', 'crm_milestones', ['milestone_id'], unique=True)
        op.create_index('ix_crm_milestones_opportunity_id', 'crm_milestones', ['opportunity_id'], unique=False)
        op.create_index('ix_crm_milestones_due_date', 'crm_milestones', ['due_date'], unique=False)
        op.create_index('ix_crm_milestones_status', 'crm_milestones', ['status'], unique=False)
        op.create_index('ix_crm_milestones_assigned_to_user_id', 'crm_milestones', ['assigned_to_user_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    # Drop crm_milestones
    if 'crm_milestones' in existing_tables:
        op.drop_table('crm_milestones')

    # Drop opportunity_id from downstream tables
    for tbl in ['crm_product_transactions', 'crm_sample_submissions', 'crm_consulting_engagements']:
        if tbl in existing_tables:
            cols = [c['name'] for c in inspector.get_columns(tbl)]
            indexes = [idx['name'] for idx in inspector.get_indexes(tbl)]
            idx_name = f'ix_{tbl}_opportunity_id'
            if idx_name in indexes:
                op.drop_index(idx_name, table_name=tbl)
            if 'opportunity_id' in cols:
                if is_sqlite:
                    with op.batch_alter_table(tbl) as batch_op:
                        batch_op.drop_column('opportunity_id')
                else:
                    op.drop_column(tbl, 'opportunity_id')

    # Drop added columns from crm_opportunities
    if 'crm_opportunities' in existing_tables:
        opp_cols = [c['name'] for c in inspector.get_columns('crm_opportunities')]
        indexes = [idx['name'] for idx in inspector.get_indexes('crm_opportunities')]
        for idx in ['ix_crm_opportunities_expected_close_date', 'ix_crm_opportunities_stage']:
            if idx in indexes:
                op.drop_index(idx, table_name='crm_opportunities')

        cols_to_drop = ['stage', 'loss_reason', 'business_area', 'expected_close_date', 'actual_close_date']
        if is_sqlite:
            with op.batch_alter_table('crm_opportunities') as batch_op:
                for c in cols_to_drop:
                    if c in opp_cols:
                        batch_op.drop_column(c)
        else:
            for c in cols_to_drop:
                if c in opp_cols:
                    op.drop_column('crm_opportunities', c)
