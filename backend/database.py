"""
Database Configuration and Session Management for CampaignIQ
PS-8 Banking Call Center Intelligence System
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# Directory paths
BACKEND_DIR = Path(__file__).resolve().parent
DB_PATH = BACKEND_DIR / "campaigniq.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Create engine (check_same_thread=False is required for SQLite with multi-threaded Flask)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

# Scoped session for thread-safe database access in Flask
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()


def get_db():
    """
    Context generator or helper to acquire a database session.
    Ensures session is closed after request processing.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initializes all database tables registered with Base metadata.
    Safe to call repeatedly; will not overwrite existing tables.
    """
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully at:", DB_PATH)
