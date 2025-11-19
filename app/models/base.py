"""Base model and database setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# SQLAlchemy base class
Base = declarative_base()

# Database engine - will be initialized by app factory
engine = None
SessionLocal = None


def init_db(database_url: str) -> None:
    """
    Initialize database engine and session factory.

    Args:
        database_url: Database connection URL (PostgreSQL or SQLite)
    """
    global engine, SessionLocal

    # SQLite doesn't support pool_size and max_overflow parameters
    if database_url.startswith('sqlite'):
        engine = create_engine(
            database_url,
            connect_args={'check_same_thread': False},
            echo=settings.is_development,
        )
    else:
        # PostgreSQL configuration
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=settings.is_development,
        )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )


def get_db():
    """
    Get database session.

    Yields:
        Database session

    Usage:
        with get_db() as db:
            # Use db session
            pass
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db first.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
