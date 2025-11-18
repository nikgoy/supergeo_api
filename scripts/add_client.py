#!/usr/bin/env python3
"""
Helper script to add a new client to the database.

Usage:
    python scripts/add_client.py

This script will prompt you for client information and add it to the database.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.models.base import init_db, SessionLocal
from app.models.client import Client
from app.config import settings


def prompt(message: str, required: bool = True, default: str = None) -> str:
    """Prompt user for input."""
    while True:
        if default:
            value = input(f"{message} [{default}]: ").strip()
            if not value:
                return default
        else:
            value = input(f"{message}: ").strip()

        if value or not required:
            return value
        print("This field is required. Please enter a value.")


def confirm(message: str) -> bool:
    """Ask for yes/no confirmation."""
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'")


def main():
    """Main function."""
    print("=" * 70)
    print("AI Cache Layer - Add New Client")
    print("=" * 70)
    print()

    # Initialize database
    try:
        database_url = settings.get_database_url()
        init_db(database_url)
        print("✓ Database connection established\n")
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        print("\nPlease ensure:")
        print("  1. DATABASE_URL is set in your .env file")
        print("  2. The database is accessible")
        print("  3. You've run the Alembic migrations")
        sys.exit(1)

    # Collect client information
    print("Enter client information:")
    print("-" * 70)

    name = prompt("Client name (e.g., 'Example Corp')", required=True)
    domain = prompt("Domain (e.g., 'example.com')", required=True)

    print("\nCloudflare configuration (optional - can be added later):")
    add_cloudflare = confirm("Do you want to add Cloudflare credentials now?")

    cloudflare_account_id = None
    cloudflare_api_token = None
    cloudflare_kv_namespace_id = None

    if add_cloudflare:
        cloudflare_account_id = prompt("Cloudflare Account ID", required=False)
        cloudflare_api_token = prompt("Cloudflare API Token", required=False)
        cloudflare_kv_namespace_id = prompt("Cloudflare KV Namespace ID", required=False)

    print("\nGemini API configuration (optional):")
    add_gemini = confirm("Do you want to add a per-client Gemini API key?")
    gemini_api_key = None

    if add_gemini:
        gemini_api_key = prompt("Gemini API Key", required=False)

    is_active = confirm("\nShould this client be active?")

    # Confirmation
    print("\n" + "=" * 70)
    print("Client Summary:")
    print("-" * 70)
    print(f"Name: {name}")
    print(f"Domain: {domain}")
    print(f"Cloudflare Account ID: {cloudflare_account_id or '(not set)'}")
    print(f"Cloudflare API Token: {'***' if cloudflare_api_token else '(not set)'}")
    print(f"Cloudflare KV Namespace ID: {cloudflare_kv_namespace_id or '(not set)'}")
    print(f"Gemini API Key: {'***' if gemini_api_key else '(not set)'}")
    print(f"Active: {is_active}")
    print("=" * 70)
    print()

    if not confirm("Create this client?"):
        print("Cancelled.")
        sys.exit(0)

    # Create client
    db = SessionLocal()
    try:
        client = Client(
            name=name,
            domain=domain,
            cloudflare_account_id=cloudflare_account_id,
            cloudflare_kv_namespace_id=cloudflare_kv_namespace_id,
            is_active=is_active
        )

        # Set encrypted fields
        if cloudflare_api_token:
            client.cloudflare_api_token = cloudflare_api_token

        if gemini_api_key:
            client.gemini_api_key = gemini_api_key

        db.add(client)
        db.commit()
        db.refresh(client)

        print()
        print("✓ Client created successfully!")
        print()
        print(f"Client ID: {client.id}")
        print(f"Created at: {client.created_at}")
        print()
        print("You can now use this client with the API.")
        print()

    except Exception as e:
        db.rollback()
        print()
        print(f"✗ Failed to create client: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()
