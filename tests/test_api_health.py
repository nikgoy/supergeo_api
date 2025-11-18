"""
Tests for health check API endpoints.

Tests /health and /ping endpoints.
"""
import pytest


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_check_success(self, client):
        """Test health check returns 200 OK."""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()

        assert 'status' in data
        assert 'database' in data
        assert 'version' in data

        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'

    def test_health_check_has_version(self, client):
        """Test health check includes version."""
        response = client.get('/health')
        data = response.get_json()

        assert 'version' in data
        assert isinstance(data['version'], str)

    def test_health_check_json_response(self, client):
        """Test health check returns JSON."""
        response = client.get('/health')

        assert response.content_type == 'application/json'

    def test_health_check_no_auth_required(self, client):
        """Test health check doesn't require authentication."""
        # Should work without X-API-Key header
        response = client.get('/health')

        assert response.status_code == 200


class TestPingEndpoint:
    """Test /ping endpoint."""

    def test_ping_returns_pong(self, client):
        """Test ping returns pong message."""
        response = client.get('/ping')

        assert response.status_code == 200
        data = response.get_json()

        assert 'message' in data
        assert data['message'] == 'pong'

    def test_ping_no_auth_required(self, client):
        """Test ping doesn't require authentication."""
        response = client.get('/ping')

        assert response.status_code == 200

    def test_ping_json_response(self, client):
        """Test ping returns JSON."""
        response = client.get('/ping')

        assert response.content_type == 'application/json'
