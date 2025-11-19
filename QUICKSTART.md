# Quick Start Guide

Get up and running in 5 minutes!

## 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Set Up Neon

Go to [neon.tech](https://neon.tech) and:

1. Create a new project
2. Wait for it to provision
3. Go to SQL Editor and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   ```
4. Get your connection string:
   - Dashboard → Connection Details: Copy the full connection string

## 3. Configure Environment

```bash
# Copy example
cp .env.example .env

# Generate keys
python scripts/generate_key.py  # Copy the output to FERNET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"  # Copy to MASTER_API_KEY
python -c "import secrets; print(secrets.token_hex(32))"  # Copy to SECRET_KEY

# Edit .env
nano .env
```

Required values in `.env`:
```bash
DATABASE_URL=postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require
GEMINI_API_KEY=your-gemini-key
FERNET_KEY=generated-from-script
MASTER_API_KEY=generated-token
SECRET_KEY=generated-hex
```

## 4. Run Migrations

```bash
alembic upgrade head
```

You should see: `Running upgrade  -> 001_initial_schema`

## 5. Add First Client

```bash
python scripts/add_client.py
```

Follow the prompts to enter:
- Client name (e.g., "Example Corp")
- Domain (e.g., "example.com")
- Cloudflare credentials (optional, can add later)

## 6. Start Server

```bash
python run.py
```

The server will start on `http://0.0.0.0:5000`

## 7. Test It

```bash
# Health check (no auth required)
curl http://localhost:5000/health

# List clients (requires API key)
curl -H "X-API-Key: your-master-api-key" \
  http://localhost:5000/api/v1/clients
```

## What's Next?

- Read the full [README.md](README.md) for detailed documentation
- Explore the API endpoints in [README.md#api-documentation](README.md#api-documentation)
- Check [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) to ensure everything is configured
- Start building the scraping and processing pipeline

## Common Issues

**Database connection fails**
- Verify DATABASE_URL has the correct password
- Check if Neon database is running
- Ensure pgcrypto extension is enabled

**Import errors**
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again

**Alembic migration fails**
- Check if tables already exist (drop them and retry)
- Verify DATABASE_URL is correct
- Ensure database user has CREATE permissions

## Need Help?

- Check [README.md](README.md#troubleshooting) for detailed troubleshooting
- Review [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) to ensure you didn't miss a step
- Open an issue on GitHub
