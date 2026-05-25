"""
ScholarForge Test Configuration and Fixtures

This module provides pytest fixtures for:
- Database setup and teardown
- FastAPI test client
- Sample data for testing
"""

import os
import pytest
import tempfile
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment variables before importing the app
# Use a temporary SQLite database file instead of in-memory to avoid connection issues
test_db_fd, test_db_path = tempfile.mkstemp(suffix=".db")
os.close(test_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
os.environ["APP_SECRET_KEY"] = "test-secret-key"
os.environ["SCHOLARFORGE_TESTING"] = "1"
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("SERP_KEY", "test-key")
os.environ.setdefault("CELERY_BROKER_URL", "redis://redis:6379/0")

# Import after setting environment
from backend import database
from backend.database import ProjectFolder, ChatSession, ChatMessage, ReportDB, Hook, Base
from backend.main import app


# ============================================================================
# DATABASE SETUP
# ============================================================================

# Create all tables
database.Base.metadata.create_all(bind=database.engine)


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Cleanup test database files at session end."""
    yield
    # Cleanup
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception as e:
        print(f"Failed to cleanup test DB: {e}")


@pytest.fixture
def test_db(monkeypatch):
    """Create a clean database session for each test."""
    # Create a connection
    connection = database.engine.connect()
    
    # Start a transaction
    transaction = connection.begin()
    
    # Create a sessionmaker for this connection with expire_on_commit=False
    # This keeps objects attached and accessible after commit
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        expire_on_commit=False
    )
    test_session = TestSessionLocal()
    
    # Pre-seed the test user to guarantee it has id=1
    from backend.database import UserDB
    test_user = test_session.query(UserDB).filter(UserDB.id == 1).first()
    if not test_user:
        test_user = UserDB(id=1, username="test_user", password_hash="dummy_hash")
        test_session.add(test_user)
        test_session.commit()
    
    # Prevent the session from being closed prematurely during test requests
    original_close = test_session.close
    test_session.close = lambda: None

    # Replace the module-level SessionLocal with our test session factory
    # This ensures all database operations use the test session
    old_sessionlocal_call = database.SessionLocal
    database.SessionLocal = lambda: test_session
    
    # Override the get_db dependency for FastAPI endpoints
    def override_get_db():
        try:
            yield test_session
        finally:
            pass
    
    app.dependency_overrides[database.get_db] = override_get_db
    
    yield test_session
    
    # Cleanup - restore original and rollback
    database.SessionLocal = old_sessionlocal_call
    test_session.close = original_close
    test_session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture
def db_session(test_db):
    """Alias for test_db fixture."""
    return test_db


# ============================================================================
# API CLIENT FIXTURE
# ============================================================================

@pytest.fixture
def client(test_db):
    """Create a FastAPI TestClient with test database."""
    return TestClient(app)


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_folder(test_db):
    """Create a sample project folder."""
    folder = ProjectFolder(name="Test Folder", user_id=1)
    test_db.add(folder)
    test_db.commit()
    test_db.refresh(folder)
    return folder


@pytest.fixture
def sample_session(test_db, sample_folder):
    """Create a sample chat session."""
    session = ChatSession(folder_id=sample_folder.id, title="Test Session")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


@pytest.fixture
def sample_messages(test_db, sample_session):
    """Create sample chat messages."""
    messages = [
        ChatMessage(session_id=sample_session.id, role="user", content="Hello"),
        ChatMessage(session_id=sample_session.id, role="assistant", content="Hi there!"),
        ChatMessage(session_id=sample_session.id, role="user", content="How are you?"),
    ]
    test_db.add_all(messages)
    test_db.commit()
    return messages


@pytest.fixture
def sample_report(test_db):
    """Create a sample report."""
    report = ReportDB(
        topic="Test Report",
        content="# Test Report\n\nThis is a test report.",
        user_id=1
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)
    return report


@pytest.fixture
def sample_hook(test_db):
    """Create a sample hook."""
    hook = Hook(content="This is a test hook with important research notes.", user_id=1)
    test_db.add(hook)
    test_db.commit()
    test_db.refresh(hook)
    return hook


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield f.name
    # Cleanup
    if os.path.exists(f.name):
        os.remove(f.name)


@pytest.fixture
def sample_pdf_bytes():
    """Create minimal PDF bytes for testing (magic bytes only)."""
    # PDF header
    return b"%PDF-1.4\n"


@pytest.fixture
def sample_docx_bytes():
    """Create minimal DOCX bytes for testing (ZIP format with minimal content)."""
    import zipfile
    import io
    
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr('word/document.xml', '<?xml version="1.0"?><root>Test Content</root>')
        zf.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types/>')
    
    return buffer.getvalue()


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
