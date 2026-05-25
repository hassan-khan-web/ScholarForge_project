# ScholarForge GitHub Actions CI/CD Pipeline

## Overview

The CI/CD pipeline automatically runs on every push to `master`, `main`, or `develop` branches and on all pull requests. It performs:

1. **Linting** — Code quality checks with `ruff`
2. **Testing** — Full test suite with `pytest`
3. **Docker Build** — Validate Dockerfile for errors
4. **Security Scanning** — Vulnerability detection with `bandit`
5. **Coverage Report** — Track test coverage trends

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Code Push / Pull Request                │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├─────────────────────────────────────────────┐
               │                                             │
          ┌────▼─────┐  ┌──────────┐  ┌─────────────────┐   │
          │   Lint   │  │ Security │  │   Coverage      │   │
          │ (ruff)   │  │ (bandit) │  │   (optional)    │   │
          └────┬─────┘  └────┬─────┘  └────────┬────────┘   │
               │             │                  │            │
               └─────────────┼──────────────────┘            │
                             │                               │
                        ┌────▼─────┐                         │
                        │   Tests   │                         │
                        │ (pytest)  │ ◄───────────────────┘
                        └────┬─────┘
                             │
                        ┌────▼────────┐
                        │ Docker Build │
                        │  (validate)  │
                        └─────────────┘
```

## Jobs

### 1. `lint`
**Purpose:** Static code analysis  
**Tool:** `ruff`  
**Runs on:** All branches  
**Failures:** Continue (warning only)

```bash
# Check for critical issues (runs first)
ruff check backend/ --select=E9,F63,F7,F82

# General linting (runs second)
ruff check backend/ --exit-zero
```

**Exit Codes:**
- `E9` — Syntax errors
- `F63` — Assert tuple
- `F7` — Async def
- `F82` — Undefined name

### 2. `test`
**Purpose:** Run full test suite  
**Dependencies:** Requires `lint` to pass  
**Tool:** `pytest`  
**Timeout:** 10 minutes

```bash
pytest tests/ -v --tb=short --junit-xml=test-results.xml
```

**Artifacts Generated:**
- `test-results.xml` — JUnit format for GitHub UI integration
- Test summary in Actions tab

### 3. `build-docker`
**Purpose:** Validate Dockerfile and catch build errors early  
**Dependencies:** Requires `test` to pass  
**Tool:** Docker Buildx  
**Caching:** Uses GitHub Actions cache for layer caching

```bash
docker buildx build --cache-from=gha --cache-to=gha,mode=max .
```

**Benefits:**
- Catches Dockerfile errors before production deployment
- Builds layer cache for faster deployments
- No push to registry (validation only)

### 4. `security-scan`
**Purpose:** Detect security vulnerabilities in Python code  
**Dependencies:** Requires `lint` to pass  
**Tool:** `bandit`  
**Report:** JSON format for trend analysis

```bash
bandit -r backend/ -ll -f json -o bandit-report.json
```

**Coverage:**
- SQL injection
- Hardcoded passwords
- Insecure temp files
- Command injection
- Other OWASP Top 10 issues

### 5. `coverage`
**Purpose:** Track code coverage trends  
**Dependencies:** Requires `test` to pass  
**Tool:** `pytest-cov` + Codecov  
**Upload:** Codecov for visual reporting

```bash
pytest tests/ \
  --cov=backend \
  --cov-report=xml \
  --cov-report=term
```

## Workflow Execution

### Triggers

1. **Push to main branches:**
   ```yaml
   on:
     push:
       branches: [ master, main, develop ]
   ```

2. **Pull requests:**
   ```yaml
   on:
     pull_request:
       branches: [ master, main, develop ]
   ```

### Execution Flow

1. **Lint** (parallel with Security)
   - Checks code quality
   - Doesn't block if warnings only
   
2. **Tests** (after Lint)
   - Runs full test suite
   - All 83 tests must pass
   - Publishes results to Actions
   
3. **Docker Build** (after Tests)
   - Validates Dockerfile
   - Builds all layers
   - Populates cache for production
   
4. **Security Scan** (parallel with Tests)
   - Scans for vulnerabilities
   - Generates JSON report
   - Optional fail (continue-on-error)
   
5. **Coverage** (after Tests)
   - Generates coverage report
   - Uploads to Codecov
   - Tracks trends over time

## Environment Setup

### Python Version
```yaml
python-version: '3.10'
```

### Caching
```yaml
cache: 'pip'
```
- Caches pip dependencies
- ~90% cache hit rate
- Saves 2-3 minutes per job

### Artifacts

**Test Results:**
- File: `test-results.xml`
- Retention: 90 days
- Viewer: GitHub Actions > Test Results

**Security Results:**
- File: `bandit-report.json`
- Retention: 90 days
- Format: JSON for parsing

**Coverage:**
- Service: Codecov.io
- Badge: Can be added to README
- Trends: Visible on Codecov dashboard

## Configuration Files

### `.github/workflows/ci.yml`

The main workflow definition. Key sections:

```yaml
name: CI Pipeline

on:
  push:
    branches: [ master, main, develop ]
  pull_request:
    branches: [ master, main, develop ]

jobs:
  lint:
    # ...
  test:
    # ...
  build-docker:
    # ...
  security-scan:
    # ...
  coverage:
    # ...
```

### `requirements.txt` (Dev Dependencies)

```
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=7.0.0
ruff>=0.1.0
bandit>=1.7.5
```

## Running Locally

### Install Dev Dependencies
```bash
pip install -r requirements.txt
```

### Run Linting
```bash
ruff check backend/
```

### Run Tests
```bash
pytest tests/ -v
```

### Generate Coverage
```bash
pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

### Security Audit
```bash
bandit -r backend/
```

## Troubleshooting

### Lint Failures
**Problem:** Ruff reports errors  
**Solution:** Fix according to error code:
- `E9` — Syntax error
- `F82` — Undefined name
- `E501` — Line too long

```bash
ruff check backend/ --fix
```

### Test Failures
**Problem:** Tests fail in CI but pass locally  
**Possible Causes:**
- Environment variables not set
- File path issues on Linux vs macOS
- Timing issues in async tests

**Debug:**
```bash
# Run with verbose output
pytest tests/ -vv

# Run single test
pytest tests/test_database.py::TestFolderOperations::test_create_folder -vv

# Run with logging
pytest tests/ --log-cli-level=DEBUG
```

### Docker Build Failures
**Problem:** Docker build fails in CI  
**Common Issues:**
- Network connectivity (apt-get)
- Missing dependencies
- Dockerfile syntax errors

**Debug Locally:**
```bash
docker build -t scholarforge:latest .
docker build --progress=plain -t scholarforge:latest .
```

### Security Scan Issues
**Problem:** Bandit reports high-risk findings  
**Common False Positives:**
- Test hardcoded credentials
- Assert statements in tests

**Suppress:**
```python
# bandit: disable=hardcoded_sql_password
api_key = "test-key-for-testing"
```

## Performance Optimization

### Cache Management
- **Pip cache:** Automatic (GitHub Actions default)
- **Docker layer cache:** 7-day retention
- **Hit rate goal:** >80%

### Parallel Jobs
Currently sequential by design (lint → test → build). Can be parallelized if needed:
- Lint (parallel)
- Security (parallel)
- Tests (after lint)
- Docker (after tests)

### Skip Workflows
Add to commit message to skip CI:
```
[skip ci]
```

Or for specific jobs:
```
[skip tests]
[skip docker]
```

## Integration with Services

### Codecov.io
- **Purpose:** Track coverage over time
- **Setup:** Automatic with token
- **Badge:** Add to README:
  ```markdown
  [![codecov](https://codecov.io/gh/user/repo/branch/master/graph/badge.svg)](https://codecov.io/gh/user/repo)
  ```

### GitHub Branch Protection
Configure in repo settings:
- Require status checks to pass before merging
- Dismiss stale review approvals
- Require branches to be up to date

**Rules to require:**
- ✅ CI Pipeline — Lint
- ✅ CI Pipeline — Test
- ✅ CI Pipeline — Build Docker

## Monitoring

### GitHub Actions Dashboard
- Visit: Actions tab in repo
- See: All workflow runs
- Filter: By branch or status

### Status Badge
Add to README.md:
```markdown
![CI Pipeline](https://github.com/user/repo/actions/workflows/ci.yml/badge.svg)
```

## Future Enhancements

### Phase 4.2 Extensions
- [ ] Deploy to staging on successful main push
- [ ] Integration tests with real services
- [ ] Performance benchmarks
- [ ] Dependency update checks
- [ ] Container registry push (Docker Hub, ECR)

### Example: Push to Docker Hub
```yaml
- name: Push to Docker Hub
  if: github.ref == 'refs/heads/master' && success()
  uses: docker/build-push-action@v4
  with:
    context: .
    push: true
    tags: |
      username/scholarforge:latest
      username/scholarforge:${{ github.sha }}
    registry: docker.io
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_PASSWORD }}
```

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.io/)
- [Docker Build Action](https://github.com/docker/build-push-action)
