"""
Application configuration using pydantic-settings.

All secrets and configuration are loaded from environment variables.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Flask settings
    flask_env: str = Field(default="production", description="Flask environment")
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="Flask secret key")
    debug: bool = Field(default=False, description="Debug mode")

    # Database settings
    database_url: str = Field(..., description="PostgreSQL connection URL (Neon)")

    # API Keys
    gemini_api_key: str = Field(..., description="Google Gemini API key (global fallback)")
    master_api_key: str = Field(..., description="Master API key for client CRUD operations")

    # Encryption
    fernet_key: str = Field(..., description="Fernet encryption key (32 url-safe base64 bytes)")

    # Application settings
    max_workers: int = Field(default=4, description="Max concurrent workers for async operations")
    page_timeout: int = Field(default=30, description="Timeout for page scraping in seconds")

    @field_validator("flask_env")
    @classmethod
    def validate_flask_env(cls, v: str) -> str:
        """Validate Flask environment."""
        if v not in ["development", "production", "testing"]:
            raise ValueError("flask_env must be development, production, or testing")
        return v

    @field_validator("fernet_key")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        """Validate Fernet key format."""
        try:
            from cryptography.fernet import Fernet
            Fernet(v.encode())
        except Exception as e:
            raise ValueError(f"Invalid Fernet key format: {e}")
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.flask_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.flask_env == "production"

    def get_database_url(self) -> str:
        """
        Get the database URL for SQLAlchemy.

        Returns the Neon PostgreSQL connection URL.
        """
        return self.database_url


# Global settings instance
settings = Settings()
