# ScholarForge: Migrations, CI/CD, and Testing

This final chapter explains how the database schema, code quality, and test suite are managed in ScholarForge, covering Alembic migrations, GitHub Actions automation, and Pytest suites.

---

## Alembic Database Migrations

When SQLAlchemy model structures are updated (e.g., adding a field to `ReportDB`), the changes must be reflected in the database. ScholarForge uses **Alembic** to manage these schema migrations:

```
1. Developer edits models (database.py)
       │
       ▼
2. Generate migration script
   $ alembic revision --autogenerate -m "Add description"
   (Creates versions/xxxx_add_description.py file)
       │
       ▼
3. Apply migration to database
   $ alembic upgrade head
```

### Key Migration Commands
* **Apply all pending changes**: `alembic upgrade head`.
* **Roll back the latest change**: `alembic downgrade -1`.
* **Check database migration history**: `alembic history`.
* **Check current database schema version**: `alembic current`.

*Note: In production deployments, databases should be backed up before running migrations, and schema changes should be tested in staging environments first.*

---

## GitHub Actions CI/CD Pipeline

ScholarForge implements a continuous integration pipeline, defined in `.github/workflows/ci.yml`. The pipeline runs on every push or pull request to the main branches (`master`, `main`, `develop`) and includes the following steps:

```
┌────────────────────────────────────────────────────────┐
│               Code Push / Pull Request                 │
└───────────┬────────────────────────────────────────────┘
            │
            ├────────────────────────────────────────────┐
            │                                            │
       ┌────▼─────┐  ┌──────────┐  ┌────────────────┐   │
       │   Lint   │  │ Security │  │    Coverage    │   │
       │ (ruff)   │  │ (bandit) │  │  (pytest-cov)  │   │
       └────┬─────┘  └────┬─────┘  └────────┬───────┘   │
            │             │                 │           │
            └─────────────┼─────────────────┘           │
                          │                             │
                     ┌────▼─────┐                       │
                     │  Tests   │ ◄─────────────────────┘
                     │ (pytest) │
                     └────┬─────┘
                          │
                     ┌────▼────────┐
                     │ Docker Build│
                     │  (validate) │
                     └─────────────┘
```

1. **Linting (`ruff`)**: Checks code quality and compliance with Python style guides.
2. **Security Scan (`bandit`)**: Scans code for vulnerabilities, such as SQL injection risks or hardcoded secrets.
3. **Tests (`pytest`)**: Runs the full test suite.
4. **Coverage (`pytest-cov`)**: Generates coverage reports and uploads them to Codecov.
5. **Docker Build**: Validates the Dockerfile to prevent build failures.

---

## The Pytest Suite

The testing suite, located in the `tests/` directory, contains 80+ unit and integration tests grouped by component:

```
tests/
├── conftest.py          # Configuration and test fixtures
├── test_database.py     # Database CRUD tests
├── test_api.py          # FastAPI endpoint tests
└── test_conversions.py  # File conversion tests
```

### 1. Test Isolation with SQLite In-Memory Fixtures
To ensure tests do not write to production files, `conftest.py` configures a temporary in-memory SQLite database:

```python
@pytest.fixture(scope="session")
def test_engine():
    # Set up in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def test_db(test_engine):
    # Wrap database session in transaction rollback to keep tests isolated
    connection = test_engine.connect()
    transaction = connection.begin()
    db = SessionLocal(bind=connection)
    
    yield db
    
    db.close()
    transaction.rollback()
    connection.close()
```

By rolling back the transaction after each test, the database is restored to a clean state, preventing tests from affecting one another.

### 2. Test Coverage Categories
* **Database Tests (`test_database.py`)**:
  Verifies CRUD operations on folders, sessions, messages, and reports, ensuring cascade deletes (like removing folders deleting associated sessions) function as expected.
* **API Tests (`test_api.py`)**:
  Uses FastAPI's `TestClient` to mock requests, verifying endpoints, body validation, rate limiting, and error responses.
* **Conversion Tests (`test_conversions.py`)**:
  Verifies format conversion functions, checking that inputs are correctly converted into PDF, DOCX, TXT, MD, and JSON outputs.

---

Next, proceed to **Chapter 10: Production Readiness and Final Product Features** to see the roadmap and detailed specifications for transitioning ScholarForge from an engineering prototype into a polished, complete product.
