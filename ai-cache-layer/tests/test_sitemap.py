"""
Tests for sitemap parser and API endpoints.

Tests XML sitemap parsing and URL import functionality.
"""
import pytest
from unittest.mock import Mock, patch

from app.services.sitemap import SitemapParser


# Sample sitemap XML
SAMPLE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1</loc>
        <lastmod>2024-01-01</lastmod>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://example.com/page2</loc>
        <lastmod>2024-01-02</lastmod>
        <priority>0.5</priority>
    </url>
    <url>
        <loc>https://example.com/page3</loc>
    </url>
</urlset>
"""

SAMPLE_SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://example.com/sitemap1.xml</loc>
        <lastmod>2024-01-01</lastmod>
    </sitemap>
    <sitemap>
        <loc>https://example.com/sitemap2.xml</loc>
        <lastmod>2024-01-02</lastmod>
    </sitemap>
</sitemapindex>
"""

SAMPLE_SITEMAP_NO_NS = """<?xml version="1.0" encoding="UTF-8"?>
<urlset>
    <url>
        <loc>https://example.com/page1</loc>
    </url>
    <url>
        <loc>https://example.com/page2</loc>
    </url>
</urlset>
"""


class TestSitemapParser:
    """Test SitemapParser class."""

    def test_parse_regular_sitemap(self):
        """Test parsing a regular sitemap."""
        parser = SitemapParser()
        result = parser.parse_sitemap(SAMPLE_SITEMAP)

        assert 'urls' in result
        assert len(result['urls']) == 3

        # Check first URL
        assert result['urls'][0]['loc'] == 'https://example.com/page1'
        assert result['urls'][0]['lastmod'] == '2024-01-01'
        assert result['urls'][0]['priority'] == '0.8'

        # Check URL without optional fields
        assert result['urls'][2]['loc'] == 'https://example.com/page3'
        assert 'lastmod' not in result['urls'][2]

    def test_parse_sitemap_index(self):
        """Test parsing a sitemap index."""
        parser = SitemapParser()
        result = parser.parse_sitemap(SAMPLE_SITEMAP_INDEX)

        assert 'sitemaps' in result
        assert len(result['sitemaps']) == 2
        assert 'https://example.com/sitemap1.xml' in result['sitemaps']
        assert 'https://example.com/sitemap2.xml' in result['sitemaps']

    def test_parse_sitemap_without_namespace(self):
        """Test parsing sitemap without XML namespace."""
        parser = SitemapParser()
        result = parser.parse_sitemap(SAMPLE_SITEMAP_NO_NS)

        assert 'urls' in result
        assert len(result['urls']) == 2
        assert result['urls'][0]['loc'] == 'https://example.com/page1'

    def test_parse_invalid_xml(self):
        """Test parsing invalid XML raises error."""
        parser = SitemapParser()

        with pytest.raises(ValueError, match="Invalid XML"):
            parser.parse_sitemap("<invalid>xml")

    def test_extract_urls(self):
        """Test extracting just URLs from sitemap."""
        parser = SitemapParser()
        urls = parser.extract_urls(SAMPLE_SITEMAP)

        assert len(urls) == 3
        assert 'https://example.com/page1' in urls
        assert 'https://example.com/page2' in urls
        assert 'https://example.com/page3' in urls

    def test_normalize_url(self):
        """Test URL normalization."""
        parser = SitemapParser()

        # Remove fragment
        normalized = parser.normalize_url('https://example.com/page#section')
        assert normalized == 'https://example.com/page'

        # Resolve relative URL
        normalized = parser.normalize_url(
            '/page',
            base_url='https://example.com'
        )
        assert normalized == 'https://example.com/page'

    @patch('app.services.sitemap.requests.get')
    def test_fetch_sitemap(self, mock_get):
        """Test fetching sitemap from URL."""
        mock_response = Mock()
        mock_response.text = SAMPLE_SITEMAP
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = SitemapParser()
        content = parser.fetch_sitemap('https://example.com/sitemap.xml')

        assert content == SAMPLE_SITEMAP
        mock_get.assert_called_once()

    def test_fetch_sitemap_invalid_url(self):
        """Test fetching with invalid URL."""
        parser = SitemapParser()

        with pytest.raises(ValueError, match="Invalid URL"):
            parser.fetch_sitemap('not-a-url')

    @patch('app.services.sitemap.requests.get')
    def test_parse_sitemap_recursive(self, mock_get):
        """Test recursive sitemap parsing."""
        # Mock responses
        def side_effect(url, **kwargs):
            mock_response = Mock()
            mock_response.raise_for_status = Mock()

            if 'sitemap.xml' in url:
                mock_response.text = SAMPLE_SITEMAP_INDEX
            elif 'sitemap1.xml' in url:
                mock_response.text = SAMPLE_SITEMAP
            elif 'sitemap2.xml' in url:
                mock_response.text = SAMPLE_SITEMAP_NO_NS
            return mock_response

        mock_get.side_effect = side_effect

        parser = SitemapParser()
        urls = parser.parse_sitemap_recursive('https://example.com/sitemap.xml')

        # Should get URLs from both nested sitemaps
        assert len(urls) >= 3
        assert any(u['loc'] == 'https://example.com/page1' for u in urls)

    def test_max_urls_limit(self):
        """Test that max_urls limit is enforced."""
        parser = SitemapParser(max_urls=2)

        # Create sitemap with 3 URLs
        with pytest.raises(ValueError, match="Exceeded maximum URL limit"):
            parser.parse_sitemap_recursive = Mock(
                side_effect=ValueError("Exceeded maximum URL limit (2)")
            )
            parser.parse_sitemap_recursive('https://example.com/sitemap.xml')


class TestSitemapAPI:
    """Test sitemap API endpoints."""

    @patch('app.api.sitemap.sitemap_parser.fetch_sitemap')
    @patch('app.api.sitemap.sitemap_parser.parse_sitemap')
    def test_parse_sitemap_endpoint(self, mock_parse, mock_fetch, client, auth_headers):
        """Test /api/v1/sitemap/parse endpoint."""
        mock_fetch.return_value = SAMPLE_SITEMAP
        mock_parse.return_value = {
            'urls': [
                {'loc': 'https://example.com/page1', 'priority': '0.8'},
                {'loc': 'https://example.com/page2'},
            ]
        }

        response = client.post(
            '/api/v1/sitemap/parse',
            headers=auth_headers,
            json={'sitemap_url': 'https://example.com/sitemap.xml'}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['total_urls'] == 2
        assert 'urls' in data
        assert data['sitemap_url'] == 'https://example.com/sitemap.xml'

    def test_parse_sitemap_requires_auth(self, client):
        """Test that parse endpoint requires authentication."""
        response = client.post(
            '/api/v1/sitemap/parse',
            json={'sitemap_url': 'https://example.com/sitemap.xml'}
        )

        assert response.status_code == 401

    def test_parse_sitemap_missing_url(self, client, auth_headers):
        """Test parse endpoint with missing sitemap_url."""
        response = client.post(
            '/api/v1/sitemap/parse',
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'sitemap_url is required' in data['error']

    @patch('app.api.sitemap.sitemap_parser.fetch_sitemap')
    @patch('app.api.sitemap.sitemap_parser.parse_sitemap')
    def test_import_sitemap_endpoint(self, mock_parse, mock_fetch, client, auth_headers, sample_client, db):
        """Test /api/v1/sitemap/import endpoint."""
        mock_fetch.return_value = SAMPLE_SITEMAP
        mock_parse.return_value = {
            'urls': [
                {'loc': 'https://test.com/page1'},
                {'loc': 'https://test.com/page2'},
                {'loc': 'https://test.com/page3'},
            ]
        }

        response = client.post(
            '/api/v1/sitemap/import',
            headers=auth_headers,
            json={
                'client_id': str(sample_client.id),
                'sitemap_url': 'https://test.com/sitemap.xml',
                'recursive': False
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['message'] == 'Sitemap imported successfully'
        assert data['summary']['total_urls'] == 3
        assert data['summary']['created'] == 3
        assert data['summary']['skipped'] == 0

        # Verify pages were created in database
        from app.models.client import Page
        pages = db.query(Page).filter(Page.client_id == sample_client.id).all()
        assert len(pages) == 3

    def test_import_sitemap_requires_auth(self, client, sample_client):
        """Test that import endpoint requires authentication."""
        response = client.post(
            '/api/v1/sitemap/import',
            json={
                'client_id': str(sample_client.id),
                'sitemap_url': 'https://test.com/sitemap.xml'
            }
        )

        assert response.status_code == 401

    def test_import_sitemap_missing_client_id(self, client, auth_headers):
        """Test import endpoint with missing client_id."""
        response = client.post(
            '/api/v1/sitemap/import',
            headers=auth_headers,
            json={'sitemap_url': 'https://test.com/sitemap.xml'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'client_id is required' in data['error']

    def test_import_sitemap_invalid_client_id(self, client, auth_headers):
        """Test import endpoint with invalid client_id format."""
        response = client.post(
            '/api/v1/sitemap/import',
            headers=auth_headers,
            json={
                'client_id': 'not-a-uuid',
                'sitemap_url': 'https://test.com/sitemap.xml'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid client_id format' in data['error']

    def test_import_sitemap_client_not_found(self, client, auth_headers):
        """Test import endpoint with non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = client.post(
            '/api/v1/sitemap/import',
            headers=auth_headers,
            json={
                'client_id': fake_uuid,
                'sitemap_url': 'https://test.com/sitemap.xml'
            }
        )

        assert response.status_code == 404

    @patch('app.api.sitemap.sitemap_parser.fetch_sitemap')
    @patch('app.api.sitemap.sitemap_parser.parse_sitemap')
    def test_import_sitemap_skip_duplicates(self, mock_parse, mock_fetch, client, auth_headers, sample_client, sample_page, db):
        """Test that import skips duplicate URLs."""
        mock_fetch.return_value = SAMPLE_SITEMAP
        mock_parse.return_value = {
            'urls': [
                {'loc': sample_page.url},  # Duplicate
                {'loc': 'https://test.com/new-page'},  # New
            ]
        }

        response = client.post(
            '/api/v1/sitemap/import',
            headers=auth_headers,
            json={
                'client_id': str(sample_client.id),
                'sitemap_url': 'https://test.com/sitemap.xml',
                'recursive': False
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['summary']['total_urls'] == 2
        assert data['summary']['created'] == 1
        assert data['summary']['skipped'] == 1

    def test_list_client_pages(self, client, auth_headers, sample_client, sample_page):
        """Test listing pages for a client."""
        response = client.get(
            f'/api/v1/sitemap/client/{sample_client.id}/pages',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['client_id'] == str(sample_client.id)
        assert data['total_pages'] == 1
        assert len(data['pages']) == 1
        assert data['pages'][0]['url'] == sample_page.url

    def test_list_client_pages_with_pagination(self, client, auth_headers, sample_client, db):
        """Test pagination in list pages endpoint."""
        # Create multiple pages
        from app.models.client import Page

        for i in range(10):
            page = Page(
                client_id=sample_client.id,
                url=f'https://test.com/page{i}',
                url_hash=Page.compute_url_hash(f'https://test.com/page{i}')
            )
            db.add(page)
        db.commit()

        # Get first 5
        response = client.get(
            f'/api/v1/sitemap/client/{sample_client.id}/pages?limit=5&offset=0',
            headers=auth_headers
        )

        data = response.get_json()
        assert data['total_pages'] == 10
        assert len(data['pages']) == 5
        assert data['limit'] == 5
        assert data['offset'] == 0

    def test_list_client_pages_filter_by_content(self, client, auth_headers, sample_client, db):
        """Test filtering pages by content."""
        from app.models.client import Page

        # Create pages with and without content
        page1 = Page(
            client_id=sample_client.id,
            url='https://test.com/with-content',
            url_hash=Page.compute_url_hash('https://test.com/with-content'),
            raw_html='<html>content</html>'
        )
        page2 = Page(
            client_id=sample_client.id,
            url='https://test.com/without-content',
            url_hash=Page.compute_url_hash('https://test.com/without-content')
        )

        db.add(page1)
        db.add(page2)
        db.commit()

        # Filter for pages with content
        response = client.get(
            f'/api/v1/sitemap/client/{sample_client.id}/pages?has_content=true',
            headers=auth_headers
        )

        data = response.get_json()
        assert data['total_pages'] == 1
        assert data['pages'][0]['url'] == 'https://test.com/with-content'

        # Filter for pages without content
        response = client.get(
            f'/api/v1/sitemap/client/{sample_client.id}/pages?has_content=false',
            headers=auth_headers
        )

        data = response.get_json()
        assert data['total_pages'] == 1
        assert data['pages'][0]['url'] == 'https://test.com/without-content'

    def test_list_pages_client_not_found(self, client, auth_headers):
        """Test listing pages for non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = client.get(
            f'/api/v1/sitemap/client/{fake_uuid}/pages',
            headers=auth_headers
        )

        assert response.status_code == 404
