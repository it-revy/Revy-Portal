"""add account site_name

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2026-10-24 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'k8l9m0n1o2p3'
down_revision = 'j7k8l9m0n1o2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    if 'accounts' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('accounts')]
        if 'site_name' not in cols:
            if is_sqlite:
                with op.batch_alter_table('accounts') as batch_op:
                    batch_op.add_column(sa.Column('site_name', sa.String(length=255), nullable=True))
            else:
                op.add_column('accounts', sa.Column('site_name', sa.String(length=255), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = inspector.get_table_names()

    if 'accounts' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('accounts')]
        if 'site_name' in cols:
            if is_sqlite:
                with op.batch_alter_table('accounts') as batch_op:
                    batch_op.drop_column('site_name')
            else:
                op.drop_column('accounts', 'site_name')
