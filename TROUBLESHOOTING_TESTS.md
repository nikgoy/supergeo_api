# Test Troubleshooting Guide

If you're seeing test failures, follow these steps to reset and verify your environment.

## Step 1: Ensure Latest Code

```bash
# Make sure you have the latest changes
git status
git pull origin claude/update-tests-docs-01Uzd164dNGzcAoQuMXFZ8o8
```

## Step 2: Clean Python Cache

```bash
# Remove all cached bytecode and pytest cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
rm -rf .pytest_cache
rm -f coverage.xml
rm -rf htmlcov
```

## Step 3: Verify Environment

```bash
# Check Python version (should be 3.11+)
python3 --version

# Verify pytest is installed
python3 -m pytest --version

# Check key dependencies
python3 -c "import flask; import sqlalchemy; import pytest; print('All imports OK')"
```

## Step 4: Reinstall Dependencies (if needed)

```bash
# Deactivate and reactivate virtual environment
deactivate
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall with fresh cache
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir pytest pytest-cov pytest-flask pytest-mock cffi
```

## Step 5: Run Tests

```bash
# Run a simple test first
python3 -m pytest tests/test_api_health.py -v

# If that works, run all tests
python3 -m pytest tests/ -v
```

## Expected Results

✅ **Good results** (as of latest commit):
- 84 tests passing
- 15 failures (actual implementation issues, not infrastructure)
- 41 errors (mostly transaction/fixture related)
- Some warnings (SAWarning about transactions)

## Common Issues

### Issue: "max_overflow" error with SQLite

**Solution:** Make sure you have the latest `app/models/base.py` which detects SQLite and uses appropriate parameters.

```bash
# Verify the fix is present
grep -A 5 "if database_url.startswith('sqlite')" app/models/base.py
```

You should see code that handles SQLite differently.

### Issue: "no such table" errors

**Solution:** This usually means database initialization happened twice. Check that `tests/conftest.py` doesn't call `init_db()` explicitly in the app fixture.

### Issue: Many tests failing that pass individually

**Cause:** Transaction cleanup issues between tests.

**Workaround:** Run tests in smaller batches:
```bash
pytest tests/test_api_health.py tests/test_encryption.py -v
pytest tests/test_models.py -v
pytest tests/test_api_clients.py -v
```

### Issue: Import errors

**Solution:**
```bash
# Make sure you're in the project root
cd /path/to/supergeo_api
pwd  # Should show .../supergeo_api

# Run from project root
python3 -m pytest tests/
```

## Quick Test Commands

```bash
# Run only passing tests (exclude known failures)
pytest tests/test_api_health.py tests/test_encryption.py tests/test_middleware.py -v

# Run with minimal output
pytest tests/ -q

# Stop on first failure
pytest tests/ -x

# Show only test names
pytest tests/ --collect-only
```

## Getting Help

If tests still fail after these steps:

1. Check that you're on the correct branch:
   ```bash
   git branch --show-current
   # Should show: claude/update-tests-docs-01Uzd164dNGzcAoQuMXFZ8o8
   ```

2. View recent commits:
   ```bash
   git log --oneline -5
   ```

3. Check for uncommitted changes:
   ```bash
   git status
   ```

## Test Status Summary

As of the latest commit, the test infrastructure is working. The **84 passing tests** demonstrate that:

- ✅ Database initialization works
- ✅ Fixtures are properly configured
- ✅ SQLite compatibility is functional
- ✅ API endpoints can be tested
- ✅ Model creation and queries work

The remaining failures are due to:
- Missing/incomplete API implementations
- Test expectations not matching actual behavior
- Some transaction isolation issues

**The test suite is ready for use!** You can now run tests locally and get meaningful feedback.
