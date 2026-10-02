import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("revy.breakfast.db")

Base = declarative_base()

def get_engine():
    db_url = settings.DATABASE_URL
    connect_args = {}
    
    # If using postgresql, handle pool settings
    if db_url.startswith("postgresql"):
        try:
            engine = create_engine(
                db_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=300
            )
            # Test connection
            with engine.connect() as conn:
                logger.info("Successfully connected to PostgreSQL database")
            return engine
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL at {db_url}: {e}")
            logger.info("Falling back to local SQLite database for development/testing")
            db_url = settings.FALLBACK_SQLITE_URL
            connect_args = {"check_same_thread": False}
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

