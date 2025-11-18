#!/usr/bin/env python3
"""
Generate a new Fernet encryption key.

Usage:
    python scripts/generate_key.py
"""
from cryptography.fernet import Fernet


def main():
    """Generate and print a new Fernet key."""
    key = Fernet.generate_key().decode()

    print()
    print("=" * 70)
    print("New Fernet Encryption Key Generated")
    print("=" * 70)
    print()
    print("Add this to your .env file:")
    print()
    print(f"FERNET_KEY={key}")
    print()
    print("⚠️  IMPORTANT: Keep this key secure!")
    print("   • Never commit it to version control")
    print("   • Never share it publicly")
    print("   • If you lose it, you cannot decrypt existing data")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
