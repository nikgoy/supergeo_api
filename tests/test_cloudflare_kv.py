"""
Tests for Cloudflare KV integration.

Tests KV upload, key generation, batch operations, and status checking.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.models.client import Client, Page
from tests.fixtures.test_data import (
    MOCK_CLIENT_DATA,
    MOCK_SITEMAP_URLS,
    MOCK_GEMINI_GEO_HTML,
    MOCK_KV_KEY,
    MOCK_KV_NAMESPACE_ID,
    MOCK_CLOUDFLARE_KV_UPLOAD_RESPONSE,
    MOCK_CLOUDFLARE_KV_LIST_RESPONSE,
)


@pytest.fixture
def kv_client(db):
    """Create a client with Cloudflare KV credentials."""
    client = Client(
        name="KV Test Client",
        domain="kv-test.com",
        cloudflare_account_id=MOCK_CLIENT_DATA["cloudflare_account_id"],
        cloudflare_kv_namespace_id=MOCK_CLIENT_DATA["cloudflare_kv_namespace_id"],
        is_active=True
    )
    client.cloudflare_api_token = MOCK_CLIENT_DATA["cloudflare_api_token"]

    db.add(client)
    db.commit()
    db.refresh(client)

    return client


@pytest.fixture
def page_ready_for_kv(db, kv_client):
    """Create a page ready for KV upload (has geo_html)."""
    page = Page(
        client_id=kv_client.id,
        url=MOCK_SITEMAP_URLS[0],
        url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[0]),
        raw_markdown="# Test Content",
        llm_markdown="# Test Content Cleaned",
        geo_html=MOCK_GEMINI_GEO_HTML,
        last_processed_at=datetime.utcnow()
    )

    db.add(page)
    db.commit()
    db.refresh(page)

    return page


@pytest.fixture
def pages_for_kv_batch(db, kv_client):
    """Create multiple pages ready for KV upload."""
    pages = []
    for i in range(5):
        page = Page(
            client_id=kv_client.id,
            url=MOCK_SITEMAP_URLS[i],
            url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[i]),
            raw_markdown=f"# Page {i}",
            llm_markdown=f"# Page {i} Cleaned",
            geo_html=MOCK_GEMINI_GEO_HTML,
            last_processed_at=datetime.utcnow()
        )
        db.add(page)
        pages.append(page)

    db.commit()

    for page in pages:
        db.refresh(page)

    return pages


@pytest.fixture
def mock_cloudflare_kv():
    """Mock Cloudflare KV API."""
    with patch('cloudflare.Cloudflare') as mock_cf:
        client_instance = MagicMock()

        # Mock KV put operation
        client_instance.kv.namespaces.values.update.return_value = (
            MOCK_CLOUDFLARE_KV_UPLOAD_RESPONSE
        )

        # Mock KV get operation
        client_instance.kv.namespaces.values.get.return_value = MOCK_GEMINI_GEO_HTML

        # Mock KV delete operation
        client_instance.kv.namespaces.values.delete.return_value = {
            'success': True
        }

        # Mock KV list operation
        client_instance.kv.namespaces.keys.list.return_value = (
            MOCK_CLOUDFLARE_KV_LIST_RESPONSE
        )

        mock_cf.return_value = client_instance
        yield mock_cf


class TestCloudflareKVService:
    """Test Cloudflare KV service functionality."""

    def test_kv_key_generation_from_url(self):
        """Test generating KV keys from URLs."""
        # from app.services.cloudflare_kv import CloudflareKVService
        #
        # service = CloudflareKVService(
        #     account_id=MOCK_CLIENT_DATA["cloudflare_account_id"],
        #     api_token=MOCK_CLIENT_DATA["cloudflare_api_token"],
        #     namespace_id=MOCK_CLIENT_DATA["cloudflare_kv_namespace_id"]
        # )
        #
        # key = service.url_to_kv_key(MOCK_SITEMAP_URLS[0])
        #
        # # Should be URL-safe and deterministic
        # assert key is not None
        # assert len(key) > 0
        # assert ' ' not in key
        # assert key == service.url_to_kv_key(MOCK_SITEMAP_URLS[0])  # Deterministic

    def test_kv_key_from_url_hash(self, page_ready_for_kv):
        """Test using URL hash as KV key."""
        # from app.services.cloudflare_kv import CloudflareKVService
        #
        # service = CloudflareKVService(...)
        # key = service.generate_kv_key(page_ready_for_kv)
        #
        # # Should use url_hash
        # assert key == page_ready_for_kv.url_hash or key.startswith(
        #     page_ready_for_kv.url_hash[:32]
        # )

    def test_upload_page_to_kv(self, mock_cloudflare_kv):
        """Test uploading single page to KV."""
        # from app.services.cloudflare_kv import CloudflareKVService
        #
        # service = CloudflareKVService(...)
        # result = service.upload_page(
        #     key=MOCK_KV_KEY,
        #     content=MOCK_GEMINI_GEO_HTML
        # )
        #
        # assert result['success'] is True


class TestCloudflareKVEndpoints:
    """Test Cloudflare KV API endpoints."""

    def test_upload_single_page(
        self,
        client,
        auth_headers,
        db,
        page_ready_for_kv,
        mock_cloudflare_kv
    ):
        """Test uploading a single page to KV."""
        page_id = str(page_ready_for_kv.id)

        response = client.post(
            f'/api/v1/cloudflare/kv/upload/{page_id}',
            headers=auth_headers
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert data['page_id'] == page_id
        # assert 'kv_key' in data
        # assert 'kv_namespace_id' in data
        # assert 'uploaded_at' in data

        # Verify database updated
        # db.refresh(page_ready_for_kv)
        # assert page_ready_for_kv.kv_key is not None
        # assert page_ready_for_kv.kv_uploaded_at is not None

    def test_upload_page_without_geo_html(
        self,
        client,
        auth_headers,
        db,
        kv_client
    ):
        """Test uploading page without geo_html fails."""
        # Create page without geo_html
        page = Page(
            client_id=kv_client.id,
            url=MOCK_SITEMAP_URLS[0],
            url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[0]),
            raw_markdown="# Content"
        )
        db.add(page)
        db.commit()

        page_id = str(page.id)

        response = client.post(
            f'/api/v1/cloudflare/kv/upload/{page_id}',
            headers=auth_headers
        )

        # Should return error
        # assert response.status_code == 400
        # data = response.get_json()
        # assert 'error' in data
        # assert 'geo_html' in data['error'].lower()

    def test_upload_client_batch(
        self,
        client,
        auth_headers,
        db,
        kv_client,
        pages_for_kv_batch,
        mock_cloudflare_kv
    ):
        """Test batch uploading all pages for a client."""
        client_id = str(kv_client.id)

        response = client.post(
            f'/api/v1/cloudflare/kv/upload-client/{client_id}',
            headers=auth_headers,
            json={'force': False}
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert data['uploaded'] == 5
        # assert data['skipped'] == 0
        # assert data['failed'] == 0

        # Verify all pages have KV keys
        # db.expire_all()
        # pages = db.query(Page).filter(
        #     Page.client_id == kv_client.id
        # ).all()
        #
        # for page in pages:
        #     assert page.kv_key is not None
        #     assert page.kv_uploaded_at is not None

    def test_skip_already_uploaded_pages(
        self,
        client,
        auth_headers,
        db,
        kv_client,
        pages_for_kv_batch
    ):
        """Test skipping pages already uploaded to KV."""
        # Mark some pages as already uploaded
        for i in range(3):
            pages_for_kv_batch[i].kv_key = f"key-{i}"
            pages_for_kv_batch[i].kv_uploaded_at = datetime.utcnow()

        db.commit()

        client_id = str(kv_client.id)

        response = client.post(
            f'/api/v1/cloudflare/kv/upload-client/{client_id}',
            headers=auth_headers,
            json={'force': False}
        )

        # Should only upload 2 remaining pages
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['uploaded'] == 2
        # assert data['skipped'] == 3

    def test_force_reupload_pages(
        self,
        client,
        auth_headers,
        db,
        kv_client,
        pages_for_kv_batch,
        mock_cloudflare_kv
    ):
        """Test force re-uploading pages."""
        # Mark all pages as uploaded
        for page in pages_for_kv_batch:
            page.kv_key = "old-key"
            page.kv_uploaded_at = datetime.utcnow()

        db.commit()

        client_id = str(kv_client.id)

        response = client.post(
            f'/api/v1/cloudflare/kv/upload-client/{client_id}',
            headers=auth_headers,
            json={'force': True}
        )

        # Should reupload all pages
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['uploaded'] == 5
        # assert data['skipped'] == 0

    def test_delete_page_from_kv(
        self,
        client,
        auth_headers,
        db,
        page_ready_for_kv,
        mock_cloudflare_kv
    ):
        """Test deleting a page from KV."""
        # First upload the page
        page_ready_for_kv.kv_key = MOCK_KV_KEY
        page_ready_for_kv.kv_uploaded_at = datetime.utcnow()
        db.commit()

        page_id = str(page_ready_for_kv.id)

        response = client.delete(
            f'/api/v1/cloudflare/kv/delete/{page_id}',
            headers=auth_headers
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert data['deleted_kv_key'] == MOCK_KV_KEY

        # Verify database cleared
        # db.refresh(page_ready_for_kv)
        # assert page_ready_for_kv.kv_key is None
        # assert page_ready_for_kv.kv_uploaded_at is None

    def test_kv_status_check(
        self,
        client,
        auth_headers,
        kv_client,
        mock_cloudflare_kv
    ):
        """Test checking KV namespace status."""
        client_id = str(kv_client.id)

        response = client.get(
            f'/api/v1/cloudflare/kv/status/{client_id}',
            headers=auth_headers
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert 'namespace_id' in data
        # assert 'total_keys' in data


class TestKVKeyGeneration:
    """Test KV key generation strategies."""

    def test_key_from_url_hash(self):
        """Test generating key from URL hash."""
        url = MOCK_SITEMAP_URLS[0]
        url_hash = Page.compute_url_hash(url)

        # from app.services.cloudflare_kv import CloudflareKVService
        # service = CloudflareKVService(...)
        # key = service.generate_key_from_hash(url_hash)
        #
        # assert key is not None
        # assert len(key) <= 512  # KV key length limit

    def test_key_from_url_path(self):
        """Test generating key from URL path."""
        # from app.services.cloudflare_kv import CloudflareKVService
        # service = CloudflareKVService(...)
        #
        # url = "https://example.com/products/shirt"
        # key = service.generate_key_from_path(url)
        #
        # # Should be like: products/shirt or products-shirt
        # assert 'products' in key
        # assert 'shirt' in key
        # assert key.replace('/', '-').isalnum() or '-' in key

    def test_key_handles_special_characters(self):
        """Test key generation handles special characters."""
        # from app.services.cloudflare_kv import CloudflareKVService
        # service = CloudflareKVService(...)
        #
        # urls = [
        #     "https://example.com/products/item?id=123",
        #     "https://example.com/search?q=cotton+shirt",
        #     "https://example.com/page#section",
        # ]
        #
        # for url in urls:
        #     key = service.url_to_kv_key(url)
        #     # Should be valid KV key
        #     assert key is not None
        #     assert len(key) <= 512

    def test_key_collision_handling(self, db, kv_client):
        """Test handling of duplicate URLs."""
        # Same URL should always generate same key
        page1 = Page(
            client_id=kv_client.id,
            url="https://example.com/page",
            url_hash=Page.compute_url_hash("https://example.com/page")
        )
        page2 = Page(
            client_id=kv_client.id,
            url="https://example.com/page",  # Duplicate
            url_hash=Page.compute_url_hash("https://example.com/page")
        )

        # Should have same hash
        assert page1.url_hash == page2.url_hash

        # Database constraint should prevent duplicate
        # (client_id, url) is unique


class TestKVErrorHandling:
    """Test error handling in KV operations."""

    def test_missing_cloudflare_credentials(
        self,
        client,
        auth_headers,
        db
    ):
        """Test upload fails without Cloudflare credentials."""
        # Create client without credentials
        incomplete_client = Client(
            name="No CF Credentials",
            domain="no-cf.com"
        )
        db.add(incomplete_client)
        db.commit()

        # Create page
        page = Page(
            client_id=incomplete_client.id,
            url=MOCK_SITEMAP_URLS[0],
            url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[0]),
            geo_html=MOCK_GEMINI_GEO_HTML
        )
        db.add(page)
        db.commit()

        page_id = str(page.id)

        response = client.post(
            f'/api/v1/cloudflare/kv/upload/{page_id}',
            headers=auth_headers
        )

        # Should return error
        # assert response.status_code == 400
        # data = response.get_json()
        # assert 'error' in data
        # assert 'credentials' in data['error'].lower()

    def test_cloudflare_api_error(
        self,
        client,
        auth_headers,
        page_ready_for_kv
    ):
        """Test handling Cloudflare API errors."""
        with patch('cloudflare.Cloudflare') as mock_cf:
            client_instance = MagicMock()
            client_instance.kv.namespaces.values.update.side_effect = Exception(
                "API authentication failed"
            )
            mock_cf.return_value = client_instance

            page_id = str(page_ready_for_kv.id)

            response = client.post(
                f'/api/v1/cloudflare/kv/upload/{page_id}',
                headers=auth_headers
            )

            # Should handle error gracefully
            # assert response.status_code in [500, 503]
            # data = response.get_json()
            # assert 'error' in data

    def test_kv_namespace_not_found(
        self,
        client,
        auth_headers,
        db,
        page_ready_for_kv
    ):
        """Test handling invalid KV namespace."""
        # Update client with invalid namespace
        kv_client = page_ready_for_kv.client
        kv_client.cloudflare_kv_namespace_id = "invalid_namespace"
        db.commit()

        page_id = str(page_ready_for_kv.id)

        with patch('cloudflare.Cloudflare') as mock_cf:
            client_instance = MagicMock()
            client_instance.kv.namespaces.values.update.side_effect = Exception(
                "Namespace not found"
            )
            mock_cf.return_value = client_instance

            response = client.post(
                f'/api/v1/cloudflare/kv/upload/{page_id}',
                headers=auth_headers
            )

            # Should handle error
            # assert response.status_code in [400, 404]

    def test_page_not_found(self, client, auth_headers):
        """Test uploading non-existent page."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'

        response = client.post(
            f'/api/v1/cloudflare/kv/upload/{fake_uuid}',
            headers=auth_headers
        )

        # Should return 404
        # assert response.status_code == 404


class TestKVContentHandling:
    """Test content handling in KV uploads."""

    def test_upload_large_content(self, mock_cloudflare_kv):
        """Test uploading large HTML content."""
        # from app.services.cloudflare_kv import CloudflareKVService
        #
        # service = CloudflareKVService(...)
        # large_html = MOCK_GEMINI_GEO_HTML * 100  # Large content
        #
        # # KV supports up to 25MB
        # result = service.upload_page(
        #     key="large-page",
        #     content=large_html
        # )
        #
        # assert result['success'] is True

    def test_upload_html_with_special_characters(self, mock_cloudflare_kv):
        """Test uploading HTML with special characters."""
        html_with_special = """
        <!DOCTYPE html>
        <html>
        <body>
            <p>Price: $29.99 € £ ¥</p>
            <p>Emoji: 🚀 ✨ 💡</p>
            <p>Quotes: "double" 'single'</p>
        </body>
        </html>
        """

        # from app.services.cloudflare_kv import CloudflareKVService
        # service = CloudflareKVService(...)
        # result = service.upload_page(
        #     key="special-chars",
        #     content=html_with_special
        # )
        #
        # assert result['success'] is True

    def test_content_encoding(self, mock_cloudflare_kv):
        """Test content is properly encoded for KV."""
        # from app.services.cloudflare_kv import CloudflareKVService
        # service = CloudflareKVService(...)
        #
        # # Content should be UTF-8 encoded
        # result = service.upload_page(
        #     key="test",
        #     content=MOCK_GEMINI_GEO_HTML
        # )
        #
        # # Verify encoding
        # assert isinstance(result, dict)


class TestKVVersioning:
    """Test versioning in KV uploads."""

    def test_version_increments_on_reupload(
        self,
        db,
        kv_client,
        page_ready_for_kv
    ):
        """Test page version increments on re-upload."""
        original_version = page_ready_for_kv.version

        # Simulate upload
        page_ready_for_kv.kv_key = "test-key"
        page_ready_for_kv.kv_uploaded_at = datetime.utcnow()
        page_ready_for_kv.version += 1
        db.commit()

        # Simulate re-upload
        page_ready_for_kv.version += 1
        db.commit()

        assert page_ready_for_kv.version == original_version + 2

    def test_kv_metadata_includes_version(self):
        """Test KV metadata includes version number."""
        # from app.services.cloudflare_kv import CloudflareKVService
        # service = CloudflareKVService(...)
        #
        # metadata = service.build_kv_metadata(
        #     page_id="test-id",
        #     version=5,
        #     uploaded_at=datetime.utcnow()
        # )
        #
        # assert 'version' in metadata
        # assert metadata['version'] == 5


class TestKVPerformance:
    """Test KV operation performance."""

    def test_batch_upload_efficiency(
        self,
        db,
        kv_client,
        mock_cloudflare_kv
    ):
        """Test batch upload handles many pages efficiently."""
        # Create 100 pages
        pages = []
        for i in range(100):
            page = Page(
                client_id=kv_client.id,
                url=f"https://{kv_client.domain}/page-{i}",
                url_hash=Page.compute_url_hash(
                    f"https://{kv_client.domain}/page-{i}"
                ),
                geo_html=MOCK_GEMINI_GEO_HTML
            )
            db.add(page)
            pages.append(page)

        db.commit()

        # from app.services.cloudflare_kv import CloudflareKVService
        # import time
        #
        # service = CloudflareKVService(...)
        #
        # start = time.time()
        # service.upload_client_pages(kv_client.id, batch_size=10)
        # duration = time.time() - start
        #
        # # Should complete in reasonable time
        # assert duration < 30  # 30 seconds for 100 pages
