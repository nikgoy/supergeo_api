# Setup Checklist

Use this checklist to ensure you've completed all setup steps correctly.

## Prerequisites

- [ ] Python 3.11+ installed
- [ ] Neon account created
- [ ] Google Gemini API key obtained
- [ ] Cloudflare account (for each client you'll add)

## Neon Setup

- [ ] Created new Neon project
- [ ] Database is fully provisioned
- [ ] Copied Connection String from Dashboard → Connection Details
- [ ] Enabled pgcrypto extension (`CREATE EXTENSION IF NOT EXISTS "pgcrypto";`)

## Local Setup

- [ ] Cloned repository
- [ ] Created virtual environment (`python3 -m venv venv`)
- [ ] Activated virtual environment
- [ ] Installed dependencies (`pip install -r requirements.txt`)
- [ ] Copied `.env.example` to `.env`

## Environment Configuration

- [ ] Set `DATABASE_URL` with correct Neon connection string
- [ ] Set `GEMINI_API_KEY`
- [ ] Generated and set `FERNET_KEY` (run `python scripts/generate_key.py`)
- [ ] Generated and set `MASTER_API_KEY`
- [ ] Generated and set `SECRET_KEY`
- [ ] Set `FLASK_ENV` to `development` or `production`

## Database Migration

- [ ] Ran `alembic upgrade head` successfully
- [ ] Verified tables created in Neon SQL Editor
- [ ] Tables visible: `clients`, `pages`, `visits`

## First Client

- [ ] Added first client (via script or API)
- [ ] Verified client appears in database
- [ ] Client has encrypted Cloudflare credentials

## Testing

- [ ] Server starts without errors (`python run.py`)
- [ ] Health endpoint responds: `curl http://localhost:5000/health`
- [ ] Ping endpoint responds: `curl http://localhost:5000/ping`
- [ ] Can list clients with API key: `curl -H "X-API-Key: your-key" http://localhost:5000/api/v1/clients`

## Security

- [ ] `.env` file is in `.gitignore`
- [ ] Strong passwords used for all keys
- [ ] Master API key is secure and not shared
- [ ] Fernet key is backed up securely
- [ ] Database credentials are not in code

## Production (if deploying)

- [ ] Set `FLASK_ENV=production`
- [ ] Set `DEBUG=False`
- [ ] Using gunicorn or production WSGI server
- [ ] HTTPS enabled
- [ ] Environment variables set on hosting platform
- [ ] Database connection pooling configured
- [ ] Monitoring and logging set up

## Next Steps

- [ ] Implement web scraping service
- [ ] Add Gemini processing integration
- [ ] Implement Cloudflare KV upload
- [ ] Deploy Cloudflare Workers
- [ ] Set up analytics dashboard
- [ ] Add comprehensive tests

---

**Date Completed**: _______________

**Notes**:
