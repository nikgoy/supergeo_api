# Testing Guide

Comprehensive testing guide for the AI Cache Layer project.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [CI/CD Integration](#cicd-integration)

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Virtual environment (recommended)

### Install Test Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Quick install (recommended) - installs only essentials
pip install -r requirements.txt
pip install pytest pytest-cov pytest-flask pytest-mock cffi

# OR: Full install (slower, includes code quality tools)
pip install -r requirements-dev.txt
```

**Note:** The quick install method is much faster and sufficient for running tests. Full install includes optional code quality tools (black, flake8, mypy, isort) which can be installed separately if needed.

### Run All Tests

```bash
# Using pytest directly
pytest

# Using make (if available)
make test
```

### Run Tests with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Or using make
make test-cov
```

View HTML coverage report:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_models.py           # Model tests (Client, Page, Visit)
├── test_encryption.py       # Encryption service tests
├── test_api_health.py       # Health check endpoint tests
├── test_api_clients.py      # Client CRUD API tests
├── test_middleware.py       # Authentication and bot detection tests
└── test_integration.py      # Integration and workflow tests
```

### Test Categories

Tests are marked with pytest markers:

- `unit` - Unit tests (fast, isolated)
- `integration` - Integration tests (slower, test interactions)
- `database` - Tests that require database
- `api` - API endpoint tests
- `encryption` - Encryption-related tests
- `slow` - Slow running tests

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_models.py
```

### Run Specific Test Class

```bash
pytest tests/test_models.py::TestClientModel
```

### Run Specific Test Function

```bash
pytest tests/test_models.py::TestClientModel::test_create_client
```

### Run Tests by Marker

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# API tests only
pytest -m api

# All except integration tests
pytest -m "not integration"
```

### Run Tests with Different Verbosity

```bash
# Minimal output
pytest -q

# Verbose output
pytest -v

# Very verbose output (show all test names)
pytest -vv
```

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest -n 4
```

### Run Failed Tests Only

```bash
# Re-run only failed tests from last run
pytest --lf

# Re-run failed tests first, then rest
pytest --ff
```

### Stop on First Failure

```bash
pytest -x
```

## Test Fixtures

### Available Fixtures

Defined in `tests/conftest.py`:

#### Application Fixtures

- `app` - Flask application configured for testing
- `client` - Flask test client for making requests
- `db` - Database session with automatic rollback

#### Data Fixtures

- `sample_client` - Pre-created client for testing
- `sample_page` - Pre-created page for testing
- `sample_visit` - Pre-created visit for testing
- `multiple_clients` - List of 5 clients for testing pagination

#### Authentication Fixtures

- `auth_headers` - Dictionary with valid X-API-Key header

### Using Fixtures

```python
def test_example(client, auth_headers, sample_client):
    """Test using multiple fixtures."""
    response = client.get(
        f'/api/v1/clients/{sample_client.id}',
        headers=auth_headers
    )
    assert response.status_code == 200
```

## Writing Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test

```python
import pytest
from app.models.client import Client


class TestClientModel:
    """Test Client model."""

    def test_create_client(self, db):
        """Test creating a basic client."""
        client = Client(
            name='Example Corp',
            domain='example.com',
            is_active=True
        )

        db.add(client)
        db.commit()
        db.refresh(client)

        assert client.id is not None
        assert client.name == 'Example Corp'

    def test_client_unique_domain(self, db, sample_client):
        """Test that client domain must be unique."""
        duplicate = Client(
            name='Different Corp',
            domain=sample_client.domain  # Duplicate
        )

        db.add(duplicate)

        with pytest.raises(Exception):
            db.commit()
```

### Testing API Endpoints

```python
def test_list_clients(client, auth_headers, sample_client):
    """Test listing clients via API."""
    response = client.get('/api/v1/clients', headers=auth_headers)

    assert response.status_code == 200
    data = response.get_json()

    assert 'clients' in data
    assert data['count'] == 1
```

### Testing Encryption

```python
def test_encrypt_decrypt(db):
    """Test encryption property."""
    client = Client(name='Test', domain='test.com')
    client.cloudflare_api_token = 'secret'

    db.add(client)
    db.commit()
    db.refresh(client)

    # Raw field should be encrypted bytes
    assert isinstance(client.cloudflare_api_token_encrypted, bytes)

    # Property should decrypt
    assert client.cloudflare_api_token == 'secret'
```

### Parametrized Tests

```python
@pytest.mark.parametrize("user_agent,expected_bot", [
    ("Mozilla/5.0 (compatible; GPTBot/1.0)", "GPTBot"),
    ("Mozilla/5.0 (compatible; ClaudeBot/1.0)", "ClaudeBot"),
    ("Chrome/91.0", None),
])
def test_bot_detection(user_agent, expected_bot):
    """Test bot detection with different user agents."""
    from app.middleware.auth import detect_bot

    is_bot, bot_name = detect_bot(user_agent)

    if expected_bot:
        assert is_bot is True
        assert bot_name == expected_bot
    else:
        assert is_bot is False
```

## Test Coverage

### Current Coverage

Run tests with coverage to see current coverage:

```bash
make test-cov
```

### Coverage Goals

- **Overall**: >80%
- **Models**: >90%
- **Services**: >90%
- **API Endpoints**: >85%
- **Middleware**: >85%

### Viewing Coverage Report

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report (more detailed)
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Coverage Configuration

Coverage settings are in `pytest.ini`:

```ini
[coverage:run]
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    */alembic/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Common Testing Patterns

### Testing Database Transactions

```python
def test_with_rollback(db):
    """Test that changes are rolled back after test."""
    # Create data
    client = Client(name='Test', domain='test.com')
    db.add(client)
    db.commit()

    # Test finishes, data is automatically rolled back
```

### Testing Errors

```python
def test_error_handling():
    """Test that function raises expected error."""
    from app.services.encryption import EncryptionService

    service = EncryptionService()

    with pytest.raises(ValueError, match="Cannot encrypt empty"):
        service.encrypt("")
```

### Mocking External Services

```python
from unittest.mock import patch, Mock

def test_with_mock():
    """Test with mocked external service."""
    with patch('app.services.external.ExternalAPI') as mock_api:
        mock_api.return_value.fetch.return_value = {'data': 'test'}

        # Your test code here
        result = some_function()

        assert result == {'data': 'test'}
        mock_api.return_value.fetch.assert_called_once()
```

## Troubleshooting

### Tests Fail with Database Errors

Ensure you're using SQLite in-memory database for tests (configured in `conftest.py`):

```python
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
```

### Import Errors

Make sure you're in the project root directory and virtual environment is activated:

```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pytest
```

### Fixture Not Found

Check that fixtures are defined in `conftest.py` or imported properly.

### Coverage Not Working

Install pytest-cov:

```bash
pip install pytest-cov
```

### Dependency Conflicts

If you encounter errors related to `urllib3` version conflicts:

```bash
# The requirements-dev.txt has been updated to handle this
# types-requests is now commented out as it's optional for testing
pip install -r requirements-dev.txt --force-reinstall
```

### Database Compatibility Issues

The codebase has been updated to support both PostgreSQL (production) and SQLite (testing):

- **UUID Type**: A custom `GUID` type decorator handles UUID columns across both databases
- **Timestamps**: Using `func.now()` instead of `text("now()")` for better cross-database compatibility
- **Connection Pooling**: SQLite doesn't use `pool_size` and `max_overflow` parameters

These changes ensure tests run smoothly locally with SQLite while maintaining PostgreSQL compatibility for production.

## Best Practices

1. **Isolation**: Each test should be independent
2. **Descriptive Names**: Use clear, descriptive test names
3. **One Assertion Per Test**: Focus on testing one thing
4. **Use Fixtures**: Reuse common setup with fixtures
5. **Test Edge Cases**: Test both happy path and error cases
6. **Keep Tests Fast**: Use mocks for external services
7. **Arrange-Act-Assert**: Follow AAA pattern

## Recent Updates

### November 2025

- Fixed dependency conflict between `types-requests` and `urllib3`
- Added cross-database UUID support via custom `GUID` type
- Updated timestamp defaults to use `func.now()` for better compatibility
- Enhanced SQLite support for local testing
- Added `cffi` as explicit dependency for cryptography support

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/latest/orm/session_basics.html#using-thread-local-scope-with-web-applications)
