# AI Cache Layer

A production-ready Flask API for building an AI-friendly caching layer for websites. This system scrapes web pages, processes them with Google Gemini into clean Markdown, generates minimal HTML, and serves it via Cloudflare KV + Workers optimized for AI bots.

## Features

- **Multi-tenant architecture**: Each client/domain has isolated configuration
- **Secure credential storage**: Cloudflare API tokens and Gemini keys encrypted at rest using Fernet
- **Neon/PostgreSQL**: Single source of truth with proper relational schema
- **Complete pipeline support**: Raw HTML → Gemini Markdown → Simple HTML → Cloudflare KV
- **Visit tracking**: Analytics for AI bot detection and traffic patterns
- **REST API**: Full CRUD operations for client management
- **Production-ready**: Proper migrations, error handling, and security practices

## Tech Stack

- **Python 3.11+**
- **Flask 3.x** with blueprints and app factory pattern
- **SQLAlchemy 2.0+** with Alembic migrations
- **Neon** (PostgreSQL) for database
- **Pydantic Settings** for configuration management
- **Cryptography (Fernet)** for encryption
- **Google Gemini API** for content processing

## Project Structure

```
ai-cache-layer/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Pydantic settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py              # Database setup
│   │   └── client.py            # Client, Page, Visit models
│   ├── services/
│   │   ├── __init__.py
│   │   └── encryption.py        # Fernet encryption service
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py            # Health check endpoints
│   │   └── clients.py           # Client CRUD API
│   └── middleware/
│       ├── __init__.py
│       └── auth.py              # API key authentication
├── alembic/
│   ├── env.py                   # Alembic environment
│   ├── script.py.mako           # Migration template
│   └── versions/
│       └── 001_initial_schema.py
├── scripts/
│   ├── add_client.py            # Interactive client creation
│   └── generate_key.py          # Fernet key generator
├── tests/                       # Test suite
│   ├── conftest.py              # Test fixtures
│   ├── test_models.py           # Model tests
│   ├── test_encryption.py       # Encryption tests
│   ├── test_api_*.py            # API tests
│   └── test_integration.py      # Integration tests
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt         # Development dependencies
├── .env.example
├── .gitignore
├── pytest.ini                   # Test configuration
├── Makefile                     # Common tasks
├── run.py                       # Development server
└── README.md
```

## Database Schema

### Clients Table

Stores client/domain configuration with encrypted Cloudflare credentials.

```sql
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    domain TEXT UNIQUE NOT NULL,
    cloudflare_account_id TEXT,
    cloudflare_api_token_encrypted BYTEA,  -- Encrypted with Fernet
    cloudflare_kv_namespace_id TEXT,
    gemini_api_key_encrypted BYTEA,        -- Optional per-client key
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Pages Table

Stores cached page content through the processing pipeline.

```sql
CREATE TABLE pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL,                -- SHA-256 of normalized URL
    content_hash TEXT,                     -- SHA-256 of raw HTML
    raw_html TEXT,                         -- Scraped content
    markdown_content TEXT,                 -- Gemini-processed
    simple_html TEXT,                      -- Generated minimal HTML
    last_scraped_at TIMESTAMPTZ,
    last_processed_at TIMESTAMPTZ,
    kv_uploaded_at TIMESTAMPTZ,
    kv_key TEXT,                           -- e.g., "https/example-com/page"
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(client_id, url)
);
```

### Visits Table

Tracks all visits for analytics and bot detection.

```sql
CREATE TABLE visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES pages(id) ON DELETE SET NULL,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    visitor_type TEXT,                     -- 'ai_bot', 'direct', 'worker_proxy'
    user_agent TEXT,
    ip_hash TEXT,                          -- Hashed for privacy
    referrer TEXT,
    bot_name TEXT,                         -- 'GPTBot', 'ClaudeBot', etc.
    visited_at TIMESTAMPTZ DEFAULT now()
);
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11 or higher
- Neon account and database
- Google Gemini API key
- Cloudflare account (for each client)

### 2. Create Neon Database

1. Go to [neon.tech](https://neon.tech) and create a new project
2. Wait for the database to be provisioned
3. Go to **Dashboard** → **Connection Details**
4. Copy the **Connection string** (it will look like: `postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require`)

### 3. Enable Required Extensions

In the Neon SQL Editor, run:

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

This enables `gen_random_uuid()` for UUID generation.

### 4. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-cache-layer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Generate a Fernet encryption key
python scripts/generate_key.py

# Edit .env and fill in your values
nano .env  # or use your preferred editor
```

**Required environment variables:**

```bash
# Flask
FLASK_ENV=development
SECRET_KEY=<generate-with-secrets-token-hex-32>
DEBUG=True

# Database (get from Neon)
DATABASE_URL=postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require

# API Keys
GEMINI_API_KEY=your-gemini-api-key
MASTER_API_KEY=<generate-with-secrets-token-urlsafe-32>

# Encryption
FERNET_KEY=<generated-from-scripts-generate-key-py>
```

### 6. Run Database Migrations

```bash
# Run Alembic migrations to create tables
alembic upgrade head
```

You should see output like:

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema, Initial schema with clients, pages, and visits tables
```

### 7. Generate Secure Keys

```bash
# Generate Fernet key
python scripts/generate_key.py

# Generate master API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate Flask secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

### 8. Add Your First Client

**Option A: Interactive script**

```bash
python scripts/add_client.py
```

**Option B: Using the API**

```bash
curl -X POST http://localhost:5000/api/v1/clients \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-master-api-key" \
  -d '{
    "name": "Example Corp",
    "domain": "example.com",
    "cloudflare_account_id": "your-cf-account-id",
    "cloudflare_api_token": "your-cf-api-token",
    "cloudflare_kv_namespace_id": "your-kv-namespace-id"
  }'
```

**Option C: Python code**

```python
from app.models.base import init_db, SessionLocal
from app.models.client import Client
from app.config import settings

# Initialize database
init_db(settings.get_database_url())

# Create client
db = SessionLocal()
client = Client(
    name="Example Corp",
    domain="example.com",
    cloudflare_account_id="your-account-id",
    cloudflare_kv_namespace_id="your-namespace-id",
    is_active=True
)

# Set encrypted fields (uses property setters)
client.cloudflare_api_token = "your-secret-token"
client.gemini_api_key = "your-optional-gemini-key"

db.add(client)
db.commit()
db.refresh(client)

print(f"Created client: {client.id}")
db.close()
```

## Running the Application

### Development

```bash
# Activate virtual environment
source venv/bin/activate

# Run development server
python run.py
```

The server will start on `http://0.0.0.0:5000`

### Production

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"

# With more workers and timeout
gunicorn -w 8 -b 0.0.0.0:5000 --timeout 120 "app:create_app()"
```

## Running Tests

The project includes comprehensive test coverage for all components.

### Quick Test Run

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term
```

### Using Make

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration
```

### Test Structure

- `tests/test_models.py` - Model tests (Client, Page, Visit)
- `tests/test_encryption.py` - Encryption service tests
- `tests/test_api_health.py` - Health check endpoint tests
- `tests/test_api_clients.py` - Client CRUD API tests
- `tests/test_middleware.py` - Authentication and bot detection tests
- `tests/test_integration.py` - Integration and workflow tests

### View Coverage Report

After running tests with coverage:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Current Coverage**: >85% across all modules

For detailed testing documentation, see [TESTING.md](TESTING.md).

## API Documentation

### Authentication

All `/api/v1/*` endpoints require API key authentication:

```bash
X-API-Key: your-master-api-key
```

### Endpoints

#### Health Check

```bash
GET /health
```

Response:

```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

#### List Clients

```bash
GET /api/v1/clients
Headers: X-API-Key: your-master-api-key
```

Response:

```json
{
  "clients": [
    {
      "id": "uuid",
      "name": "Example Corp",
      "domain": "example.com",
      "has_cloudflare_token": true,
      "is_active": true,
      ...
    }
  ],
  "count": 1
}
```

#### Get Client by ID

```bash
GET /api/v1/clients/{client_id}
Headers: X-API-Key: your-master-api-key

# Include decrypted secrets (use with caution)
GET /api/v1/clients/{client_id}?include_secrets=true
```

#### Get Client by Domain

```bash
GET /api/v1/clients/by-domain/{domain}
Headers: X-API-Key: your-master-api-key
```

### Sitemap Operations

#### Import Sitemap

Import all URLs from a sitemap into the database:

```bash
POST /api/v1/sitemap/import
Headers:
  X-API-Key: your-master-api-key
  Content-Type: application/json

Body:
{
  "client_id": "client-uuid",
  "sitemap_url": "https://example.com/sitemap.xml",
  "recursive": true,        // Follow sitemap indices (default: true)
  "max_depth": 3,           // Max recursion depth (default: 3)
  "create_pages": true,     // Create Page entries (default: true)
  "overwrite": false        // Overwrite existing pages (default: false)
}

Response:
{
  "message": "Sitemap imported successfully",
  "summary": {
    "total_urls": 150,
    "created": 145,
    "skipped": 5,
    "updated": 0,
    "errors": 0
  },
  "client": {
    "id": "...",
    "name": "Example Corp",
    "domain": "example.com"
  }
}
```

**Features:**
- Automatically detects sitemap index files and follows nested sitemaps
- Creates Page entries for all URLs found
- Skips duplicate URLs by default (set `overwrite: true` to update)
- Safety limit of 10,000 URLs per import
- Returns detailed summary of import results

#### Parse Sitemap (Preview)

Parse a sitemap without creating database entries (useful for previewing):

```bash
POST /api/v1/sitemap/parse
Headers:
  X-API-Key: your-master-api-key
  Content-Type: application/json

Body:
{
  "sitemap_url": "https://example.com/sitemap.xml",
  "recursive": true
}

Response:
{
  "sitemap_url": "https://example.com/sitemap.xml",
  "total_urls": 150,
  "urls": [
    {
      "loc": "https://example.com/page1",
      "lastmod": "2024-01-01",
      "priority": "0.8",
      "changefreq": "weekly"
    },
    ...
  ],
  "truncated": true  // If more than 100 URLs
}
```

#### List Client Pages

List all pages for a specific client:

```bash
GET /api/v1/sitemap/client/{client_id}/pages?limit=100&offset=0&has_content=false
Headers: X-API-Key: your-master-api-key

Query Parameters:
  - limit: Max pages to return (default: 100, max: 1000)
  - offset: Number of pages to skip (default: 0)
  - has_content: Filter by content presence (true/false)

Response:
{
  "client_id": "...",
  "client_name": "Example Corp",
  "total_pages": 150,
  "pages": [
    {
      "id": "...",
      "url": "https://example.com/page1",
      "has_raw_html": false,
      "last_scraped_at": null,
      "version": 1,
      ...
    }
  ],
  "limit": 100,
  "offset": 0
}
```

**Use cases:**
- View all pages that need scraping (`has_content=false`)
- View pages with cached content (`has_content=true`)
- Pagination for large page lists

#### Create Client

```bash
POST /api/v1/clients
Headers:
  X-API-Key: your-master-api-key
  Content-Type: application/json

Body:
{
  "name": "Example Corp",
  "domain": "example.com",
  "cloudflare_account_id": "abc123",
  "cloudflare_api_token": "secret-token",
  "cloudflare_kv_namespace_id": "kv123",
  "gemini_api_key": "optional-key",
  "is_active": true
}
```

#### Update Client

```bash
PUT /api/v1/clients/{client_id}
Headers:
  X-API-Key: your-master-api-key
  Content-Type: application/json

Body:
{
  "cloudflare_api_token": "new-token",
  "is_active": false
}
```

#### Delete Client

```bash
DELETE /api/v1/clients/{client_id}
Headers: X-API-Key: your-master-api-key
```

**Warning**: This will cascade delete all associated pages and visits.

## Security Best Practices

### Encryption

- All Cloudflare API tokens are encrypted at rest using Fernet
- Fernet key is loaded from environment variable (`FERNET_KEY`)
- **Never commit the Fernet key to version control**
- **If you lose the Fernet key, you cannot decrypt existing data**

### API Keys

- Master API key protects all client CRUD operations
- Use strong, randomly generated keys (at least 32 bytes)
- Rotate keys periodically
- Use different keys for development and production

### Database

- Neon provides automatic connection pooling and scaling
- Regularly backup your database (Neon provides automatic backups)
- Use SSL/TLS for database connections (enabled by default with Neon using sslmode=require)

### Production Deployment

1. Set `FLASK_ENV=production` and `DEBUG=False`
2. Use a production WSGI server (gunicorn, uwsgi)
3. Enable HTTPS (use Cloudflare or Let's Encrypt)
4. Set up proper logging and monitoring
5. Use environment-specific `.env` files
6. Never expose the master API key in client-side code

## Development

### Adding New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration in alembic/versions/
# Edit if necessary

# Apply migration
alembic upgrade head
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests (when implemented)
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## Troubleshooting

### Database Connection Issues

**Error**: `Could not connect to database`

**Solutions**:
1. Verify `DATABASE_URL` in `.env` is correct
2. Ensure your Neon database is running
3. Check if you're using the correct password
4. Verify network connectivity to Neon

### Migration Errors

**Error**: `relation "clients" already exists`

**Solutions**:
1. Check if tables were created manually
2. Drop all tables and re-run migrations:
   ```bash
   # In Neon SQL Editor
   DROP TABLE IF EXISTS visits CASCADE;
   DROP TABLE IF EXISTS pages CASCADE;
   DROP TABLE IF EXISTS clients CASCADE;

   # Then re-run
   alembic upgrade head
   ```

### Encryption Errors

**Error**: `cryptography.fernet.InvalidToken`

**Solutions**:
1. Verify `FERNET_KEY` in `.env` is correct
2. Ensure you're using the same key that encrypted the data
3. If data is not critical, generate a new key and re-encrypt

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'app'`

**Solutions**:
1. Ensure virtual environment is activated
2. Install dependencies: `pip install -r requirements.txt`
3. Check if you're in the correct directory

## Next Steps

After setup, you can extend this foundation with:

1. **Scraping service**: Implement web scraping with Playwright/Selenium
2. **Gemini processing**: Add Markdown conversion using Gemini API
3. **Cloudflare KV upload**: Implement KV storage for processed pages
4. **Worker integration**: Deploy Cloudflare Workers to serve cached content
5. **Bot detection**: Enhance AI bot detection and routing
6. **Analytics dashboard**: Build a UI for visit analytics
7. **Webhook notifications**: Add webhooks for page updates
8. **Rate limiting**: Implement rate limiting for API endpoints

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests and ensure they pass
5. Commit with clear messages: `git commit -m "Add feature X"`
6. Push to your fork: `git push origin feature-name`
7. Open a Pull Request

## License

MIT License - See LICENSE file for details

## Support

- Documentation: See this README
- Issues: Open an issue on GitHub
- Questions: Create a discussion on GitHub

## Acknowledgments

- Flask team for the excellent web framework
- Neon for serverless PostgreSQL hosting
- Google for Gemini API
- Cloudflare for Workers and KV storage
