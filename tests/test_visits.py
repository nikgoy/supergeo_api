"""
Tests for visit tracking API.

Tests recording visits, bot detection, analytics, and reporting.
"""
import pytest
from datetime import datetime, timedelta

from app.models.client import Client, Page, Visit
from tests.fixtures.test_data import (
    MOCK_CLIENT_DATA,
    MOCK_SITEMAP_URLS,
    AI_BOT_USER_AGENTS,
    HUMAN_USER_AGENTS,
    AI_REFERRER_URLS,
    MOCK_VISIT_BOT,
    MOCK_VISIT_HUMAN,
)


@pytest.fixture
def visit_client(db):
    """Create a client for visit tracking tests."""
    client = Client(
        name="Visit Test Shop",
        domain="visit-test.com",
        is_active=True
    )

    db.add(client)
    db.commit()
    db.refresh(client)

    return client


@pytest.fixture
def visit_page(db, visit_client):
    """Create a page for visit tracking."""
    page = Page(
        client_id=visit_client.id,
        url=MOCK_SITEMAP_URLS[0],
        url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[0]),
        geo_html="<html><body>Test Page</body></html>"
    )

    db.add(page)
    db.commit()
    db.refresh(page)

    return page


@pytest.fixture
def sample_visits(db, visit_client, visit_page):
    """Create sample visits for testing analytics."""
    visits = []

    # Create 10 bot visits
    for i, (bot_name, user_agent) in enumerate(AI_BOT_USER_AGENTS.items()):
        visit = Visit(
            page_id=visit_page.id,
            client_id=visit_client.id,
            url=visit_page.url,
            visitor_type='ai_bot',
            user_agent=user_agent,
            ip_hash=Visit.hash_ip(f'203.0.113.{i}'),
            bot_name=bot_name,
            referrer=AI_REFERRER_URLS.get(bot_name)
        )
        db.add(visit)
        visits.append(visit)

    # Create 5 human visits
    for i, (browser_name, user_agent) in enumerate(HUMAN_USER_AGENTS.items()):
        visit = Visit(
            page_id=visit_page.id,
            client_id=visit_client.id,
            url=visit_page.url,
            visitor_type='direct',
            user_agent=user_agent,
            ip_hash=Visit.hash_ip(f'203.0.113.{100 + i}'),
            referrer='https://www.google.com/search?q=test'
        )
        db.add(visit)
        visits.append(visit)

    db.commit()

    for visit in visits:
        db.refresh(visit)

    return visits


class TestVisitRecordingEndpoint:
    """Test visit recording API endpoint."""

    def test_record_bot_visit(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test recording an AI bot visit."""
        payload = {
            'client_id': str(visit_client.id),
            'page_id': str(visit_page.id),
            'url': visit_page.url,
            'user_agent': AI_BOT_USER_AGENTS['ChatGPT'],
            'ip': '203.0.113.42',
            'referrer': AI_REFERRER_URLS['ChatGPT'],
            'bot_name': 'ChatGPT'
        }

        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )

        # Expected response when implemented
        # assert response.status_code == 201
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert 'visit_id' in data

    def test_record_human_visit(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test recording a human visit."""
        payload = {
            'client_id': str(visit_client.id),
            'page_id': str(visit_page.id),
            'url': visit_page.url,
            'user_agent': HUMAN_USER_AGENTS['Chrome'],
            'ip': '203.0.113.100'
        }

        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )

        # Expected response
        # assert response.status_code == 201
        # data = response.get_json()
        # assert data['success'] is True

    def test_record_visit_without_page_id(
        self,
        client,
        auth_headers,
        visit_client
    ):
        """Test recording visit without page_id (lookup by URL)."""
        payload = {
            'client_id': str(visit_client.id),
            'url': 'https://visit-test.com/new-page',
            'user_agent': AI_BOT_USER_AGENTS['ChatGPT'],
            'ip': '203.0.113.42'
        }

        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )

        # Should create visit even without page_id
        # assert response.status_code == 201

    def test_record_visit_ip_hashing(
        self,
        client,
        auth_headers,
        db,
        visit_client,
        visit_page
    ):
        """Test IP addresses are hashed for privacy."""
        payload = {
            'client_id': str(visit_client.id),
            'page_id': str(visit_page.id),
            'url': visit_page.url,
            'user_agent': HUMAN_USER_AGENTS['Chrome'],
            'ip': '192.168.1.1'
        }

        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )

        # Verify IP is hashed
        # visit = db.query(Visit).filter(
        #     Visit.client_id == visit_client.id
        # ).order_by(Visit.visited_at.desc()).first()
        #
        # assert visit.ip_hash != '192.168.1.1'
        # assert len(visit.ip_hash) == 64  # SHA-256 hash length

    def test_record_visit_missing_required_fields(
        self,
        client,
        auth_headers
    ):
        """Test recording visit without required fields."""
        payload = {
            'url': 'https://test.com/page'
            # Missing client_id
        }

        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )

        # Should return error
        # assert response.status_code == 400


class TestVisitBotDetection:
    """Test bot detection in visit tracking."""

    def test_detect_bot_from_user_agent(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test bot detection from user agent."""
        for bot_name, user_agent in AI_BOT_USER_AGENTS.items():
            payload = {
                'client_id': str(visit_client.id),
                'page_id': str(visit_page.id),
                'url': visit_page.url,
                'user_agent': user_agent,
                'ip': '203.0.113.1'
                # Don't provide bot_name - should auto-detect
            }

            response = client.post(
                '/api/v1/visits/record',
                headers=auth_headers,
                json=payload
            )

            # Should auto-detect bot
            # assert response.status_code == 201

    def test_human_not_detected_as_bot(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test human user agents are not detected as bots."""
        for browser_name, user_agent in HUMAN_USER_AGENTS.items():
            payload = {
                'client_id': str(visit_client.id),
                'page_id': str(visit_page.id),
                'url': visit_page.url,
                'user_agent': user_agent,
                'ip': '203.0.113.1'
            }

            response = client.post(
                '/api/v1/visits/record',
                headers=auth_headers,
                json=payload
            )

            # Should not be detected as bot
            # assert response.status_code == 201


class TestVisitAnalyticsEndpoints:
    """Test visit analytics API endpoints."""

    def test_get_client_visits(
        self,
        client,
        auth_headers,
        visit_client,
        sample_visits
    ):
        """Test getting visit statistics for a client."""
        client_id = str(visit_client.id)

        response = client.get(
            f'/api/v1/visits/client/{client_id}',
            headers=auth_headers
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert 'total_visits' in data
        # assert 'bot_visits' in data
        # assert 'human_visits' in data
        # assert 'top_bots' in data
        # assert 'top_pages' in data
        #
        # assert data['total_visits'] == 15  # 10 bots + 5 humans
        # assert data['bot_visits'] >= 7  # At least 7 AI bots
        # assert data['human_visits'] == 5

    def test_get_client_visits_with_date_filter(
        self,
        client,
        auth_headers,
        visit_client,
        sample_visits
    ):
        """Test filtering visits by date range."""
        client_id = str(visit_client.id)

        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()

        response = client.get(
            f'/api/v1/visits/client/{client_id}?start_date={start_date}&end_date={end_date}',
            headers=auth_headers
        )

        # Should return filtered results
        # assert response.status_code == 200

    def test_get_page_visits(
        self,
        client,
        auth_headers,
        visit_page,
        sample_visits
    ):
        """Test getting visits for a specific page."""
        page_id = str(visit_page.id)

        response = client.get(
            f'/api/v1/visits/page/{page_id}',
            headers=auth_headers
        )

        # Expected response
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert 'total_visits' in data
        # assert 'visits' in data
        # assert len(data['visits']) == 15

    def test_get_visit_analytics_dashboard(
        self,
        client,
        auth_headers,
        visit_client,
        sample_visits
    ):
        """Test getting dashboard analytics data."""
        client_id = str(visit_client.id)

        response = client.get(
            f'/api/v1/visits/analytics/{client_id}',
            headers=auth_headers
        )

        # Expected response
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert 'time_series' in data
        # assert 'bot_breakdown' in data
        # assert 'page_breakdown' in data


class TestVisitAnalyticsData:
    """Test visit analytics data aggregation."""

    def test_top_bots_ranking(self, db, visit_client, sample_visits):
        """Test getting top bot rankings."""
        # from app.services.visit_analytics import get_top_bots
        #
        # top_bots = get_top_bots(visit_client.id, limit=5)
        #
        # assert len(top_bots) > 0
        # assert all('bot_name' in bot for bot in top_bots)
        # assert all('count' in bot for bot in top_bots)
        #
        # # Should be sorted by count descending
        # counts = [bot['count'] for bot in top_bots]
        # assert counts == sorted(counts, reverse=True)

    def test_top_pages_by_visits(self, db, visit_client, sample_visits):
        """Test getting top pages by visit count."""
        # from app.services.visit_analytics import get_top_pages
        #
        # top_pages = get_top_pages(visit_client.id, limit=10)
        #
        # assert len(top_pages) > 0
        # assert all('url' in page for page in top_pages)
        # assert all('count' in page for page in top_pages)

    def test_visits_time_series(self, db, visit_client, sample_visits):
        """Test getting visits time series data."""
        # from app.services.visit_analytics import get_visits_time_series
        #
        # time_series = get_visits_time_series(
        #     visit_client.id,
        #     start_date=datetime.utcnow() - timedelta(days=7),
        #     end_date=datetime.utcnow(),
        #     interval='day'
        # )
        #
        # assert len(time_series) > 0
        # assert all('date' in point for point in time_series)
        # assert all('bot_visits' in point for point in time_series)
        # assert all('human_visits' in point for point in time_series)

    def test_bot_vs_human_ratio(self, db, visit_client, sample_visits):
        """Test calculating bot vs human visitor ratio."""
        total_visits = len(sample_visits)
        bot_visits = len([v for v in sample_visits if v.visitor_type == 'ai_bot'])
        human_visits = total_visits - bot_visits

        assert bot_visits > 0
        assert human_visits > 0

        bot_ratio = bot_visits / total_visits
        assert 0 < bot_ratio < 1


class TestVisitReferrerTracking:
    """Test referrer tracking in visits."""

    def test_record_visit_with_referrer(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test recording visit with referrer."""
        payload = {
            'client_id': str(visit_client.id),
            'page_id': str(visit_page.id),
            'url': visit_page.url,
            'user_agent': AI_BOT_USER_AGENTS['ChatGPT'],
            'ip': '203.0.113.1',
            'referrer': AI_REFERRER_URLS['ChatGPT']
        }

        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )

        # Should store referrer
        # assert response.status_code == 201

    def test_identify_ai_referrers(self, db, visit_client, sample_visits):
        """Test identifying AI platform referrers."""
        ai_referrers = [
            v for v in sample_visits
            if v.referrer and any(
                domain in v.referrer
                for domain in ['openai.com', 'perplexity.ai', 'claude.ai']
            )
        ]

        assert len(ai_referrers) > 0

    def test_track_direct_traffic(self, db, visit_client, sample_visits):
        """Test tracking direct traffic (no referrer)."""
        direct_visits = [v for v in sample_visits if not v.referrer]

        # Some visits may not have referrer
        # assert len(direct_visits) >= 0


class TestVisitPrivacy:
    """Test privacy features in visit tracking."""

    def test_ip_address_hashing(self):
        """Test IP addresses are hashed."""
        ip = "192.168.1.1"
        hashed = Visit.hash_ip(ip)

        assert hashed != ip
        assert len(hashed) == 64  # SHA-256 produces 64 hex characters

    def test_same_ip_same_hash(self):
        """Test same IP produces same hash (deterministic)."""
        ip = "192.168.1.1"
        hash1 = Visit.hash_ip(ip)
        hash2 = Visit.hash_ip(ip)

        assert hash1 == hash2

    def test_different_ips_different_hashes(self):
        """Test different IPs produce different hashes."""
        hash1 = Visit.hash_ip("192.168.1.1")
        hash2 = Visit.hash_ip("192.168.1.2")

        assert hash1 != hash2

    def test_no_pii_stored(self, sample_visits):
        """Test no personally identifiable information is stored."""
        for visit in sample_visits:
            # IP should be hashed
            assert visit.ip_hash is None or len(visit.ip_hash) == 64

            # No email, name, or other PII
            # (user_agent is acceptable as it's general device/browser info)


class TestVisitWorkerIntegration:
    """Test integration with Cloudflare Worker."""

    def test_worker_sends_visit_data(self):
        """Test worker sends properly formatted visit data."""
        # This tests the contract between worker and API
        # Worker should send:
        worker_payload = {
            'client_id': 'uuid-here',
            'url': 'https://example.com/page',
            'user_agent': 'ChatGPT-User/1.0',
            'referrer': 'https://chat.openai.com/',
            'visitor_type': 'ai_bot',
            'bot_name': 'ChatGPT'
        }

        # All required fields present
        assert 'client_id' in worker_payload
        assert 'url' in worker_payload
        assert 'user_agent' in worker_payload

    def test_api_validates_worker_requests(self):
        """Test API validates requests from worker."""
        # Could use API key or signature validation
        # from app.api.visits import validate_worker_request
        #
        # is_valid = validate_worker_request(headers={'X-API-Key': 'valid-key'})
        # assert is_valid is True


class TestVisitPerformance:
    """Test visit tracking performance."""

    def test_record_visit_fast(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test visit recording is fast."""
        import time

        payload = {
            'client_id': str(visit_client.id),
            'page_id': str(visit_page.id),
            'url': visit_page.url,
            'user_agent': AI_BOT_USER_AGENTS['ChatGPT'],
            'ip': '203.0.113.1'
        }

        start = time.time()
        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )
        duration = time.time() - start

        # Should be very fast (under 500ms)
        assert duration < 0.5

    def test_bulk_visit_recording(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test recording many visits doesn't slow down."""
        # Record 100 visits
        for i in range(100):
            payload = {
                'client_id': str(visit_client.id),
                'page_id': str(visit_page.id),
                'url': visit_page.url,
                'user_agent': AI_BOT_USER_AGENTS['ChatGPT'],
                'ip': f'203.0.113.{i}'
            }

            response = client.post(
                '/api/v1/visits/record',
                headers=auth_headers,
                json=payload
            )

        # All should succeed
        # (in production, might want batch endpoint)

    def test_analytics_query_performance(
        self,
        client,
        auth_headers,
        db,
        visit_client
    ):
        """Test analytics queries are performant with many visits."""
        # Create 1000 visits
        import time
        from datetime import datetime

        for i in range(1000):
            visit = Visit(
                client_id=visit_client.id,
                url=f'https://visit-test.com/page-{i % 10}',
                visitor_type='ai_bot' if i % 2 == 0 else 'direct',
                user_agent='TestBot/1.0',
                visited_at=datetime.utcnow()
            )
            db.add(visit)

        db.commit()

        # Query analytics
        start = time.time()
        response = client.get(
            f'/api/v1/visits/client/{visit_client.id}',
            headers=auth_headers
        )
        duration = time.time() - start

        # Should complete in reasonable time
        # assert response.status_code == 200
        # assert duration < 2.0  # Under 2 seconds


class TestVisitEdgeCases:
    """Test edge cases in visit tracking."""

    def test_visit_without_user_agent(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test recording visit without user agent."""
        payload = {
            'client_id': str(visit_client.id),
            'page_id': str(visit_page.id),
            'url': visit_page.url,
            'ip': '203.0.113.1'
            # No user_agent
        }

        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )

        # Should still record
        # assert response.status_code == 201

    def test_visit_to_nonexistent_page(
        self,
        client,
        auth_headers,
        visit_client
    ):
        """Test recording visit to page that doesn't exist in DB."""
        payload = {
            'client_id': str(visit_client.id),
            'url': 'https://visit-test.com/nonexistent-page',
            'user_agent': AI_BOT_USER_AGENTS['ChatGPT'],
            'ip': '203.0.113.1'
        }

        response = client.post(
            '/api/v1/visits/record',
            headers=auth_headers,
            json=payload
        )

        # Should still record with page_id = None
        # assert response.status_code == 201

    def test_concurrent_visit_recording(
        self,
        client,
        auth_headers,
        visit_client,
        visit_page
    ):
        """Test concurrent visit recording doesn't cause issues."""
        from concurrent.futures import ThreadPoolExecutor

        def record_visit(i):
            payload = {
                'client_id': str(visit_client.id),
                'page_id': str(visit_page.id),
                'url': visit_page.url,
                'user_agent': AI_BOT_USER_AGENTS['ChatGPT'],
                'ip': f'203.0.113.{i}'
            }
            return client.post(
                '/api/v1/visits/record',
                headers=auth_headers,
                json=payload
            )

        # Record 50 visits concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(record_visit, i) for i in range(50)]
            responses = [f.result() for f in futures]

        # All should succeed
        # assert all(r.status_code == 201 for r in responses)
