"""API blueprints package."""
from app.api.health import health_bp
from app.api.clients import clients_bp

__all__ = ["health_bp", "clients_bp"]
