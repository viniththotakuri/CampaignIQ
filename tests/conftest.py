"""
Pytest Configuration & Fixtures for CampaignIQ
PS-8 Banking Call Center Intelligence System
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure isolated temporary SQLite database for test execution
temp_dir = tempfile.gettempdir()
test_db_path = Path(temp_dir) / "campaigniq_test_isolated.db"
if test_db_path.exists():
    try:
        test_db_path.unlink()
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.resolve()}"

# Ensure backend directory is in Python path for all tests
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app
from database import SessionLocal, init_db, engine
from seed_data import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Initializes tables and seeds test benchmark data in isolated test database."""
    init_db()
    seed_database()
    yield
    # Clean up test database after all tests complete
    engine.dispose()
    try:
        if test_db_path.exists():
            test_db_path.unlink()
    except Exception:
        pass


@pytest.fixture
def client():
    """Provides Flask test client with test context."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def db_session():
    """Provides isolated database session for tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
