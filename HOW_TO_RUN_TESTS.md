# How to Run Tests Locally

This guide provides quick instructions for running the test suite locally.

## Setup (One-time)

1. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   pip install cffi
   ```

   **Note:** `cffi` is required for the cryptography library.

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Specific Test File
```bash
pytest tests/test_api_health.py
```

### Run Specific Test Class
```bash
pytest tests/test_models.py::TestClientModel
```

### Run Specific Test Function
```bash
pytest tests/test_models.py::TestClientModel::test_create_client
```

### Run Tests by Category
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only API tests
pytest -m api

# Exclude integration tests
pytest -m "not integration"
```

### Run Tests with Coverage Report
```bash
pytest --cov=app --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the coverage report.

## Quick Test Commands

```bash
# Fast check - run all tests quietly
pytest -q

# Full suite with coverage
pytest --cov=app --cov-report=term-missing

# Stop on first failure
pytest -x

# Re-run only failed tests from last run
pytest --lf
```

## Common Issues

### Import Errors
Make sure you're in the project root directory and your virtual environment is activated:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
cd /path/to/supergeo_api
pytest
```

### Missing Dependencies
```bash
pip install -r requirements-dev.txt --force-reinstall
pip install cffi
```

### Database Errors
Tests use SQLite in-memory database by default (configured in `tests/conftest.py`), so no database setup is required.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_models.py           # Model tests (Client, Page, Visit)
├── test_encryption.py       # Encryption service tests
├── test_api_health.py       # Health check endpoint tests
├── test_api_clients.py      # Client CRUD API tests
├── test_middleware.py       # Authentication and bot detection tests
├── test_sitemap.py          # Sitemap parsing and API tests
└── test_integration.py      # Integration and workflow tests
```

## More Information

For comprehensive testing documentation, including:
- Writing new tests
- Test fixtures
- Best practices
- CI/CD integration

See [TESTING.md](TESTING.md)
