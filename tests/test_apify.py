"""
Tests for Apify RAG Web Browser integration.

Tests cover:
- Apify service functionality
- API endpoints
- Error handling
- Parallel processing
"""
import json
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

import pytest

from app.models.client import Client, Page


class TestApifyService:
    """Tests for ApifyRagService."""

    @patch('app.services.apify_rag.requests.post')
    def test_scrape_url_success(self, mock_post):
        """Test successful URL scraping."""
        from app.services.apify_rag import ApifyRagService

        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'url': 'https://example.com',
                'markdown': '# Test Page\n\nThis is test content.',
                'text': 'Test Page This is test content.',
                'html': '<html>...</html>'
            }
        ]
        mock_post.return_value = mock_response

        # Create service and scrape
        service = ApifyRagService(api_token='test-token')
        result = service.scrape_url('https://example.com')

        # Assertions
        assert result['status'] == 'success'
        assert result['url'] == 'https://example.com'
        assert result['run_id'] is None
        assert result['markdown'] == '# Test Page\n\nThis is test content.'
        assert result['metadata']['crawled_url'] == 'https://example.com'

        # Verify the POST request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'token=test-token' in call_args[0][0]
        assert call_args[1]['json']['query'] == 'https://example.com'
        assert call_args[1]['json']['outputFormats'] == ['markdown']

    @patch('app.services.apify_rag.requests.post')
    def test_scrape_url_failed(self, mock_post):
        """Test failed URL scraping."""
        from app.services.apify_rag import ApifyRagService

        # Mock failed API response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        # Create service and scrape
        service = ApifyRagService(api_token='test-token', max_retries=1)
        result = service.scrape_url('https://example.com')

        # Assertions
        assert result['status'] == 'failed'
        assert result['run_id'] is None
        assert 'Apify API returned status 500' in result['error']

    @patch('app.services.apify_rag.requests.post')
    def test_scrape_url_exception(self, mock_post):
        """Test exception handling during scraping."""
        from app.services.apify_rag import ApifyRagService

        # Mock requests.post to raise exception
        mock_post.side_effect = Exception('Network error')

        # Create service and scrape
        service = ApifyRagService(api_token='test-token', max_retries=1)
        result = service.scrape_url('https://example.com')

        # Assertions
        assert result['status'] == 'failed'
        assert result['run_id'] is None
        assert 'Network error' in result['error']

    @patch('app.services.apify_rag.requests.post')
    def test_scrape_urls_parallel(self, mock_post):
        """Test parallel URL scraping."""
        from app.services.apify_rag import ApifyRagService

        # Mock successful API responses
        def mock_response(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            # Extract URL from the query parameter in the payload
            url = kwargs['json']['query']
            mock_resp.json.return_value = [
                {
                    'url': url,
                    'markdown': f'Test content for {url}',
                    'text': 'Test content',
                    'html': '<html>...</html>'
                }
            ]
            return mock_resp

        mock_post.side_effect = mock_response

        # Create service and scrape multiple URLs
        service = ApifyRagService(api_token='test-token')
        urls = [
            'https://example.com/page1',
            'https://example.com/page2',
            'https://example.com/page3'
        ]
        results = service.scrape_urls_parallel(urls, max_workers=2)

        # Assertions
        assert len(results) == 3
        assert all(r['status'] == 'success' for r in results)
        assert all(r['run_id'] is None for r in results)
        assert mock_post.call_count == 3


class TestApifyAPI:
    """Tests for Apify API endpoints."""

    @patch('app.api.apify.apify_rag_service.scrape_url')
    def test_scrape_single_url_by_page_id(self, mock_scrape, client, auth_headers, db, sample_client):
        """Test scraping a single URL using page_id."""
        # Create page without raw_markdown
        page = Page(
            client_id=sample_client.id,
            url='https://test.com/new-page',
            url_hash=Page.compute_url_hash('https://test.com/new-page'),
            version=1
        )
        db.add(page)
        db.commit()
        db.refresh(page)

        # Mock successful scrape
        mock_scrape.return_value = {
            'status': 'success',
            'url': 'https://test.com/new-page',
            'run_id': None,
            'markdown': '# New Page\n\nContent here.',
            'metadata': {'crawled_url': 'https://test.com/new-page', 'markdown_length': 27}
        }

        # Make request
        response = client.post(
            '/api/v1/apify/scrape-url',
            headers=auth_headers,
            json={'page_id': str(page.id)}
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'URL scraped successfully'
        assert data['scrape_result']['status'] == 'success'
        assert data['page']['has_raw_markdown'] is True
        assert data['page']['apify_run_id'] is None

    @patch('app.api.apify.apify_rag_service.scrape_url')
    def test_scrape_single_url_by_url(self, mock_scrape, client, auth_headers, db, sample_client):
        """Test scraping a single URL using url + client_id."""
        # Mock successful scrape
        mock_scrape.return_value = {
            'status': 'success',
            'url': 'https://test.com/dynamic-page',
            'run_id': None,
            'markdown': '# Dynamic Page\n\nContent.',
            'metadata': {'crawled_url': 'https://test.com/dynamic-page', 'markdown_length': 24}
        }

        # Make request (page doesn't exist, will be created)
        response = client.post(
            '/api/v1/apify/scrape-url',
            headers=auth_headers,
            json={
                'url': 'https://test.com/dynamic-page',
                'client_id': str(sample_client.id),
                'create_if_missing': True
            }
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'URL scraped successfully'
        assert data['page']['url'] == 'https://test.com/dynamic-page'

    def test_scrape_single_url_already_scraped(self, client, auth_headers, db, sample_page):
        """Test scraping URL that already has raw_markdown."""
        # sample_page fixture already has raw_markdown

        # Make request without force_rescrape
        response = client.post(
            '/api/v1/apify/scrape-url',
            headers=auth_headers,
            json={'page_id': str(sample_page.id)}
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'already has raw_markdown' in data['message']
        assert data['skipped'] is True

    @patch('app.api.apify.apify_rag_service.scrape_url')
    def test_scrape_single_url_force_rescrape(self, mock_scrape, client, auth_headers, db, sample_page):
        """Test force re-scraping URL."""
        # Mock successful scrape
        mock_scrape.return_value = {
            'status': 'success',
            'url': sample_page.url,
            'run_id': None,
            'markdown': '# Updated Content',
            'metadata': {'crawled_url': sample_page.url, 'markdown_length': 18}
        }

        # Make request with force_rescrape
        response = client.post(
            '/api/v1/apify/scrape-url',
            headers=auth_headers,
            json={
                'page_id': str(sample_page.id),
                'force_rescrape': True
            }
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'URL scraped successfully'
        assert data['page']['scrape_attempts'] == 1

    @patch('app.api.apify.apify_rag_service.scrape_url')
    def test_scrape_single_url_failed(self, mock_scrape, client, auth_headers, db, sample_client):
        """Test scraping URL that fails."""
        # Create page
        page = Page(
            client_id=sample_client.id,
            url='https://test.com/failing-page',
            url_hash=Page.compute_url_hash('https://test.com/failing-page'),
            version=1
        )
        db.add(page)
        db.commit()
        db.refresh(page)

        # Mock failed scrape
        mock_scrape.return_value = {
            'status': 'failed',
            'url': 'https://test.com/failing-page',
            'run_id': None,
            'error': 'Timeout error'
        }

        # Make request
        response = client.post(
            '/api/v1/apify/scrape-url',
            headers=auth_headers,
            json={'page_id': str(page.id)}
        )

        # Assertions
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['message'] == 'URL scraping failed'
        assert data['scrape_result']['error'] == 'Timeout error'

    def test_scrape_single_url_missing_params(self, client, auth_headers):
        """Test scraping without required parameters."""
        # Send a non-empty dict without the required fields
        response = client.post(
            '/api/v1/apify/scrape-url',
            headers=auth_headers,
            json={'some_other_field': 'value'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Either page_id or url is required' in data['error']

    @patch('app.api.apify.apify_rag_service.scrape_urls_parallel')
    def test_scrape_client_urls(self, mock_scrape_parallel, client, auth_headers, db, sample_client):
        """Test batch scraping all client URLs."""
        # Create pages without raw_markdown
        pages = []
        for i in range(3):
            page = Page(
                client_id=sample_client.id,
                url=f'https://test.com/page{i}',
                url_hash=Page.compute_url_hash(f'https://test.com/page{i}'),
                version=1
            )
            db.add(page)
            pages.append(page)
        db.commit()

        # Mock parallel scraping
        mock_scrape_parallel.return_value = [
            {
                'status': 'success',
                'url': f'https://test.com/page{i}',
                'run_id': None,
                'markdown': f'# Page {i}',
                'metadata': {'crawled_url': f'https://test.com/page{i}', 'markdown_length': 9}
            }
            for i in range(3)
        ]

        # Make request
        response = client.post(
            f'/api/v1/apify/scrape-client/{sample_client.id}',
            headers=auth_headers,
            json={'only_missing': True, 'max_pages': 100}
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Batch scraping completed'
        assert data['summary']['total_pages'] == 3
        assert data['summary']['successful'] == 3
        assert data['summary']['failed'] == 0

    @patch('app.api.apify.apify_rag_service.scrape_urls_parallel')
    def test_scrape_client_urls_partial_failure(self, mock_scrape_parallel, client, auth_headers, db, sample_client):
        """Test batch scraping with some failures."""
        # Create pages
        pages = []
        for i in range(3):
            page = Page(
                client_id=sample_client.id,
                url=f'https://test.com/page{i}',
                url_hash=Page.compute_url_hash(f'https://test.com/page{i}'),
                version=1
            )
            db.add(page)
            pages.append(page)
        db.commit()

        # Mock parallel scraping with 1 failure
        mock_scrape_parallel.return_value = [
            {'status': 'success', 'url': 'https://test.com/page0', 'run_id': None, 'markdown': '# Page 0', 'metadata': {}},
            {'status': 'failed', 'url': 'https://test.com/page1', 'run_id': None, 'error': 'Timeout'},
            {'status': 'success', 'url': 'https://test.com/page2', 'run_id': None, 'markdown': '# Page 2', 'metadata': {}},
        ]

        # Make request
        response = client.post(
            f'/api/v1/apify/scrape-client/{sample_client.id}',
            headers=auth_headers,
            json={'only_missing': True}
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['summary']['successful'] == 2
        assert data['summary']['failed'] == 1

    def test_scrape_client_urls_no_pages(self, client, auth_headers, db, sample_client):
        """Test batch scraping when no pages need scraping."""
        # All pages already have raw_markdown (sample_page fixture)

        response = client.post(
            f'/api/v1/apify/scrape-client/{sample_client.id}',
            headers=auth_headers,
            json={'only_missing': True}
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'No pages to scrape'
        assert data['summary']['total_pages'] == 0

    def test_scrape_client_urls_invalid_client(self, client, auth_headers):
        """Test batch scraping with invalid client_id."""
        fake_client_id = str(uuid4())

        response = client.post(
            f'/api/v1/apify/scrape-client/{fake_client_id}',
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Client not found' in data['error']

    @patch('app.api.apify.apify_rag_service.get_run_status')
    def test_get_scrape_status(self, mock_get_status, client, auth_headers, db, sample_client):
        """Test getting scrape status for a page."""
        # Create page with scrape data
        page = Page(
            client_id=sample_client.id,
            url='https://test.com/status-page',
            url_hash=Page.compute_url_hash('https://test.com/status-page'),
            raw_markdown='# Content',
            apify_run_id='run_status_123',
            scrape_attempts=1,
            version=1
        )
        page.update_content_hash()
        db.add(page)
        db.commit()
        db.refresh(page)

        # Mock Apify run status (now deprecated)
        mock_get_status.return_value = {
            'run_id': 'run_status_123',
            'status': 'not_supported',
            'error': 'Run status tracking is not supported with the new direct API implementation'
        }

        # Make request
        response = client.get(
            f'/api/v1/apify/status/{page.id}',
            headers=auth_headers
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['page_id'] == str(page.id)
        assert data['has_raw_markdown'] is True
        assert data['apify_run_id'] == 'run_status_123'
        assert data['apify_run_status']['status'] == 'not_supported'

    def test_get_scrape_status_page_not_found(self, client, auth_headers):
        """Test getting status for non-existent page."""
        fake_page_id = str(uuid4())

        response = client.get(
            f'/api/v1/apify/status/{fake_page_id}',
            headers=auth_headers
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Page not found' in data['error']

    def test_scrape_url_no_auth(self, client):
        """Test scraping without authentication."""
        response = client.post(
            '/api/v1/apify/scrape-url',
            json={'page_id': str(uuid4())}
        )

        assert response.status_code == 401
