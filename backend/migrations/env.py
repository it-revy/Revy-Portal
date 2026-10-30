import os
import sys
from urllib.parse import urlparse
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

# Confirmed testing host pattern
KNOWN_TESTING_HOST_PATTERNS = [
    "ep-silent-sound-b49uucbd",
    "ep-silent-sound-b49uucbd-pooler",
]
KNOWN_PRODUCTION_HOST_PATTERNS = [
    "ep-production",
    "prod-db",
    "revy-production"
]


def is_known_production_target(url: str) -> bool:
    """
    Returns True only if the target database resolves to an actual production cluster.
    The ep-silent-sound Neon database is confirmed as the authorized testing environment.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        
        # Explicit testing host check
        for pat in KNOWN_TESTING_HOST_PATTERNS:
            if pat in host:
                return False
                
        for pattern in KNOWN_PRODUCTION_HOST_PATTERNS:
            if pattern in host:
                return True
                
        if os.environ.get("ENVIRONMENT", "").lower() == "production":
            return True
            
        return False
    except Exception:
        return False


def get_url():
    # Check -x argument first
    x_args = context.get_x_argument(as_dictionary=True)
    staging_requested = (
        x_args.get("staging", "").lower() in ("true", "1", "yes") or
        x_args.get("env", "").lower() == "staging" or
        os.environ.get("EXECUTE_STAGING_MIGRATION", "").lower() in ("true", "1")
    )

    if "sqlalchemy.url" in x_args:
        url = x_args["sqlalchemy.url"]
    elif staging_requested:
        url = os.environ.get("STAGING_DATABASE_URL")
        if not url:
            raise RuntimeError(
                "STAGING MIGRATION GUARD: Staging migration explicitly requested (-x staging=true), "
                "but STAGING_DATABASE_URL environment variable is not configured. "
                "Refusing to run migration against default/unconfigured database."
            )
    else:
        # Check env var or settings
        url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # SAFETY GUARD: Refuse to run against known production Neon database without explicit release authorization
    if is_known_production_target(url):
        if staging_requested:
            raise RuntimeError(
                "SAFETY GUARD TRIGGERED: Staging migration target resolves to the KNOWN PRODUCTION DATABASE. "
                "Execution aborted immediately to protect production data."
            )
        allow_prod = os.environ.get("ALLOW_PRODUCTION_MIGRATIONS", "").lower() == "true"
        if not allow_prod:
            raise RuntimeError(
                "PRODUCTION SAFETY GUARD TRIGGERED: The target database resolves to the known production database cluster. "
                "Direct Alembic migrations against production require explicit authorization via ALLOW_PRODUCTION_MIGRATIONS='true'."
            )

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
    
    connectable = create_engine(url, poolclass=pool.NullPool, connect_args=connect_args)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
