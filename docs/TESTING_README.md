# ScholarForge Test Suite Documentation

## Overview

The ScholarForge test suite provides comprehensive coverage for:
- **Database Operations** (CRUD operations on all models)
- **API Endpoints** (Response codes, validation, error handling)
- **File Conversions** (PDF, DOCX, TXT, JSON, MD formats)
- **Content Cleaning** (AI output processing)

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest fixtures and configuration
├── test_database.py            # Database CRUD tests
├── test_api.py                 # API endpoint tests
└── test_conversions.py         # File conversion tests

pytest.ini                       # Pytest configuration
TESTING_README.md              # This file
```

## Test Categories

### 1. Unit Tests (`@pytest.mark.unit`)
Fast tests that verify individual functions in isolation.
- **Database Tests**: CRUD operations on models (ProjectFolder, ChatSession, ChatMessage, ReportDB, Hook)
- **API Tests**: Endpoint response codes, validation, error handling
- **Conversion Tests**: Format conversion functions (TXT, MD, JSON)

### 2. Integration Tests (`@pytest.mark.integration`)
Tests that verify components work together.
- Database + API endpoint flows
- File upload and conversion workflows
- Session lifecycle with messages and reports

## Installation

### Prerequisites
```bash
# Required packages (already installed)
pip install pytest pytest-asyncio httpx
```

### Development Installation
```bash
# Install all dependencies including test packages
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-timeout
```

## Running Tests

### Run All Tests
```bash
# Run with verbose output
pytest

# Run with minimal output
pytest -q

# Run with short traceback
pytest --tb=short
```

### Run Specific Test Categories

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only database tests
pytest -m database

# Run only API tests
pytest -m api

# Run only conversion tests
pytest -m conversion
```

### Run Specific Test Files

```bash
# Test database operations
pytest tests/test_database.py

# Test API endpoints
pytest tests/test_api.py

# Test file conversions
pytest tests/test_conversions.py
```

### Run Specific Tests

```bash
# Test a specific test class
pytest tests/test_database.py::TestFolderOperations

# Test a specific test method
pytest tests/test_database.py::TestFolderOperations::test_create_folder

# Run all tests matching a pattern
pytest -k "create" -v
```

## Test Coverage

### Generate Coverage Report
```bash
# Install coverage plugin
pip install pytest-cov

# Generate coverage report
pytest --cov=backend --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

### Coverage Goals
- **Database Layer**: >90% coverage (all CRUD operations tested)
- **API Layer**: >85% coverage (all endpoints tested)
- **Business Logic**: >80% coverage (core functionality tested)

## Fixtures

### Database Fixtures (`conftest.py`)

**`test_engine`** - Session-scoped in-memory SQLite database
```python
@pytest.fixture(scope="session")
def test_engine():
    """Create an in-memory SQLite database for testing."""
```

**`test_db`** - Function-scoped database session with automatic rollback
```python
@pytest.fixture
def test_db(test_engine):
    """Create a clean database session for each test."""
```

**`client`** - FastAPI TestClient with test database
```python
@pytest.fixture
def client(test_db):
    """Create a FastAPI TestClient with test database."""
```

### Sample Data Fixtures

**`sample_folder`** - ProjectFolder instance
```python
@pytest.fixture
def sample_folder(test_db):
    """Create a sample project folder."""
```

**`sample_session`** - ChatSession instance with folder
```python
@pytest.fixture
def sample_session(test_db, sample_folder):
    """Create a sample chat session."""
```

**`sample_messages`** - ChatMessage instances
```python
@pytest.fixture
def sample_messages(test_db, sample_session):
    """Create sample chat messages."""
```

**`sample_report`** - ReportDB instance
```python
@pytest.fixture
def sample_report(test_db):
    """Create a sample report."""
```

**`sample_hook`** - Hook instance
```python
@pytest.fixture
def sample_hook(test_db):
    """Create a sample hook."""
```

### File Fixtures

**`temp_file`** - Temporary file for testing
```python
@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
```

**`sample_pdf_bytes`** - Minimal PDF bytes
```python
@pytest.fixture
def sample_pdf_bytes():
    """Create minimal PDF bytes for testing."""
```

**`sample_docx_bytes`** - Minimal DOCX bytes
```python
@pytest.fixture
def sample_docx_bytes():
    """Create minimal DOCX bytes for testing."""
```

## Example Tests

### Database Test Example
```python
@pytest.mark.unit
def test_create_folder(self, test_db):
    """Test creating a new folder."""
    folder = create_folder("My Research Project")
    assert folder.id is not None
    assert folder.name == "My Research Project"
    
    # Verify it's in the database
    retrieved = test_db.query(ProjectFolder).filter_by(id=folder.id).first()
    assert retrieved is not None
```

### API Test Example
```python
@pytest.mark.unit
def test_get_folders_empty(self, client):
    """Test getting folders when none exist."""
    response = client.get("/api/folders")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

### Conversion Test Example
```python
@pytest.mark.unit
def test_convert_to_txt(self, temp_file):
    """Test converting content to TXT format."""
    content = "# Heading\n\nThis is test content."
    result = convert_to_txt(content, temp_file)
    
    assert result == "Success"
    assert os.path.exists(temp_file)
```

## Best Practices

### 1. Test Isolation
- Each test runs with a clean database
- No dependencies between tests
- All fixtures are function-scoped (except `test_engine`)

### 2. Clear Assertions
```python
# Good
assert folder.name == "Expected Name"
assert response.status_code == 200

# Avoid
assert folder.name  # Too vague
assert response  # Doesn't verify status
```

### 3. Descriptive Test Names
```python
# Good
def test_create_folder_with_valid_name(self)
def test_delete_nonexistent_folder_returns_false(self)

# Avoid
def test_folder(self)
def test_delete(self)
```

### 4. Use Markers
```python
@pytest.mark.unit
def test_fast_operation(self):
    pass

@pytest.mark.integration
def test_api_workflow(self):
    pass
```

### 5. Error Testing
```python
def test_invalid_operation(self):
    with pytest.raises(ValueError, match="Invalid"):
        perform_invalid_operation()
```

## Debugging Tests

### Verbose Output
```bash
# Show print statements and detailed output
pytest -v -s

# Show local variables in tracebacks
pytest -l

# Drop into debugger on failure
pytest --pdb
```

### Logging
```bash
# Show logs during test execution
pytest --log-cli-level=DEBUG

# Detailed traceback
pytest --tb=long
```

### Run Single Test
```bash
# Easier to debug when running one test at a time
pytest tests/test_database.py::TestFolderOperations::test_create_folder -v
```

## Continuous Integration

### GitHub Actions Example (if configured)
```yaml
- name: Run tests
  run: pytest --cov=backend --cov-report=lcov

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

### Pre-commit Hook
```bash
# Run before committing
pytest --fail-on-flaky --maxfail=1
```

## Troubleshooting

### Issue: "No module named 'backend'"
**Solution**: Ensure you're running pytest from the project root directory
```bash
cd /home/mohammed/ScholarForge
pytest
```

### Issue: "Database is locked"
**Solution**: Tests are using in-memory SQLite, which should prevent locking. Ensure old processes are killed:
```bash
pkill -f "pytest"
pytest
```

### Issue: "Fixtures not found"
**Solution**: Ensure `conftest.py` is in the tests directory and is imported correctly
```bash
ls -la tests/conftest.py
```

### Issue: "Async test failing"
**Solution**: Ensure `asyncio_mode = auto` is set in `pytest.ini`
```
[pytest]
asyncio_mode = auto
```

## Performance

### Test Execution Time
- **Unit Tests**: ~2-5 seconds for 50+ tests
- **Integration Tests**: ~10-30 seconds
- **Full Suite**: ~30-60 seconds

### Optimization Tips
```bash
# Run tests in parallel (if pytest-xdist installed)
pytest -n auto

# Stop after first failure
pytest -x

# Stop after N failures
pytest --maxfail=3

# Run only failed tests from last run
pytest --lf

# Run failed tests first, then others
pytest --ff
```

## Test Dependencies

### Required Packages
- `pytest` >= 7.4.0
- `pytest-asyncio` >= 0.21.0
- `httpx` >= 0.24.0

### Optional Packages
- `pytest-cov` - Code coverage reports
- `pytest-timeout` - Test timeout enforcement
- `pytest-xdist` - Parallel test execution
- `pytest-mock` - Mocking assistance

### Install Optional Packages
```bash
pip install pytest-cov pytest-timeout pytest-xdist
```

## Contributing Tests

When adding new features, ensure test coverage:

1. **Create test file** if needed (e.g., `test_new_feature.py`)
2. **Add fixtures** in `conftest.py` if required
3. **Write unit tests** for individual functions
4. **Write integration tests** for workflows
5. **Update this documentation** with new test categories
6. **Verify coverage** before committing

### Test Template
```python
"""
Brief description of what tests in this module cover.
"""

import pytest
from module_to_test import function_to_test


class TestNewFeature:
    """Test new feature functionality."""
    
    @pytest.mark.unit
    def test_new_feature_basic(self):
        """Test basic new feature operation."""
        result = function_to_test()
        assert result is not None
    
    @pytest.mark.unit
    def test_new_feature_error(self):
        """Test new feature error handling."""
        with pytest.raises(ValueError):
            function_to_test(invalid_param=True)
```

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#in-memory-databases)

## Support

For issues or questions about the test suite:
1. Check the Troubleshooting section above
2. Review existing test examples
3. Check test log file: `tests/pytest.log`
