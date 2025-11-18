"""
Tests for database models.

Tests for Client, Page, and Visit models including encryption.
"""
import pytest
from datetime import datetime
from uuid import UUID

from app.models.client import Client, Page, Visit


class TestClientModel:
    """Test Client model."""

    def test_create_client(self, db):
        """Test creating a basic client."""
        client = Client(
            name='Example Corp',
            domain='example.com',
            is_active=True
        )

        db.add(client)
        db.commit()
        db.refresh(client)

        assert client.id is not None
        assert isinstance(client.id, UUID)
        assert client.name == 'Example Corp'
        assert client.domain == 'example.com'
        assert client.is_active is True
        assert client.created_at is not None
        assert client.updated_at is not None

    def test_client_unique_name(self, db, sample_client):
        """Test that client name must be unique."""
        duplicate = Client(
            name=sample_client.name,  # Same name
            domain='different.com'
        )

        db.add(duplicate)

        with pytest.raises(Exception):  # IntegrityError
            db.commit()

    def test_client_unique_domain(self, db, sample_client):
        """Test that client domain must be unique."""
        duplicate = Client(
            name='Different Corp',
            domain=sample_client.domain  # Same domain
        )

        db.add(duplicate)

        with pytest.raises(Exception):  # IntegrityError
            db.commit()

    def test_client_cloudflare_token_encryption(self, db):
        """Test Cloudflare API token encryption/decryption."""
        client = Client(
            name='Test Corp',
            domain='test.com'
        )

        # Set encrypted field using property
        client.cloudflare_api_token = 'super-secret-token-123'

        db.add(client)
        db.commit()
        db.refresh(client)

        # Raw field should be encrypted bytes
        assert client.cloudflare_api_token_encrypted is not None
        assert isinstance(client.cloudflare_api_token_encrypted, bytes)
        assert b'super-secret-token-123' not in client.cloudflare_api_token_encrypted

        # Property should decrypt
        assert client.cloudflare_api_token == 'super-secret-token-123'

    def test_client_gemini_key_encryption(self, db):
        """Test Gemini API key encryption/decryption."""
        client = Client(
            name='Test Corp',
            domain='test.com'
        )

        client.gemini_api_key = 'gemini-api-key-xyz'

        db.add(client)
        db.commit()
        db.refresh(client)

        # Raw field should be encrypted
        assert client.gemini_api_key_encrypted is not None
        assert isinstance(client.gemini_api_key_encrypted, bytes)

        # Property should decrypt
        assert client.gemini_api_key == 'gemini-api-key-xyz'

    def test_client_optional_fields_null(self, db):
        """Test that optional encrypted fields can be None."""
        client = Client(
            name='Test Corp',
            domain='test.com'
        )

        # Don't set encrypted fields
        db.add(client)
        db.commit()
        db.refresh(client)

        assert client.cloudflare_api_token is None
        assert client.cloudflare_api_token_encrypted is None
        assert client.gemini_api_key is None
        assert client.gemini_api_key_encrypted is None

    def test_client_to_dict(self, sample_client):
        """Test client to_dict method."""
        data = sample_client.to_dict()

        assert 'id' in data
        assert 'name' in data
        assert 'domain' in data
        assert data['name'] == 'Test Corp'
        assert data['domain'] == 'test.com'

        # Should not include decrypted secrets by default
        assert 'cloudflare_api_token' not in data
        assert 'gemini_api_key' not in data

        # Should include flags
        assert data['has_cloudflare_token'] is True
        assert data['has_gemini_key'] is True

    def test_client_to_dict_include_secrets(self, sample_client):
        """Test client to_dict with include_secrets=True."""
        data = sample_client.to_dict(include_secrets=True)

        assert 'cloudflare_api_token' in data
        assert data['cloudflare_api_token'] == 'test-cloudflare-token'
        assert 'gemini_api_key' in data
        assert data['gemini_api_key'] == 'test-gemini-key'

    def test_client_repr(self, sample_client):
        """Test client __repr__ method."""
        repr_str = repr(sample_client)
        assert 'Test Corp' in repr_str
        assert 'test.com' in repr_str

    def test_client_cascade_delete_pages(self, db, sample_client, sample_page):
        """Test that deleting client cascades to pages."""
        client_id = sample_client.id
        page_id = sample_page.id

        # Delete client
        db.delete(sample_client)
        db.commit()

        # Page should be deleted
        page = db.query(Page).filter(Page.id == page_id).first()
        assert page is None


class TestPageModel:
    """Test Page model."""

    def test_create_page(self, db, sample_client):
        """Test creating a basic page."""
        page = Page(
            client_id=sample_client.id,
            url='https://example.com/test',
            url_hash=Page.compute_url_hash('https://example.com/test'),
            raw_html='<html>test</html>'
        )

        db.add(page)
        db.commit()
        db.refresh(page)

        assert page.id is not None
        assert isinstance(page.id, UUID)
        assert page.url == 'https://example.com/test'
        assert page.version == 1

    def test_page_unique_client_url(self, db, sample_client, sample_page):
        """Test that client_id + url must be unique."""
        duplicate = Page(
            client_id=sample_client.id,
            url=sample_page.url,  # Same URL for same client
            url_hash=Page.compute_url_hash(sample_page.url)
        )

        db.add(duplicate)

        with pytest.raises(Exception):  # IntegrityError
            db.commit()

    def test_compute_url_hash(self):
        """Test URL hash computation."""
        url1 = 'https://example.com/page'
        url2 = 'https://example.com/page'
        url3 = 'https://example.com/other'

        hash1 = Page.compute_url_hash(url1)
        hash2 = Page.compute_url_hash(url2)
        hash3 = Page.compute_url_hash(url3)

        # Same URL should produce same hash
        assert hash1 == hash2

        # Different URL should produce different hash
        assert hash1 != hash3

        # Hash should be hex string
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars

    def test_compute_content_hash(self):
        """Test content hash computation."""
        content1 = '<html>test</html>'
        content2 = '<html>test</html>'
        content3 = '<html>other</html>'

        hash1 = Page.compute_content_hash(content1)
        hash2 = Page.compute_content_hash(content2)
        hash3 = Page.compute_content_hash(content3)

        assert hash1 == hash2
        assert hash1 != hash3
        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_update_url_hash(self, db, sample_client):
        """Test update_url_hash method."""
        page = Page(
            client_id=sample_client.id,
            url='https://example.com/test',
            url_hash=''  # Empty initially
        )

        page.update_url_hash()

        expected_hash = Page.compute_url_hash('https://example.com/test')
        assert page.url_hash == expected_hash

    def test_update_content_hash(self, db, sample_client):
        """Test update_content_hash method."""
        page = Page(
            client_id=sample_client.id,
            url='https://example.com/test',
            url_hash=Page.compute_url_hash('https://example.com/test'),
            raw_html='<html>content</html>'
        )

        page.update_content_hash()

        expected_hash = Page.compute_content_hash('<html>content</html>')
        assert page.content_hash == expected_hash

    def test_update_content_hash_no_html(self, db, sample_client):
        """Test update_content_hash with no raw_html."""
        page = Page(
            client_id=sample_client.id,
            url='https://example.com/test',
            url_hash=Page.compute_url_hash('https://example.com/test'),
            raw_html=None
        )

        page.update_content_hash()

        assert page.content_hash is None

    def test_page_to_dict(self, sample_page):
        """Test page to_dict method."""
        data = sample_page.to_dict()

        assert 'id' in data
        assert 'url' in data
        assert data['url'] == 'https://test.com/page1'

        # Should include flags, not full content
        assert data['has_raw_html'] is True
        assert data['has_markdown'] is True
        assert data['has_simple_html'] is True

        # Should not include large fields by default
        assert 'raw_html' not in data
        assert 'markdown_content' not in data
        assert 'simple_html' not in data

    def test_page_relationship_to_client(self, sample_page, sample_client):
        """Test page -> client relationship."""
        assert sample_page.client == sample_client
        assert sample_page.client.name == 'Test Corp'


class TestVisitModel:
    """Test Visit model."""

    def test_create_visit(self, db, sample_client, sample_page):
        """Test creating a basic visit."""
        visit = Visit(
            page_id=sample_page.id,
            client_id=sample_client.id,
            url=sample_page.url,
            visitor_type='ai_bot',
            user_agent='GPTBot/1.0',
            bot_name='GPTBot'
        )

        db.add(visit)
        db.commit()
        db.refresh(visit)

        assert visit.id is not None
        assert isinstance(visit.id, UUID)
        assert visit.visitor_type == 'ai_bot'
        assert visit.bot_name == 'GPTBot'
        assert visit.visited_at is not None

    def test_visit_without_page(self, db, sample_client):
        """Test creating visit without page_id (nullable)."""
        visit = Visit(
            page_id=None,  # No page association
            client_id=sample_client.id,
            url='https://test.com/unknown',
            visitor_type='direct'
        )

        db.add(visit)
        db.commit()
        db.refresh(visit)

        assert visit.id is not None
        assert visit.page_id is None

    def test_hash_ip(self):
        """Test IP address hashing."""
        ip1 = '192.168.1.1'
        ip2 = '192.168.1.1'
        ip3 = '192.168.1.2'

        hash1 = Visit.hash_ip(ip1)
        hash2 = Visit.hash_ip(ip2)
        hash3 = Visit.hash_ip(ip3)

        # Same IP should produce same hash
        assert hash1 == hash2

        # Different IP should produce different hash
        assert hash1 != hash3

        # Hash should not contain original IP
        assert '192.168.1.1' not in hash1

        # Hash should be hex string
        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_visit_to_dict(self, sample_visit):
        """Test visit to_dict method."""
        data = sample_visit.to_dict()

        assert 'id' in data
        assert 'url' in data
        assert 'visitor_type' in data
        assert 'bot_name' in data
        assert data['visitor_type'] == 'ai_bot'
        assert data['bot_name'] == 'GPTBot'

    def test_visit_relationship_to_client(self, sample_visit, sample_client):
        """Test visit -> client relationship."""
        assert sample_visit.client == sample_client
        assert sample_visit.client.name == 'Test Corp'

    def test_visit_relationship_to_page(self, sample_visit, sample_page):
        """Test visit -> page relationship."""
        assert sample_visit.page == sample_page
        assert sample_visit.page.url == sample_page.url

    def test_visit_cascade_delete_with_page(self, db, sample_visit, sample_page):
        """Test that deleting page sets visit.page_id to NULL."""
        visit_id = sample_visit.id

        # Delete page
        db.delete(sample_page)
        db.commit()

        # Visit should still exist but page_id should be NULL
        visit = db.query(Visit).filter(Visit.id == visit_id).first()
        assert visit is not None
        assert visit.page_id is None
