"""
Database models for clients, pages, and visits.

All models use UUID primary keys and include timestamps.
Sensitive fields are encrypted at rest using Fernet.
"""
import hashlib
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    LargeBinary, String, Text, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.services.encryption import encryption_service


class Client(Base):
    """
    Client/domain configuration.

    Each client represents a website/domain with its own Cloudflare credentials.
    Cloudflare secrets are encrypted at rest.
    """

    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, unique=True, nullable=False, index=True)
    domain = Column(Text, unique=True, nullable=False, index=True)

    # Cloudflare configuration (encrypted)
    cloudflare_account_id = Column(Text, nullable=True)
    cloudflare_api_token_encrypted = Column(LargeBinary, nullable=True)
    cloudflare_kv_namespace_id = Column(Text, nullable=True)

    # Optional per-client Gemini API key (encrypted)
    gemini_api_key_encrypted = Column(LargeBinary, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=datetime.utcnow)

    # Relationships
    pages = relationship("Page", back_populates="client", cascade="all, delete-orphan")
    visits = relationship("Visit", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Client {self.name} ({self.domain})>"

    # Encrypted properties for Cloudflare API Token

    @property
    def cloudflare_api_token(self) -> Optional[str]:
        """Decrypt and return Cloudflare API token."""
        if self.cloudflare_api_token_encrypted is None:
            return None
        return encryption_service.decrypt(self.cloudflare_api_token_encrypted)

    @cloudflare_api_token.setter
    def cloudflare_api_token(self, value: Optional[str]) -> None:
        """Encrypt and store Cloudflare API token."""
        if value is None:
            self.cloudflare_api_token_encrypted = None
        else:
            self.cloudflare_api_token_encrypted = encryption_service.encrypt(value)

    # Encrypted properties for Gemini API Key

    @property
    def gemini_api_key(self) -> Optional[str]:
        """Decrypt and return Gemini API key."""
        if self.gemini_api_key_encrypted is None:
            return None
        return encryption_service.decrypt(self.gemini_api_key_encrypted)

    @gemini_api_key.setter
    def gemini_api_key(self, value: Optional[str]) -> None:
        """Encrypt and store Gemini API key."""
        if value is None:
            self.gemini_api_key_encrypted = None
        else:
            self.gemini_api_key_encrypted = encryption_service.encrypt(value)

    def to_dict(self, include_secrets: bool = False) -> dict:
        """
        Convert client to dictionary.

        Args:
            include_secrets: If True, include decrypted secrets (use with caution)

        Returns:
            Dictionary representation
        """
        data = {
            "id": str(self.id),
            "name": self.name,
            "domain": self.domain,
            "cloudflare_account_id": self.cloudflare_account_id,
            "cloudflare_kv_namespace_id": self.cloudflare_kv_namespace_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_secrets:
            data["cloudflare_api_token"] = self.cloudflare_api_token
            data["gemini_api_key"] = self.gemini_api_key
        else:
            data["has_cloudflare_token"] = self.cloudflare_api_token_encrypted is not None
            data["has_gemini_key"] = self.gemini_api_key_encrypted is not None

        return data


class Page(Base):
    """
    Cached page content.

    Stores the complete pipeline: raw HTML → Markdown → simple HTML → KV storage.
    """

    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("client_id", "url", name="uq_client_url"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)

    url = Column(Text, nullable=False, index=True)
    url_hash = Column(Text, nullable=False, index=True)  # SHA-256 of normalized URL
    content_hash = Column(Text, nullable=True)  # SHA-256 of raw HTML for change detection

    # Content at various stages
    raw_html = Column(Text, nullable=True)
    markdown_content = Column(Text, nullable=True)
    simple_html = Column(Text, nullable=True)

    # Processing timestamps
    last_scraped_at = Column(DateTime, nullable=True)
    last_processed_at = Column(DateTime, nullable=True)
    kv_uploaded_at = Column(DateTime, nullable=True)

    # Cloudflare KV metadata
    kv_key = Column(Text, nullable=True)  # e.g., "https/example-com/page"
    version = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="pages")
    visits = relationship("Visit", back_populates="page", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Page {self.url}>"

    @staticmethod
    def compute_url_hash(url: str) -> str:
        """
        Compute SHA-256 hash of normalized URL.

        Args:
            url: URL to hash

        Returns:
            Hex digest of SHA-256 hash
        """
        normalized = url.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """
        Compute SHA-256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def update_url_hash(self) -> None:
        """Update url_hash based on current url."""
        self.url_hash = self.compute_url_hash(self.url)

    def update_content_hash(self) -> None:
        """Update content_hash based on current raw_html."""
        if self.raw_html:
            self.content_hash = self.compute_content_hash(self.raw_html)
        else:
            self.content_hash = None

    def to_dict(self) -> dict:
        """
        Convert page to dictionary.

        Returns:
            Dictionary representation (excluding large content fields by default)
        """
        return {
            "id": str(self.id),
            "client_id": str(self.client_id),
            "url": self.url,
            "url_hash": self.url_hash,
            "content_hash": self.content_hash,
            "has_raw_html": self.raw_html is not None,
            "has_markdown": self.markdown_content is not None,
            "has_simple_html": self.simple_html is not None,
            "last_scraped_at": self.last_scraped_at.isoformat() if self.last_scraped_at else None,
            "last_processed_at": self.last_processed_at.isoformat() if self.last_processed_at else None,
            "kv_uploaded_at": self.kv_uploaded_at.isoformat() if self.kv_uploaded_at else None,
            "kv_key": self.kv_key,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Visit(Base):
    """
    Visit tracking for analytics.

    Tracks both AI bot visits and direct user visits.
    IP addresses are hashed for privacy.
    """

    __tablename__ = "visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id", ondelete="SET NULL"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)

    url = Column(Text, nullable=False)
    visitor_type = Column(String(50), nullable=True)  # 'ai_bot', 'direct', 'worker_proxy'
    user_agent = Column(Text, nullable=True)
    ip_hash = Column(Text, nullable=True)  # Hashed IP for privacy
    referrer = Column(Text, nullable=True)
    bot_name = Column(Text, nullable=True)  # e.g., 'GPTBot', 'ClaudeBot', 'Googlebot'

    visited_at = Column(DateTime, nullable=False, server_default=text("now()"))

    # Relationships
    client = relationship("Client", back_populates="visits")
    page = relationship("Page", back_populates="visits")

    def __repr__(self) -> str:
        return f"<Visit {self.visitor_type} @ {self.url}>"

    @staticmethod
    def hash_ip(ip: str) -> str:
        """
        Hash IP address for privacy.

        Args:
            ip: IP address to hash

        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(ip.encode()).hexdigest()

    def to_dict(self) -> dict:
        """
        Convert visit to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": str(self.id),
            "page_id": str(self.page_id) if self.page_id else None,
            "client_id": str(self.client_id),
            "url": self.url,
            "visitor_type": self.visitor_type,
            "user_agent": self.user_agent,
            "ip_hash": self.ip_hash,
            "referrer": self.referrer,
            "bot_name": self.bot_name,
            "visited_at": self.visited_at.isoformat() if self.visited_at else None,
        }
