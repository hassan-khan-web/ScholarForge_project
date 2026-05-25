import os
from datetime import datetime, timezone
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, event
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, StaticPool
from typing import Generator

from .logging_config import setup_logging

logger = setup_logging("scholarforge.database")

DB_FOLDER = os.path.join(os.path.dirname(__file__), "data")
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER, exist_ok=True)

SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    f"sqlite:///{DB_FOLDER}/scholarforge.db"
)

# Configure connection pooling based on database type
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # SQLite uses StaticPool for single-threaded usage
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
else:
    # PostgreSQL/MySQL use QueuePool with connection pooling
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,  # Number of connections to maintain
        max_overflow=20,  # Maximum overflow connections
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections every hour
        echo=False  # Set to True for SQL debugging
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ReportDB(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    topic = Column(String, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ProjectFolder(Base):
    __tablename__ = "project_folders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sessions = relationship("ChatSession", back_populates="folder", cascade="all, delete-orphan")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey("project_folders.id")) 
    title = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    folder = relationship("ProjectFolder", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session = relationship("ChatSession", back_populates="messages")

class Hook(Base):
    __tablename__ = "hooks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================================
# DATABASE SESSION MANAGEMENT
# ============================================================================

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Ensures proper cleanup even if exceptions occur.
    
    Usage:
        with get_db_session() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction error: {e}", exc_info=e)
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for request-scoped database sessions.
    
    Usage in FastAPI endpoints:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database: create tables if they don't exist."""
    try:
        logger.info("Initializing database schema...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}", exc_info=e)
        raise


# ============================================================================
# USER MANAGEMENT & CRYPTOGRAPHY (ZERO-DEPENDENCY PBKDF2)
# ============================================================================

import hashlib
import os

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}:{hash_bytes.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        if not stored_hash or ":" not in stored_hash:
            return False
        salt_hex, hash_hex = stored_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        actual_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return actual_hash == expected_hash
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def create_user(username: str, password: str) -> UserDB:
    try:
        with get_db_session() as db:
            existing = db.query(UserDB).filter(UserDB.username == username).first()
            if existing:
                raise Exception("Username already exists")
            user = UserDB(username=username, password_hash=hash_password(password))
            db.add(user)
            db.flush()
            db.refresh(user)
            logger.info(f"Created user: {username} (ID: {user.id})")
            return user
    except Exception as e:
        logger.error(f"Error creating user {username}: {e}")
        raise

def authenticate_user(username: str, password: str) -> UserDB:
    try:
        with get_db_session() as db:
            user = db.query(UserDB).filter(UserDB.username == username).first()
            if user and verify_password(password, user.password_hash):
                return user
            return None
    except Exception as e:
        logger.error(f"Error authenticating user {username}: {e}")
        return None

def get_user_by_id(user_id: int) -> UserDB:
    try:
        with get_db_session() as db:
            return db.query(UserDB).filter(UserDB.id == user_id).first()
    except Exception as e:
        logger.error(f"Error retrieving user by id {user_id}: {e}")
        return None


# ============================================================================
# PROJECT & CHAT DATA OPERATIONS
# ============================================================================

# ============================================================================
# PROJECT & CHAT DATA OPERATIONS
# ============================================================================

def create_folder(name: str, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ProjectFolder).filter(ProjectFolder.name == name)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            existing = query.first()
            if existing:
                raise Exception("Folder with this name already exists")
            folder = ProjectFolder(name=name, user_id=user_id)
            db.add(folder)
            db.flush()  # Flush to get the ID without committing
            db.refresh(folder)
            logger.info(f"Created folder: {name} (ID: {folder.id}) for user {user_id}")
            return folder
    except Exception as e:
        logger.error(f"Error creating folder {name}: {e}")
        raise

def rename_folder(folder_id: int, new_name: str, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ProjectFolder).filter(ProjectFolder.id == folder_id)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            folder = query.first()
            if folder:
                folder.name = new_name
                logger.info(f"Renamed folder {folder_id} to: {new_name}")
                return True
            logger.warning(f"Folder not found or unauthorized: {folder_id}")
            return False
    except Exception as e:
        logger.error(f"Error renaming folder {folder_id}: {e}")
        raise

def delete_folder(folder_id: int, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ProjectFolder).filter(ProjectFolder.id == folder_id)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            folder = query.first()
            if folder:
                db.delete(folder)
                logger.info(f"Deleted folder: {folder_id}")
                return True
            logger.warning(f"Folder not found or unauthorized: {folder_id}")
            return False
    except Exception as e:
        logger.error(f"Error deleting folder {folder_id}: {e}")
        raise

def get_folders_with_sessions(user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ProjectFolder)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            folders = query.order_by(ProjectFolder.created_at.desc()).all()
            result = []
            for f in folders:
                sessions = sorted(f.sessions, key=lambda s: s.created_at, reverse=True)
                result.append({
                    "id": f.id,
                    "name": f.name,
                    "sessions": [{"id": s.id, "title": s.title, "created_at": s.created_at.strftime("%b %d, %H:%M") if s.created_at else None} for s in sessions]
                })
            return result
    except Exception as e:
        logger.error(f"Error fetching folders for user {user_id}: {e}")
        raise

def create_chat_session(folder_id: int, title: str, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ProjectFolder).filter(ProjectFolder.id == folder_id)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            folder = query.first()
            if not folder:
                raise Exception("Unauthorized folder session creation request")
            session = ChatSession(folder_id=folder_id, title=title)
            db.add(session)
            db.flush()
            db.refresh(session)
            logger.info(f"Created chat session: {title} (ID: {session.id}) in folder {folder_id}")
            return session
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise

def rename_chat_session(session_id: int, new_title: str, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ChatSession).join(ProjectFolder).filter(ChatSession.id == session_id)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            session = query.first()
            if session:
                session.title = new_title
                logger.info(f"Renamed chat session {session_id} to: {new_title}")
                return True
            logger.warning(f"Chat session not found or unauthorized: {session_id}")
            return False
    except Exception as e:
        logger.error(f"Error renaming chat session {session_id}: {e}")
        raise

def delete_chat_session(session_id: int, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ChatSession).join(ProjectFolder).filter(ChatSession.id == session_id)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            session = query.first()
            if session:
                db.delete(session)
                logger.info(f"Deleted chat session: {session_id}")
                return True
            logger.warning(f"Chat session not found or unauthorized: {session_id}")
            return False
    except Exception as e:
        logger.error(f"Error deleting chat session {session_id}: {e}")
        raise

def get_chat_session(session_id: int, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ChatSession).join(ProjectFolder).filter(ChatSession.id == session_id)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            session = query.first()
            logger.debug(f"Retrieved chat session: {session_id}")
            return session
    except Exception as e:
        logger.error(f"Error retrieving chat session {session_id}: {e}")
        raise

def get_session_messages(session_id: int, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ChatSession).join(ProjectFolder).filter(ChatSession.id == session_id)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            session = query.first()
            if not session:
                return []
            messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
            logger.debug(f"Retrieved {len(messages)} messages from session {session_id}")
            return messages
    except Exception as e:
        logger.error(f"Error retrieving session messages {session_id}: {e}")
        raise

def save_chat_message(session_id: int, role: str, content: str, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ChatSession).join(ProjectFolder).filter(ChatSession.id == session_id)
            if user_id is not None:
                query = query.filter(ProjectFolder.user_id == user_id)
            session = query.first()
            if not session:
                raise Exception("Unauthorized request to save message")
            msg = ChatMessage(session_id=session_id, role=role, content=content)
            db.add(msg)
            logger.debug(f"Saved {role} message to session {session_id}")
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        raise

def save_report(topic: str, content: str, user_id: int = None):
    try:
        with get_db_session() as db:
            new_report = ReportDB(topic=topic, content=content, user_id=user_id)
            db.add(new_report)
            logger.info(f"Saved report: {topic} for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        raise

def get_all_reports(user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ReportDB.id, ReportDB.topic, ReportDB.created_at)
            if user_id is not None:
                query = query.filter(ReportDB.user_id == user_id)
            reports = query.order_by(ReportDB.created_at.desc()).all()
            logger.debug(f"Retrieved {len(reports)} reports for user {user_id}")
            return reports
    except Exception as e:
        logger.error(f"Error retrieving reports: {e}")
        raise

def get_report_content(report_id: int, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ReportDB).filter(ReportDB.id == report_id)
            if user_id is not None:
                query = query.filter(ReportDB.user_id == user_id)
            report = query.first()
            logger.debug(f"Retrieved report content: {report_id}")
            return report
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {e}")
        raise

def delete_report(report_id: int, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ReportDB).filter(ReportDB.id == report_id)
            if user_id is not None:
                query = query.filter(ReportDB.user_id == user_id)
            report = query.first()
            if report:
                db.delete(report)
                logger.info(f"Deleted report: {report_id}")
                return True
            logger.warning(f"Report not found or unauthorized: {report_id}")
            return False
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}")
        raise

def delete_all_reports(user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(ReportDB)
            if user_id is not None:
                query = query.filter(ReportDB.user_id == user_id)
            count = query.delete()
            logger.info(f"Deleted all reports for user {user_id}: {count} records")
            return True
    except Exception as e:
        logger.error(f"Error deleting all reports: {e}")
        raise

def save_hook(content: str, user_id: int = None):
    try:
        with get_db_session() as db:
            new_hook = Hook(content=content, user_id=user_id)
            db.add(new_hook)
            logger.info(f"Saved hook for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving hook: {e}")
        raise

def get_all_hooks(user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(Hook)
            if user_id is not None:
                query = query.filter(Hook.user_id == user_id)
            hooks = query.order_by(Hook.created_at.desc()).all()
            logger.debug(f"Retrieved {len(hooks)} hooks for user {user_id}")
            return hooks
    except Exception as e:
        logger.error(f"Error retrieving hooks: {e}")
        raise

def delete_hook(hook_id: int, user_id: int = None):
    try:
        with get_db_session() as db:
            query = db.query(Hook).filter(Hook.id == hook_id)
            if user_id is not None:
                query = query.filter(Hook.user_id == user_id)
            hook = query.first()
            if hook:
                db.delete(hook)
                logger.info(f"Deleted hook: {hook_id}")
                return True
            logger.warning(f"Hook not found or unauthorized: {hook_id}")
            return False
    except Exception as e:
        logger.error(f"Error deleting hook {hook_id}: {e}")
        raise