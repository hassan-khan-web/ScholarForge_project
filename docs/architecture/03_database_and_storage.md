# ScholarForge: Database and Storage

In this chapter, we are going to look closely at `backend/database.py`. This file handles the data models, connection lifecycles, connection pooling, and CRUD helper queries.

---

## Connection Pooling & Multi-Dialect Support

ScholarForge supports both **SQLite** (for easy, zero-setup local development) and **PostgreSQL** (for production deployments). Because SQLite and PostgreSQL handle concurrency differently, the backend configures connection pooling dynamically based on the database URL:

```python
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    f"sqlite:///{DB_FOLDER}/scholarforge.db"
)
```

### 1. SQLite Optimization
SQLite is a serverless, file-based database. If multiple threads attempt to write to the same file simultaneously without proper pooling, it raises "Database is locked" exceptions. To mitigate this:
* **StaticPool**: Reuses a single connection across the thread runtime.
* **check_same_thread=False**: Allows multi-threaded access on a single connection.
* **Write-Ahead Logging (WAL)**: An event listener intercepts the SQLite engine connection and executes `PRAGMA journal_mode=WAL`. This enables concurrent reads while a write operation is active, preventing locking.

### 2. PostgreSQL Optimization
For enterprise databases, ScholarForge configures SQLAlchemy's `QueuePool`:
* **pool_size=10**: Keeps 10 persistent, ready-to-use database connections in reserve.
* **max_overflow=20**: Allows the pool to open up to 20 additional connections during high-traffic surges.
* **pool_pre_ping=True**: Executes a lightweight test query (`SELECT 1`) before returning a connection from the pool. If the connection died (e.g., database restarted), it discards it and creates a fresh one.
* **pool_recycle=3600**: Recycles database connections hourly to prevent idle timeout disconnects.

---

## Database Schema (SQLAlchemy Models)

The schema is defined using SQLAlchemy's Declarative Base:

```
                  ┌──────────────────────┐
                  │    ProjectFolder     │
                  └──────────┬───────────┘
                             │ 1
                             │
                             │ * (Cascade Delete)
                  ┌──────────▼───────────┐
                  │     ChatSession      │
                  └──────────┬───────────┘
                             │ 1
                             │
                             │ * (Cascade Delete)
                  ┌──────────▼───────────┐
                  │     ChatMessage      │
                  └──────────────────────┘

  ┌──────────────────────┐          ┌──────────────────────┐
  │       ReportDB       │          │         Hook         │
  └──────────────────────┘          └──────────────────────┘
```

1. **`ProjectFolder` (`project_folders` table)**:
   * Fields: `id` (Primary Key), `name` (Unique String), `created_at` (DateTime UTC).
   * Relationship: Has a one-to-many relationship with `ChatSession`. The `cascade="all, delete-orphan"` parameter ensures that if a folder is deleted, all child sessions are automatically wiped out.

2. **`ChatSession` (`chat_sessions` table)**:
   * Fields: `id` (Primary Key), `folder_id` (Foreign Key referencing `project_folders.id`), `title` (String), `created_at` (DateTime UTC).
   * Relationship: Belongs to a folder, and has a one-to-many relationship with `ChatMessage` (with cascade delete enabled).

3. **`ChatMessage` (`chat_messages` table)**:
   * Fields: `id` (Primary Key), `session_id` (Foreign Key referencing `chat_sessions.id`), `role` (String, e.g., "user" or "assistant"), `content` (Text), `created_at` (DateTime UTC).

4. **`ReportDB` (`reports` table)**:
   * Fields: `id` (Primary Key), `topic` (String), `content` (Text), `created_at` (DateTime UTC). Stores compiled research reports.

5. **`Hook` (`hooks` table)**:
   * Fields: `id` (Primary Key), `content` (Text), `created_at` (DateTime UTC). Stores research notes that can be merged into reports.

---

## Session Lifecycle Management

To prevent connection leaks, the database session lifecycle is tightly controlled:

### 1. Context Manager: `get_db_session`
For background workers, standalone tasks, and write operations, the `get_db_session` context manager is used:

```python
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
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
```

**How it works**:
It opens a local database session. If the code inside the `with` block finishes successfully, it commits the changes. If an exception occurs, it automatically rolls back the transaction to maintain integrity, logs the failure, and ensures that the connection is closed.

### 2. FastAPI Dependency: `get_db`
For standard HTTP endpoints, `get_db` is used as a FastAPI dependency. It yields a request-scoped session and closes it automatically after the response is sent.

---

## Core Database CRUD Operations

`database.py` contains helper functions for database operations. Here is a summary of how they are implemented:

* **Folder Actions**:
  * `create_folder(name)`: Checks if a folder name exists. If unique, saves it.
  * `rename_folder(folder_id, new_name)`: Updates the name of the folder matching the ID.
  * `delete_folder(folder_id)`: Deletes the folder (and cascade deletes sessions and messages).
  * `get_folders_with_sessions()`: Fetches all folders, sorts them by creation date, sorts each folder's sessions by date, and formats the result as a list of dictionaries for JSON responses.
* **Chat Sessions & Messages**:
  * `create_chat_session(folder_id, title)`: Inserts a session.
  * `save_chat_message(session_id, role, content)`: Inserts a message (user or assistant) associated with the session.
  * `get_session_messages(session_id)`: Fetches all messages for a session, sorted chronologically.
* **Reports & Hooks**:
  * `save_report(topic, content)`: Stores a generated report.
  * `get_all_reports()`: Fetches metadata for all reports (IDs, topics, and dates) without loading large text blocks.
  * `get_report_content(report_id)`: Loads the complete text content of a specific report.
  * `save_hook(content)`: Saves a research hook.
  * `get_all_hooks()`: Lists all saved hooks.

This database architecture keeps operations clean, isolated, and scalable. Let's move on to **Chapter 4: AI Generation Engine** to see the logic of report generation.
