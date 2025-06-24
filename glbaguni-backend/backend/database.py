"""
Database configuration and session management for glbaguni app.
"""

import logging
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./glbaguni.db")

# Create engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL debugging
    )

    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    # PostgreSQL/MySQL configuration
    engine = create_engine(DATABASE_URL, echo=False)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Database dependency for FastAPI
def get_db():
    """
    Database dependency for FastAPI endpoints.
    Provides a database session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables.
    This should be called during application startup.
    """
    try:
        from .models import Base
    except ImportError:
        from models import Base
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def init_database():
    """
    Initialize database with tables and basic data.
    """
    logger.info("Initializing database...")
    create_tables()
    logger.info("Database initialization completed")


# Utility functions for database operations
def get_or_create_user_preferences(db, user_id: str, preferred_language: str = "en"):
    """
    Get or create user preferences for a given user_id.
    """
    try:
        from .models import UserPreferences
    except ImportError:
        from models import UserPreferences

    preferences = (
        db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    )
    if not preferences:
        preferences = UserPreferences(
            user_id=user_id,
            preferred_language=preferred_language,
            preferred_categories="[]",  # Empty JSON array
            email_notifications=True,
        )
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

    return preferences
