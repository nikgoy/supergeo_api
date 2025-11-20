"""
Tests for page analytics API endpoints.

Tests all /api/v1/pages_analytics endpoints.
"""
import pytest
from datetime import datetime, timedelta
from app.models.client import Page, PageAnalytics


@pytest.fixture(scope='function')
def pages_with_pipeline_stages(db, sample_client):
    """
    Create pages at different pipeline stages for testing analytics.

    Args:
        db: Database session fixture
        sample_client: Sample client fixture

    Returns:
        List of Page instances with different completion stages
    """
    pages = [
        # Page with all stages complete
        Page(
            client_id=sample_client.id,
            url='https://test.com/complete',
            url_hash=Page.compute_url_hash('https://test.com/complete'),
            raw_markdown='<html>Complete</html>',
            llm_markdown='# Complete',
            geo_html='<h1>Complete</h1>',
            kv_key='https/test-com/complete',
            version=1
        ),
        # Page with only raw markdown
        Page(
            client_id=sample_client.id,
            url='https://test.com/html-only',
            url_hash=Page.compute_url_hash('https://test.com/html-only'),
            raw_markdown='<html>HTML only</html>',
            version=1
        ),
        # Page with raw markdown and LLM markdown
        Page(
            client_id=sample_client.id,
            url='https://test.com/html-md',
            url_hash=Page.compute_url_hash('https://test.com/html-md'),
            raw_markdown='<html>HTML MD</html>',
            llm_markdown='# HTML MD',
            version=1
        ),
        # Page with raw markdown, LLM markdown, and geo HTML
        Page(
            client_id=sample_client.id,
            url='https://test.com/html-md-simple',
            url_hash=Page.compute_url_hash('https://test.com/html-md-simple'),
            raw_markdown='<html>HTML MD Simple</html>',
            llm_markdown='# HTML MD Simple',
            geo_html='<h1>HTML MD Simple</h1>',
            version=1
        ),
        # Page with no content (just URL)
        Page(
            client_id=sample_client.id,
            url='https://test.com/no-content',
            url_hash=Page.compute_url_hash('https://test.com/no-content'),
            version=1
        ),
    ]

    for page in pages:
        page.update_content_hash()
        db.add(page)

    db.commit()

    for page in pages:
        db.refresh(page)

    return pages


@pytest.fixture(scope='function')
def sample_analytics(db, sample_client):
    """
    Create sample analytics for testing.

    Args:
        db: Database session fixture
        sample_client: Sample client fixture

    Returns:
        Sample PageAnalytics instance
    """
    analytics = PageAnalytics(
        client_id=sample_client.id,
        total_urls=100,
        urls_with_raw_markdown=80,
        urls_with_markdown=60,
        urls_with_geo_html=50,
        urls_with_kv_key=40,
        html_completion_rate=80.0,
        markdown_completion_rate=60.0,
        geo_html_completion_rate=50.0,
        kv_upload_completion_rate=40.0,
        pages_updated_last_30_days=15,
        last_calculated_at=datetime.utcnow()
    )

    db.add(analytics)
    db.commit()
    db.refresh(analytics)

    return analytics


class TestGetClientAnalytics:
    """Test GET /api/v1/pages_analytics/client/{client_id} endpoint."""

    def test_get_analytics_requires_auth(self, client, sample_client):
        """Test getting analytics requires API key."""
        response = client.get(f'/api/v1/pages_analytics/client/{sample_client.id}')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_get_analytics_not_found(self, client, auth_headers, sample_client):
        """Test getting analytics when none exist."""
        response = client.get(
            f'/api/v1/pages_analytics/client/{sample_client.id}',
            headers=auth_headers
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_analytics_success(self, client, auth_headers, sample_client, sample_analytics):
        """Test getting analytics successfully."""
        response = client.get(
            f'/api/v1/pages_analytics/client/{sample_client.id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['client_id'] == str(sample_client.id)
        assert data['total_urls'] == 100
        assert data['urls_with_raw_markdown'] == 80
        assert data['urls_with_markdown'] == 60
        assert data['urls_with_geo_html'] == 50
        assert data['urls_with_kv_key'] == 40
        assert data['html_completion_rate'] == 80.0
        assert data['markdown_completion_rate'] == 60.0
        assert data['geo_html_completion_rate'] == 50.0
        assert data['kv_upload_completion_rate'] == 40.0
        assert data['pages_updated_last_30_days'] == 15
        assert 'last_calculated_at' in data
        assert 'created_at' in data
        assert 'updated_at' in data


class TestCalculateClientAnalytics:
    """Test POST /api/v1/pages_analytics/calculate/{client_id} endpoint."""

    def test_calculate_analytics_requires_auth(self, client, sample_client):
        """Test calculating analytics requires API key."""
        response = client.post(f'/api/v1/pages_analytics/calculate/{sample_client.id}')

        assert response.status_code == 401

    def test_calculate_analytics_client_not_found(self, client, auth_headers):
        """Test calculating analytics for non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = client.post(
            f'/api/v1/pages_analytics/calculate/{fake_uuid}',
            headers=auth_headers
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_calculate_analytics_no_pages(self, client, auth_headers, sample_client):
        """Test calculating analytics with no pages."""
        response = client.post(
            f'/api/v1/pages_analytics/calculate/{sample_client.id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert 'message' in data
        assert 'analytics' in data

        analytics = data['analytics']
        assert analytics['total_urls'] == 0
        assert analytics['urls_with_raw_markdown'] == 0
        assert analytics['urls_with_markdown'] == 0
        assert analytics['urls_with_geo_html'] == 0
        assert analytics['urls_with_kv_key'] == 0
        assert analytics['html_completion_rate'] == 0.0

    def test_calculate_analytics_with_pages(self, client, auth_headers, sample_client, pages_with_pipeline_stages):
        """Test calculating analytics with pages at different stages."""
        response = client.post(
            f'/api/v1/pages_analytics/calculate/{sample_client.id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        analytics = data['analytics']
        assert analytics['total_urls'] == 5
        assert analytics['urls_with_raw_markdown'] == 4  # 4 pages have raw_markdown
        assert analytics['urls_with_markdown'] == 3  # 3 pages have LLM markdown
        assert analytics['urls_with_geo_html'] == 2  # 2 pages have geo_html
        assert analytics['urls_with_kv_key'] == 1  # 1 page has kv_key
        assert analytics['html_completion_rate'] == 80.0  # 4/5 = 80%
        assert analytics['markdown_completion_rate'] == 60.0  # 3/5 = 60%
        assert analytics['geo_html_completion_rate'] == 40.0  # 2/5 = 40%
        assert analytics['kv_upload_completion_rate'] == 20.0  # 1/5 = 20%

    def test_calculate_analytics_updates_existing(self, client, auth_headers, sample_client, sample_analytics, pages_with_pipeline_stages):
        """Test that calculating analytics updates existing record."""
        # Get original values
        original_total = sample_analytics.total_urls

        response = client.post(
            f'/api/v1/pages_analytics/calculate/{sample_client.id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        # Should have updated the existing record
        analytics = data['analytics']
        assert analytics['id'] == str(sample_analytics.id)
        assert analytics['total_urls'] != original_total
        assert analytics['total_urls'] == 5  # Based on pages_with_pipeline_stages


class TestGetAllAnalytics:
    """Test GET /api/v1/pages_analytics endpoint."""

    def test_get_all_analytics_requires_auth(self, client):
        """Test getting all analytics requires API key."""
        response = client.get('/api/v1/pages_analytics')

        assert response.status_code == 401

    def test_get_all_analytics_empty(self, client, auth_headers, db):
        """Test getting all analytics when none exist."""
        response = client.get('/api/v1/pages_analytics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert 'analytics' in data
        assert 'count' in data
        assert 'total' in data
        assert data['count'] == 0
        assert data['total'] == 0
        assert data['analytics'] == []

    def test_get_all_analytics_with_data(self, client, auth_headers, sample_analytics):
        """Test getting all analytics with data."""
        response = client.get('/api/v1/pages_analytics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['count'] == 1
        assert data['total'] == 1
        assert len(data['analytics']) == 1

        analytics = data['analytics'][0]
        assert analytics['total_urls'] == 100

    def test_get_all_analytics_pagination(self, client, auth_headers, multiple_clients, db):
        """Test pagination of all analytics."""
        # Create analytics for each client
        for client_obj in multiple_clients:
            analytics = PageAnalytics(
                client_id=client_obj.id,
                total_urls=10,
                urls_with_raw_markdown=8,
                urls_with_markdown=6,
                urls_with_geo_html=4,
                urls_with_kv_key=2,
                html_completion_rate=80.0,
                markdown_completion_rate=60.0,
                geo_html_completion_rate=40.0,
                kv_upload_completion_rate=20.0,
                pages_updated_last_30_days=5,
                last_calculated_at=datetime.utcnow()
            )
            db.add(analytics)
        db.commit()

        # Test first page
        response = client.get(
            '/api/v1/pages_analytics?limit=2&offset=0',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['count'] == 2
        assert data['total'] == 5
        assert data['limit'] == 2
        assert data['offset'] == 0

        # Test second page
        response = client.get(
            '/api/v1/pages_analytics?limit=2&offset=2',
            headers=auth_headers
        )

        data = response.get_json()
        assert data['count'] == 2
        assert data['offset'] == 2


class TestCalculateAllAnalytics:
    """Test POST /api/v1/pages_analytics/calculate-all endpoint."""

    def test_calculate_all_requires_auth(self, client):
        """Test calculating all analytics requires API key."""
        response = client.post('/api/v1/pages_analytics/calculate-all')

        assert response.status_code == 401

    def test_calculate_all_no_clients(self, client, auth_headers, db):
        """Test calculating all analytics with no clients."""
        response = client.post(
            '/api/v1/pages_analytics/calculate-all',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert 'message' in data
        assert 'total_calculated' in data
        assert data['total_calculated'] == 0
        assert data['analytics'] == []

    def test_calculate_all_with_clients(self, client, auth_headers, multiple_clients, db):
        """Test calculating all analytics for multiple clients."""
        # Create some pages for each active client
        for client_obj in multiple_clients:
            if client_obj.is_active:
                page = Page(
                    client_id=client_obj.id,
                    url=f'https://{client_obj.domain}/page',
                    url_hash=Page.compute_url_hash(f'https://{client_obj.domain}/page'),
                    raw_markdown='<html>Test</html>',
                    version=1
                )
                page.update_content_hash()
                db.add(page)
        db.commit()

        response = client.post(
            '/api/v1/pages_analytics/calculate-all',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        # Should have calculated analytics for 3 active clients (is_active=True for clients 0, 2, 4)
        assert data['total_calculated'] == 3
        assert len(data['analytics']) == 3

        # Verify each analytics record
        for analytics in data['analytics']:
            assert analytics['total_urls'] == 1
            assert analytics['urls_with_raw_markdown'] == 1
            assert 'last_calculated_at' in analytics
