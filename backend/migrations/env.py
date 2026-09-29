import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from alembic import context

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    # Check -x argument first
    x_args = context.get_x_argument(as_dictionary=True)
    if "sqlalchemy.url" in x_args:
        return x_args["sqlalchemy.url"]
    
    # Check env var or settings
    url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    return url

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    
    try:
        connectable = create_engine(url, poolclass=pool.NullPool, connect_args=connect_args)
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata
            )
            with context.begin_transaction():
                context.run_migrations()
    except Exception as e:
        # If postgres fails in local dev without postgres credentials, fallback to sqlite
        if url.startswith("postgresql"):
            fallback_url = settings.FALLBACK_SQLITE_URL
            print(f"[Alembic] Connection to PostgreSQL failed ({e}). Using fallback: {fallback_url}")
            connectable = create_engine(fallback_url, poolclass=pool.NullPool, connect_args={"check_same_thread": False})
            with connectable.connect() as connection:
                context.configure(
                    connection=connection,
                    target_metadata=target_metadata
                )
                with context.begin_transaction():
                    context.run_migrations()
        else:
            raise e


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
