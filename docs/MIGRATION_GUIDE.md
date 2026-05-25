# Database Migration Guide for ScholarForge

## Overview
This guide explains how to manage database schema changes using Alembic migrations.

## Common Tasks

### 1. Creating a New Migration

After modifying `backend/database.py` models:

```bash
cd /home/mohammed/ScholarForge
alembic revision --autogenerate -m "Description of changes"
```

This creates a new migration file in `alembic/versions/`.

### 2. Applying Migrations

To apply pending migrations:

```bash
alembic upgrade head
```

To apply a specific number of migrations:

```bash
alembic upgrade +2
```

### 3. Reverting Migrations

To go back one migration:

```bash
alembic downgrade -1
```

To go back to a specific migration:

```bash
alembic downgrade <revision_id>
```

### 4. Viewing Migration History

```bash
alembic history
```

### 5. Viewing Current Database Version

```bash
alembic current
```

## Important Notes

- **Automatic Detection**: Alembic autogenerate detects:
  - New tables
  - Dropped tables
  - Changed columns
  - Added/removed indexes
  - Constraint changes

- **Manual Edits**: After generation, review the migration file in `alembic/versions/` and make any necessary adjustments before applying.

- **Production Safety**: Always:
  1. Test migrations on a development database first
  2. Backup production database before applying
  3. Run migrations during maintenance window

- **Connection Pooling**: Database connections now use:
  - **SQLite**: StaticPool (single-threaded)
  - **PostgreSQL/MySQL**: QueuePool with:
    - pool_size=10 (baseline connections)
    - max_overflow=20 (additional connections)
    - pool_pre_ping=True (connection validation)
    - pool_recycle=3600 (recycle hourly)

## API Usage

### Old Pattern (Still Works)
```python
from backend.database import SessionLocal

db = SessionLocal()
try:
    user = db.query(User).first()
finally:
    db.close()
```

### New Pattern (Recommended)
```python
from backend.database import get_db_session

with get_db_session() as db:
    user = db.query(User).first()
```

### FastAPI Pattern (For Endpoints)
```python
from fastapi import Depends
from backend.database import get_db

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

## Logging

All database operations are now logged with:
- Operation type (create, read, update, delete)
- Resource IDs and names
- Errors with full traceback
- Debug information for queries

View logs:
```bash
# In Docker
docker logs scholarforge-web

# In terminal
tail -f /path/to/logs
```
