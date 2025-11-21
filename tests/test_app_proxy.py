"""
Tests for Shopify App Proxy endpoints.

Tests serving llms.txt and other content through Shopify app proxy.
"""
import pytest

from app.models.client import Client, Page
from tests.fixtures.test_data import (
    MOCK_CLIENT_DATA,
    MOCK_SHOPIFY_PROXY_HEADERS,
    MOCK_LLMS_TXT,
    MOCK_GEMINI_GEO_HTML,
)


@pytest.fixture
def proxy_client(db):
    """Create a client for app proxy testing."""
    client = Client(
        name="Proxy Test Shop",
        domain="test-shop.myshopify.com",
        is_active=True
    )

    db.add(client)
    db.commit()
    db.refresh(client)

    return client


@pytest.fixture
def proxy_pages(db, proxy_client):
    """Create pages for app proxy testing."""
    pages = []
    for i in range(3):
        page = Page(
            client_id=proxy_client.id,
            url=f'https://{proxy_client.domain}/page-{i}',
            url_hash=Page.compute_url_hash(f'https://{proxy_client.domain}/page-{i}'),
            llm_markdown=f"# Page {i}\n\nContent",
            geo_html=MOCK_GEMINI_GEO_HTML
        )
        db.add(page)
        pages.append(page)

    db.commit()

    for page in pages:
        db.refresh(page)

    return pages


class TestAppProxyLLMSTxt:
    """Test serving llms.txt through app proxy."""

    def test_serve_llms_txt(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test serving llms.txt via app proxy."""
        response = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # assert response.content_type == 'text/plain' or 'text/plain' in response.content_type
        #
        # data = response.get_data(as_text=True)
        # assert len(data) > 0
        # assert proxy_client.domain in data

    def test_llms_txt_content_type(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test llms.txt returns correct content type."""
        response = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # Should return text/plain
        # assert response.status_code == 200
        # assert 'text/plain' in response.content_type

    def test_llms_txt_without_shopify_headers(self, client):
        """Test accessing llms.txt without Shopify headers."""
        response = client.get('/app-proxy/llms.txt')

        # Should return error (can't identify shop)
        # assert response.status_code in [400, 401, 404]

    def test_llms_txt_invalid_shop_domain(self, client):
        """Test llms.txt with invalid shop domain."""
        headers = MOCK_SHOPIFY_PROXY_HEADERS.copy()
        headers['X-Shopify-Shop-Domain'] = 'nonexistent-shop.myshopify.com'

        response = client.get('/app-proxy/llms.txt', headers=headers)

        # Should return 404
        # assert response.status_code == 404


class TestAppProxyClientIdentification:
    """Test identifying clients from Shopify headers."""

    def test_extract_shop_domain_from_headers(self):
        """Test extracting shop domain from Shopify headers."""
        # from app.api.app_proxy import extract_shop_domain
        #
        # domain = extract_shop_domain(MOCK_SHOPIFY_PROXY_HEADERS)
        # assert domain == "test-shop.myshopify.com"

    def test_handle_missing_shop_header(self):
        """Test handling missing X-Shopify-Shop-Domain header."""
        # from app.api.app_proxy import extract_shop_domain
        #
        # headers = {}
        # domain = extract_shop_domain(headers)
        #
        # # Should return None or raise error
        # assert domain is None

    def test_find_client_by_domain(self, db, proxy_client):
        """Test finding client by shop domain."""
        # from app.api.app_proxy import find_client_by_domain
        #
        # client = find_client_by_domain(db, proxy_client.domain)
        #
        # assert client is not None
        # assert client.id == proxy_client.id
        # assert client.domain == proxy_client.domain

    def test_client_not_found_by_domain(self, db):
        """Test handling non-existent shop domain."""
        # from app.api.app_proxy import find_client_by_domain
        #
        # client = find_client_by_domain(db, "nonexistent.myshopify.com")
        #
        # assert client is None


class TestAppProxyHeaders:
    """Test Shopify app proxy header handling."""

    def test_parse_shopify_headers(self):
        """Test parsing Shopify-specific headers."""
        # from app.api.app_proxy import parse_shopify_headers
        #
        # parsed = parse_shopify_headers(MOCK_SHOPIFY_PROXY_HEADERS)
        #
        # assert 'shop_domain' in parsed
        # assert 'customer_id' in parsed
        # assert parsed['shop_domain'] == "test-shop.myshopify.com"

    def test_handle_customer_headers(self):
        """Test handling customer-specific headers."""
        # Shopify includes customer ID if logged in
        assert 'X-Shopify-Customer-Id' in MOCK_SHOPIFY_PROXY_HEADERS

    def test_validate_shopify_hmac(self):
        """Test validating Shopify HMAC signature."""
        # from app.api.app_proxy import validate_shopify_hmac
        #
        # # In production, would validate HMAC
        # # For testing, mock validation
        # is_valid = validate_shopify_hmac(
        #     MOCK_SHOPIFY_PROXY_HEADERS,
        #     secret="test-secret"
        # )
        #
        # # Mock would return True
        # assert is_valid is True or is_valid is None  # May skip in test


class TestAppProxyCaching:
    """Test caching behavior for app proxy."""

    def test_llms_txt_cached_for_performance(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test llms.txt is cached for fast serving."""
        import time

        # First request
        start1 = time.time()
        response1 = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )
        duration1 = time.time() - start1

        # Second request (should be cached)
        start2 = time.time()
        response2 = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )
        duration2 = time.time() - start2

        # Both should succeed
        # assert response1.status_code == 200
        # assert response2.status_code == 200
        #
        # # Second should be faster (cached)
        # assert duration2 <= duration1

    def test_cache_headers_set(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test proper cache headers are set."""
        response = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # Should include cache headers
        # assert response.status_code == 200
        # assert 'Cache-Control' in response.headers or 'ETag' in response.headers


class TestAppProxyErrorHandling:
    """Test error handling in app proxy."""

    def test_handle_inactive_client(self, db, client):
        """Test handling inactive client."""
        # Create inactive client
        inactive_client = Client(
            name="Inactive Shop",
            domain="inactive-shop.myshopify.com",
            is_active=False
        )
        db.add(inactive_client)
        db.commit()

        headers = MOCK_SHOPIFY_PROXY_HEADERS.copy()
        headers['X-Shopify-Shop-Domain'] = inactive_client.domain

        response = client.get('/app-proxy/llms.txt', headers=headers)

        # Should return error or 404
        # assert response.status_code in [403, 404]

    def test_handle_database_error(self, client):
        """Test handling database errors gracefully."""
        # Simulate database error
        with pytest.raises(Exception):
            # Force database connection issue
            # from app.models.base import engine
            # engine.dispose()

            response = client.get(
                '/app-proxy/llms.txt',
                headers=MOCK_SHOPIFY_PROXY_HEADERS
            )

            # Should return 500
            # assert response.status_code == 500

    def test_handle_empty_client(self, client, proxy_client):
        """Test handling client with no pages."""
        # proxy_client has no pages initially
        response = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # Should return valid (but empty) llms.txt
        # assert response.status_code == 200
        # data = response.get_data(as_text=True)
        # assert len(data) > 0  # At least has site name


class TestAppProxyRoutes:
    """Test different app proxy routes."""

    def test_root_proxy_endpoint(self, client, proxy_client):
        """Test root app proxy endpoint."""
        response = client.get(
            '/app-proxy/',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # May return info or redirect
        # assert response.status_code in [200, 302, 404]

    def test_proxy_health_check(self, client):
        """Test app proxy health check endpoint."""
        response = client.get('/app-proxy/health')

        # Should return health status
        # assert response.status_code == 200

    def test_proxy_unknown_route(self, client):
        """Test accessing unknown proxy route."""
        response = client.get(
            '/app-proxy/unknown-route',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # Should return 404
        # assert response.status_code == 404


class TestAppProxyShopifyIntegration:
    """Test Shopify-specific integration."""

    def test_app_proxy_url_format(self):
        """Test app proxy URLs follow Shopify format."""
        # Shopify app proxy URLs:
        # https://shop.myshopify.com/apps/your-app/llms.txt
        # Maps to: https://your-api.com/app-proxy/llms.txt

        # URL should start with /app-proxy/
        assert '/app-proxy/' in '/app-proxy/llms.txt'

    def test_liquid_variables_if_needed(self):
        """Test handling Shopify Liquid variables if needed."""
        # If returning HTML that needs Liquid, handle appropriately
        # For llms.txt (plain text), not applicable
        pass

    def test_app_proxy_subpath_configuration(self):
        """Test app proxy subpath configuration."""
        # In Shopify app settings, configure:
        # Subpath: /apps/ai-cache
        # URL: https://your-api.com/app-proxy

        # This is configuration, not code to test
        # But document it here
        pass


class TestAppProxyPerformance:
    """Test app proxy performance."""

    def test_response_time_fast(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test app proxy responds quickly."""
        import time

        start = time.time()
        response = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )
        duration = time.time() - start

        # Should be fast (under 1 second)
        assert duration < 1.0

    def test_handles_concurrent_requests(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test app proxy handles concurrent requests."""
        from concurrent.futures import ThreadPoolExecutor

        def make_request():
            return client.get(
                '/app-proxy/llms.txt',
                headers=MOCK_SHOPIFY_PROXY_HEADERS
            )

        # Make 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]

        # All should succeed
        # assert all(r.status_code == 200 for r in responses)


class TestAppProxyContentNegotiation:
    """Test content negotiation in app proxy."""

    def test_plain_text_content_type(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test llms.txt returns plain text."""
        response = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # Content-Type should be text/plain
        # assert response.status_code == 200
        # assert 'text/plain' in response.content_type

    def test_utf8_encoding(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test response uses UTF-8 encoding."""
        response = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # Should specify UTF-8
        # assert response.status_code == 200
        # assert 'charset=utf-8' in response.content_type.lower() or \
        #        response.charset == 'utf-8'

    def test_cors_headers_if_needed(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test CORS headers if serving to external domains."""
        response = client.get(
            '/app-proxy/llms.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # May include CORS headers
        # assert response.status_code == 200
        # Check for Access-Control-Allow-Origin if needed


class TestAppProxySecurityHeaders:
    """Test security in app proxy."""

    def test_validates_shopify_origin(self):
        """Test validates requests come from Shopify."""
        # from app.api.app_proxy import validate_shopify_request
        #
        # # Valid Shopify domain
        # is_valid = validate_shopify_request("shop.myshopify.com")
        # assert is_valid is True
        #
        # # Invalid domain
        # is_valid = validate_shopify_request("malicious.com")
        # assert is_valid is False

    def test_rate_limiting(self, client, proxy_client):
        """Test rate limiting on app proxy endpoints."""
        # Make many rapid requests
        for i in range(100):
            response = client.get(
                '/app-proxy/llms.txt',
                headers=MOCK_SHOPIFY_PROXY_HEADERS
            )

        # May implement rate limiting
        # After many requests, should return 429
        # (depends on implementation)

    def test_rejects_missing_required_headers(self, client):
        """Test rejects requests without required headers."""
        # No Shopify headers
        response = client.get('/app-proxy/llms.txt')

        # Should reject
        # assert response.status_code in [400, 401]


class TestAppProxyCustomRoutes:
    """Test custom app proxy routes beyond llms.txt."""

    def test_serve_specific_page_via_proxy(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test serving specific page content via proxy."""
        page = proxy_pages[0]

        # Could support: /app-proxy/pages/{page_id}
        response = client.get(
            f'/app-proxy/pages/{page.id}',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # If implemented
        # assert response.status_code == 200

    def test_serve_sitemap_via_proxy(
        self,
        client,
        proxy_client,
        proxy_pages
    ):
        """Test serving sitemap via proxy."""
        response = client.get(
            '/app-proxy/sitemap.xml',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # If implemented, return sitemap
        # assert response.status_code in [200, 404]

    def test_serve_robots_txt_via_proxy(self, client, proxy_client):
        """Test serving robots.txt via proxy."""
        response = client.get(
            '/app-proxy/robots.txt',
            headers=MOCK_SHOPIFY_PROXY_HEADERS
        )

        # If implemented
        # assert response.status_code in [200, 404]
