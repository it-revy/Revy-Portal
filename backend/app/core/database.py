import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("revy.breakfast.db")

Base = declarative_base()

def get_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    connect_args = {}
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    abs_sqlite_path = os.path.join(backend_dir, "breakfast.db").replace("\\", "/")
    fallback_url = f"sqlite:///{abs_sqlite_path}"
    
    # If using postgresql, handle pool settings
    if db_url.startswith("postgresql"):
        engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=300
        )
        logger.info("Connected to PostgreSQL database (Neon)")
        return engine
    elif db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(db_url, connect_args=connect_args)
    return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables in database if not created (useful for tests/quickstart)"""
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

