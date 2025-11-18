"""Middleware package."""
from app.middleware.auth import require_api_key

__all__ = ["require_api_key"]
