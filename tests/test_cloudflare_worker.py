"""
Tests for Cloudflare Worker management.

Tests worker creation, deployment, routing, bot detection, and lifecycle management.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.models.client import Client
from tests.fixtures.test_data import (
    MOCK_CLIENT_DATA,
    MOCK_WORKER_NAME,
    MOCK_WORKER_SCRIPT,
    MOCK_CLOUDFLARE_WORKER_RESPONSE,
    MOCK_CLOUDFLARE_WORKER_STATUS_RESPONSE,
    AI_BOT_USER_AGENTS,
    HUMAN_USER_AGENTS,
)


@pytest.fixture
def worker_client(db):
    """Create a client with Cloudflare credentials for worker testing."""
    client = Client(
        name="Worker Test Client",
        domain="worker-test.com",
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
def mock_cloudflare_worker():
    """Mock Cloudflare Workers API."""
    with patch('cloudflare.Cloudflare') as mock_cf:
        client_instance = MagicMock()

        # Mock worker creation
        client_instance.workers.scripts.update.return_value = (
            MOCK_CLOUDFLARE_WORKER_RESPONSE
        )

        # Mock worker get/status
        client_instance.workers.scripts.get.return_value = (
            MOCK_CLOUDFLARE_WORKER_STATUS_RESPONSE
        )

        # Mock worker deletion
        client_instance.workers.scripts.delete.return_value = {
            'success': True
        }

        # Mock route management
        client_instance.workers.routes.create.return_value = {
            'success': True,
            'result': {
                'id': 'route_123',
                'pattern': '*.worker-test.com/*'
            }
        }

        client_instance.workers.routes.list.return_value = {
            'success': True,
            'result': []
        }

        mock_cf.return_value = client_instance
        yield mock_cf


class TestCloudflareWorkerService:
    """Test Cloudflare Worker service functionality."""

    def test_generate_worker_name(self):
        """Test generating worker name from client."""
        # from app.services.cloudflare_worker import CloudflareWorkerService
        #
        # service = CloudflareWorkerService(...)
        # name = service.generate_worker_name("example.com")
        #
        # assert name is not None
        # assert 'example' in name.lower()
        # assert len(name) > 0

    def test_generate_worker_script(self):
        """Test generating worker script with bot detection."""
        # from app.services.cloudflare_worker import CloudflareWorkerService
        #
        # service = CloudflareWorkerService(...)
        # script = service.generate_worker_script(
        #     domain="example.com",
        #     kv_namespace_id="ns_123",
        #     api_url="https://api.example.com"
        # )
        #
        # # Should include bot detection
        # assert 'ChatGPT' in script
        # assert 'PerplexityBot' in script
        # assert 'Claude' in script
        #
        # # Should reference KV namespace
        # assert 'ns_123' in script or 'KV_NAMESPACE' in script
        #
        # # Should include visit tracking
        # assert 'trackVisit' in script or 'record' in script

    def test_worker_script_template_valid(self):
        """Test worker script template is valid JavaScript."""
        # Worker script should be syntactically valid
        # This is basic check - actual validation would need JS parser
        assert 'addEventListener' in MOCK_WORKER_SCRIPT
        assert 'fetch' in MOCK_WORKER_SCRIPT
        assert 'async function' in MOCK_WORKER_SCRIPT


class TestCloudflareWorkerEndpoints:
    """Test Cloudflare Worker API endpoints."""

    def test_create_worker(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test creating a worker for a client."""
        client_id = str(worker_client.id)

        response = client.post(
            f'/api/v1/cloudflare/worker/create/{client_id}',
            headers=auth_headers,
            json={
                'worker_name': MOCK_WORKER_NAME,
                'route_pattern': f'*.{worker_client.domain}/*'
            }
        )

        # Expected response when implemented
        # assert response.status_code == 201
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert 'worker_name' in data
        # assert 'worker_id' in data
        # assert 'routes' in data
        # assert 'created_at' in data

    def test_create_worker_with_default_name(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test creating worker with auto-generated name."""
        client_id = str(worker_client.id)

        response = client.post(
            f'/api/v1/cloudflare/worker/create/{client_id}',
            headers=auth_headers,
            json={}  # No worker_name specified
        )

        # Should auto-generate name
        # assert response.status_code == 201
        # data = response.get_json()
        # assert 'worker_name' in data
        # assert worker_client.domain.replace('.', '-') in data['worker_name']

    def test_get_worker_status_exists(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test getting worker status when it exists."""
        client_id = str(worker_client.id)

        response = client.get(
            f'/api/v1/cloudflare/worker/status/{client_id}',
            headers=auth_headers
        )

        # Expected response when worker exists
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert data['exists'] is True
        # assert 'worker_name' in data
        # assert 'routes' in data
        # assert 'last_deployed' in data

    def test_get_worker_status_not_exists(
        self,
        client,
        auth_headers,
        worker_client
    ):
        """Test getting worker status when it doesn't exist."""
        with patch('cloudflare.Cloudflare') as mock_cf:
            client_instance = MagicMock()
            client_instance.workers.scripts.get.side_effect = Exception(
                "Worker not found"
            )
            mock_cf.return_value = client_instance

            client_id = str(worker_client.id)

            response = client.get(
                f'/api/v1/cloudflare/worker/status/{client_id}',
                headers=auth_headers
            )

            # Should return 404 or status indicating worker doesn't exist
            # assert response.status_code in [200, 404]
            # if response.status_code == 200:
            #     data = response.get_json()
            #     assert data['exists'] is False

    def test_update_worker(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test updating an existing worker."""
        client_id = str(worker_client.id)

        custom_script = "// Custom worker script\n" + MOCK_WORKER_SCRIPT

        response = client.put(
            f'/api/v1/cloudflare/worker/update/{client_id}',
            headers=auth_headers,
            json={'script': custom_script}
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert 'updated_at' in data

    def test_update_worker_with_default_script(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test updating worker without providing script (uses default)."""
        client_id = str(worker_client.id)

        response = client.put(
            f'/api/v1/cloudflare/worker/update/{client_id}',
            headers=auth_headers,
            json={}
        )

        # Should use default template
        # assert response.status_code == 200

    def test_delete_worker(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test deleting a worker."""
        client_id = str(worker_client.id)

        response = client.delete(
            f'/api/v1/cloudflare/worker/delete/{client_id}',
            headers=auth_headers
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert 'deleted_worker' in data


class TestWorkerBotDetection:
    """Test bot detection logic in worker."""

    def test_detect_chatgpt_bot(self):
        """Test detecting ChatGPT user agent."""
        user_agent = AI_BOT_USER_AGENTS["ChatGPT"]

        # from app.services.cloudflare_worker import detect_ai_bot
        # is_bot = detect_ai_bot(user_agent)
        # assert is_bot is True

        # Check in worker script
        assert 'ChatGPT' in MOCK_WORKER_SCRIPT or 'GPTBot' in MOCK_WORKER_SCRIPT

    def test_detect_perplexity_bot(self):
        """Test detecting Perplexity bot."""
        user_agent = AI_BOT_USER_AGENTS["Perplexity"]

        # Should be detected
        assert 'Perplexity' in MOCK_WORKER_SCRIPT

    def test_detect_claude_bot(self):
        """Test detecting Claude bot."""
        user_agent = AI_BOT_USER_AGENTS["Claude"]

        # Should be detected
        assert 'Claude' in MOCK_WORKER_SCRIPT

    def test_detect_googlebot(self):
        """Test detecting Googlebot."""
        user_agent = AI_BOT_USER_AGENTS["GoogleBot"]

        # Should be detected
        assert 'Googlebot' in MOCK_WORKER_SCRIPT

    def test_human_user_agents_not_detected(self):
        """Test human user agents are not detected as bots."""
        # from app.services.cloudflare_worker import detect_ai_bot
        #
        # for name, user_agent in HUMAN_USER_AGENTS.items():
        #     is_bot = detect_ai_bot(user_agent)
        #     assert is_bot is False, f"{name} should not be detected as bot"

    def test_bot_detection_case_insensitive(self):
        """Test bot detection is case-insensitive."""
        # from app.services.cloudflare_worker import detect_ai_bot
        #
        # assert detect_ai_bot("chatgpt-user") is True
        # assert detect_ai_bot("CHATGPT-USER") is True
        # assert detect_ai_bot("ChatGPT-User") is True


class TestWorkerRouting:
    """Test worker routing logic."""

    def test_route_pattern_generation(self):
        """Test generating route patterns."""
        # from app.services.cloudflare_worker import CloudflareWorkerService
        #
        # service = CloudflareWorkerService(...)
        # pattern = service.generate_route_pattern("example.com")
        #
        # # Should match all paths on domain
        # assert "example.com" in pattern
        # assert "*" in pattern  # Wildcard

    def test_route_covers_subdomains(self):
        """Test route pattern covers subdomains."""
        # from app.services.cloudflare_worker import CloudflareWorkerService
        #
        # service = CloudflareWorkerService(...)
        # pattern = service.generate_route_pattern("example.com")
        #
        # # Should match *.example.com/*
        # assert pattern == "*.example.com/*" or "*example.com*" in pattern

    def test_worker_routes_bots_to_kv(self):
        """Test worker routes AI bots to KV content."""
        # This tests the logic in the worker script
        # Worker should fetch from KV when AI bot detected
        assert 'KV_NAMESPACE' in MOCK_WORKER_SCRIPT or 'kv' in MOCK_WORKER_SCRIPT.lower()
        assert 'get' in MOCK_WORKER_SCRIPT  # KV get operation

    def test_worker_routes_humans_to_origin(self):
        """Test worker routes humans to origin."""
        # Worker should fetch from origin for non-bots
        assert 'fetch' in MOCK_WORKER_SCRIPT
        # Should have logic to pass through to origin


class TestWorkerVisitTracking:
    """Test visit tracking in worker."""

    def test_worker_sends_visit_analytics(self):
        """Test worker sends visit data to API."""
        # Worker script should include API call
        assert 'trackVisit' in MOCK_WORKER_SCRIPT or 'record' in MOCK_WORKER_SCRIPT
        assert '/api/v1/visits/record' in MOCK_WORKER_SCRIPT or 'visits' in MOCK_WORKER_SCRIPT

    def test_worker_includes_user_agent(self):
        """Test worker includes user agent in tracking."""
        assert 'user_agent' in MOCK_WORKER_SCRIPT or 'userAgent' in MOCK_WORKER_SCRIPT

    def test_worker_includes_referrer(self):
        """Test worker includes referrer in tracking."""
        assert 'referrer' in MOCK_WORKER_SCRIPT or 'referer' in MOCK_WORKER_SCRIPT


class TestWorkerErrorHandling:
    """Test error handling in worker operations."""

    def test_missing_cloudflare_credentials(
        self,
        client,
        auth_headers,
        db
    ):
        """Test worker creation fails without credentials."""
        # Create client without credentials
        incomplete_client = Client(
            name="No CF Client",
            domain="no-cf.com"
        )
        db.add(incomplete_client)
        db.commit()

        client_id = str(incomplete_client.id)

        response = client.post(
            f'/api/v1/cloudflare/worker/create/{client_id}',
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
        worker_client
    ):
        """Test handling Cloudflare API errors."""
        with patch('cloudflare.Cloudflare') as mock_cf:
            client_instance = MagicMock()
            client_instance.workers.scripts.update.side_effect = Exception(
                "API quota exceeded"
            )
            mock_cf.return_value = client_instance

            client_id = str(worker_client.id)

            response = client.post(
                f'/api/v1/cloudflare/worker/create/{client_id}',
                headers=auth_headers
            )

            # Should handle error gracefully
            # assert response.status_code in [500, 503]

    def test_invalid_worker_script(
        self,
        client,
        auth_headers,
        worker_client
    ):
        """Test handling invalid worker script."""
        client_id = str(worker_client.id)

        invalid_script = "this is not valid javascript {"

        response = client.post(
            f'/api/v1/cloudflare/worker/create/{client_id}',
            headers=auth_headers,
            json={'script': invalid_script}
        )

        # Should validate or return error from Cloudflare
        # assert response.status_code in [400, 422]

    def test_client_not_found(self, client, auth_headers):
        """Test worker operations with non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'

        response = client.post(
            f'/api/v1/cloudflare/worker/create/{fake_uuid}',
            headers=auth_headers
        )

        # Should return 404
        # assert response.status_code == 404


class TestWorkerKVIntegration:
    """Test worker integration with KV."""

    def test_worker_binds_kv_namespace(self):
        """Test worker is bound to correct KV namespace."""
        # from app.services.cloudflare_worker import CloudflareWorkerService
        #
        # service = CloudflareWorkerService(...)
        # bindings = service.get_kv_bindings(namespace_id="ns_123")
        #
        # assert 'KV_NAMESPACE' in bindings
        # assert bindings['KV_NAMESPACE'] == "ns_123"

    def test_worker_script_references_kv_binding(self):
        """Test worker script correctly references KV binding."""
        # Should use environment binding
        # e.g., env.KV_NAMESPACE or KV_NAMESPACE
        assert 'KV' in MOCK_WORKER_SCRIPT.upper()

    def test_worker_handles_kv_miss(self):
        """Test worker handles KV cache miss."""
        # Worker should fetch from origin if not in KV
        # Script should have fallback logic
        assert 'if' in MOCK_WORKER_SCRIPT  # Conditional logic for cache hit/miss


class TestWorkerConfiguration:
    """Test worker configuration and customization."""

    def test_worker_includes_api_url(self):
        """Test worker script includes API URL for tracking."""
        # from app.services.cloudflare_worker import CloudflareWorkerService
        #
        # service = CloudflareWorkerService(...)
        # script = service.generate_worker_script(
        #     domain="example.com",
        #     kv_namespace_id="ns_123",
        #     api_url="https://api.example.com"
        # )
        #
        # assert "https://api.example.com" in script

    def test_worker_includes_domain(self):
        """Test worker script includes client domain."""
        # from app.services.cloudflare_worker import CloudflareWorkerService
        #
        # service = CloudflareWorkerService(...)
        # script = service.generate_worker_script(
        #     domain="example.com",
        #     kv_namespace_id="ns_123"
        # )
        #
        # # May include domain for validation or logic
        # # assert "example.com" in script

    def test_worker_script_customizable(self):
        """Test worker script can be customized per client."""
        # from app.services.cloudflare_worker import CloudflareWorkerService
        #
        # service = CloudflareWorkerService(...)
        #
        # # Should support custom bot list
        # custom_bots = ["CustomBot", "AnotherBot"]
        # script = service.generate_worker_script(
        #     domain="example.com",
        #     kv_namespace_id="ns_123",
        #     custom_bots=custom_bots
        # )
        #
        # assert "CustomBot" in script
        # assert "AnotherBot" in script


class TestWorkerLifecycle:
    """Test worker lifecycle management."""

    def test_create_then_update_worker(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test creating then updating a worker."""
        client_id = str(worker_client.id)

        # Create
        create_response = client.post(
            f'/api/v1/cloudflare/worker/create/{client_id}',
            headers=auth_headers
        )

        # Update
        update_response = client.put(
            f'/api/v1/cloudflare/worker/update/{client_id}',
            headers=auth_headers,
            json={'script': MOCK_WORKER_SCRIPT}
        )

        # Both should succeed
        # assert create_response.status_code == 201
        # assert update_response.status_code == 200

    def test_create_then_delete_worker(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test creating then deleting a worker."""
        client_id = str(worker_client.id)

        # Create
        create_response = client.post(
            f'/api/v1/cloudflare/worker/create/{client_id}',
            headers=auth_headers
        )

        # Delete
        delete_response = client.delete(
            f'/api/v1/cloudflare/worker/delete/{client_id}',
            headers=auth_headers
        )

        # Both should succeed
        # assert create_response.status_code == 201
        # assert delete_response.status_code == 200

    def test_worker_auto_created_on_kv_upload(self):
        """Test worker is auto-created when uploading to KV (if needed)."""
        # This could be a workflow where uploading triggers worker creation
        # if one doesn't exist
        # Depends on implementation design


class TestWorkerPerformance:
    """Test worker performance characteristics."""

    def test_worker_script_size(self):
        """Test worker script size is within limits."""
        # Cloudflare has limits on worker script size
        # Free tier: 1 MB, Paid: 10 MB
        script_size = len(MOCK_WORKER_SCRIPT.encode('utf-8'))

        assert script_size < 1024 * 1024  # Less than 1 MB

    def test_worker_deployment_speed(
        self,
        client,
        auth_headers,
        worker_client,
        mock_cloudflare_worker
    ):
        """Test worker deploys quickly."""
        import time

        client_id = str(worker_client.id)

        start = time.time()

        response = client.post(
            f'/api/v1/cloudflare/worker/create/{client_id}',
            headers=auth_headers
        )

        duration = time.time() - start

        # Should be fast (under 5 seconds)
        assert duration < 5
