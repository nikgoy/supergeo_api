"""
Tests for client CRUD API endpoints.

Tests all /api/v1/clients endpoints.
"""
import pytest
import json


class TestListClients:
    """Test GET /api/v1/clients endpoint."""

    def test_list_clients_requires_auth(self, client):
        """Test listing clients requires API key."""
        response = client.get('/api/v1/clients')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_list_clients_invalid_api_key(self, client):
        """Test listing clients with invalid API key."""
        response = client.get(
            '/api/v1/clients',
            headers={'X-API-Key': 'wrong-key'}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Invalid API key'

    def test_list_clients_empty(self, client, auth_headers, db):
        """Test listing clients when database is empty."""
        response = client.get('/api/v1/clients', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert 'clients' in data
        assert 'count' in data
        assert data['count'] == 0
        assert data['clients'] == []

    def test_list_clients_with_data(self, client, auth_headers, sample_client):
        """Test listing clients with data."""
        response = client.get('/api/v1/clients', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['count'] == 1
        assert len(data['clients']) == 1

        client_data = data['clients'][0]
        assert client_data['name'] == 'Test Corp'
        assert client_data['domain'] == 'test.com'

    def test_list_clients_hides_secrets(self, client, auth_headers, sample_client):
        """Test that listing clients doesn't expose secrets."""
        response = client.get('/api/v1/clients', headers=auth_headers)
        data = response.get_json()

        client_data = data['clients'][0]

        # Should not include decrypted secrets
        assert 'cloudflare_api_token' not in client_data
        assert 'gemini_api_key' not in client_data

        # Should include flags
        assert client_data['has_cloudflare_token'] is True
        assert client_data['has_gemini_key'] is True

    def test_list_multiple_clients(self, client, auth_headers, multiple_clients):
        """Test listing multiple clients."""
        response = client.get('/api/v1/clients', headers=auth_headers)
        data = response.get_json()

        assert data['count'] == 5
        assert len(data['clients']) == 5


class TestGetClient:
    """Test GET /api/v1/clients/{id} endpoint."""

    def test_get_client_requires_auth(self, client, sample_client):
        """Test getting client requires API key."""
        response = client.get(f'/api/v1/clients/{sample_client.id}')

        assert response.status_code == 401

    def test_get_client_success(self, client, auth_headers, sample_client):
        """Test getting a client by ID."""
        response = client.get(
            f'/api/v1/clients/{sample_client.id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['id'] == str(sample_client.id)
        assert data['name'] == 'Test Corp'
        assert data['domain'] == 'test.com'

    def test_get_client_not_found(self, client, auth_headers):
        """Test getting non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = client.get(
            f'/api/v1/clients/{fake_uuid}',
            headers=auth_headers
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'Client not found'

    def test_get_client_hides_secrets_by_default(self, client, auth_headers, sample_client):
        """Test that getting client hides secrets by default."""
        response = client.get(
            f'/api/v1/clients/{sample_client.id}',
            headers=auth_headers
        )

        data = response.get_json()

        assert 'cloudflare_api_token' not in data
        assert 'gemini_api_key' not in data
        assert data['has_cloudflare_token'] is True

    def test_get_client_include_secrets(self, client, auth_headers, sample_client):
        """Test getting client with secrets."""
        response = client.get(
            f'/api/v1/clients/{sample_client.id}?include_secrets=true',
            headers=auth_headers
        )

        data = response.get_json()

        assert 'cloudflare_api_token' in data
        assert data['cloudflare_api_token'] == 'test-cloudflare-token'
        assert data['gemini_api_key'] == 'test-gemini-key'


class TestCreateClient:
    """Test POST /api/v1/clients endpoint."""

    def test_create_client_requires_auth(self, client):
        """Test creating client requires API key."""
        response = client.post(
            '/api/v1/clients',
            json={'name': 'Test', 'domain': 'test.com'}
        )

        assert response.status_code == 401

    def test_create_client_success(self, client, auth_headers, db):
        """Test creating a new client."""
        payload = {
            'name': 'New Corp',
            'domain': 'new.com',
            'cloudflare_account_id': 'account-123',
            'cloudflare_api_token': 'secret-token',
            'cloudflare_kv_namespace_id': 'kv-123'
        }

        response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 201
        data = response.get_json()

        assert 'message' in data
        assert 'client' in data
        assert data['client']['name'] == 'New Corp'
        assert data['client']['domain'] == 'new.com'

    def test_create_client_minimal_fields(self, client, auth_headers):
        """Test creating client with only required fields."""
        payload = {
            'name': 'Minimal Corp',
            'domain': 'minimal.com'
        }

        response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 201
        data = response.get_json()

        assert data['client']['name'] == 'Minimal Corp'
        assert data['client']['domain'] == 'minimal.com'

    def test_create_client_missing_name(self, client, auth_headers):
        """Test creating client without name."""
        payload = {'domain': 'test.com'}

        response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_client_missing_domain(self, client, auth_headers):
        """Test creating client without domain."""
        payload = {'name': 'Test Corp'}

        response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 400

    def test_create_client_duplicate_name(self, client, auth_headers, sample_client):
        """Test creating client with duplicate name."""
        payload = {
            'name': sample_client.name,  # Duplicate
            'domain': 'different.com'
        }

        response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 409  # Conflict
        data = response.get_json()
        assert 'already exists' in data['error'].lower()

    def test_create_client_duplicate_domain(self, client, auth_headers, sample_client):
        """Test creating client with duplicate domain."""
        payload = {
            'name': 'Different Corp',
            'domain': sample_client.domain  # Duplicate
        }

        response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 409

    def test_create_client_no_body(self, client, auth_headers):
        """Test creating client without request body."""
        response = client.post(
            '/api/v1/clients',
            headers=auth_headers
        )

        assert response.status_code == 400

    def test_create_client_encrypts_secrets(self, client, auth_headers, db):
        """Test that creating client encrypts secrets."""
        payload = {
            'name': 'Secure Corp',
            'domain': 'secure.com',
            'cloudflare_api_token': 'super-secret-token',
            'gemini_api_key': 'gemini-secret-key'
        }

        response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 201
        data = response.get_json()

        # Response should not include secrets
        assert 'cloudflare_api_token' not in data['client']
        assert 'gemini_api_key' not in data['client']

        # But should indicate they exist
        assert data['client']['has_cloudflare_token'] is True
        assert data['client']['has_gemini_key'] is True


class TestUpdateClient:
    """Test PUT/PATCH /api/v1/clients/{id} endpoint."""

    def test_update_client_requires_auth(self, client, sample_client):
        """Test updating client requires API key."""
        response = client.put(
            f'/api/v1/clients/{sample_client.id}',
            json={'name': 'Updated'}
        )

        assert response.status_code == 401

    def test_update_client_success(self, client, auth_headers, sample_client):
        """Test updating a client."""
        payload = {'name': 'Updated Corp'}

        response = client.put(
            f'/api/v1/clients/{sample_client.id}',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['client']['name'] == 'Updated Corp'
        assert data['client']['domain'] == 'test.com'  # Unchanged

    def test_update_client_patch_method(self, client, auth_headers, sample_client):
        """Test updating client with PATCH method."""
        payload = {'is_active': False}

        response = client.patch(
            f'/api/v1/clients/{sample_client.id}',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['client']['is_active'] is False

    def test_update_client_not_found(self, client, auth_headers):
        """Test updating non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = client.put(
            f'/api/v1/clients/{fake_uuid}',
            headers=auth_headers,
            json={'name': 'Test'}
        )

        assert response.status_code == 404

    def test_update_client_secrets(self, client, auth_headers, sample_client):
        """Test updating client secrets."""
        payload = {
            'cloudflare_api_token': 'new-secret-token',
            'gemini_api_key': 'new-gemini-key'
        }

        response = client.put(
            f'/api/v1/clients/{sample_client.id}',
            headers=auth_headers,
            json=payload
        )

        assert response.status_code == 200

        # Verify secrets were updated (need to query with include_secrets)
        get_response = client.get(
            f'/api/v1/clients/{sample_client.id}?include_secrets=true',
            headers=auth_headers
        )

        data = get_response.get_json()
        assert data['cloudflare_api_token'] == 'new-secret-token'
        assert data['gemini_api_key'] == 'new-gemini-key'

    def test_update_client_no_body(self, client, auth_headers, sample_client):
        """Test updating client without request body."""
        response = client.put(
            f'/api/v1/clients/{sample_client.id}',
            headers=auth_headers
        )

        assert response.status_code == 400


class TestDeleteClient:
    """Test DELETE /api/v1/clients/{id} endpoint."""

    def test_delete_client_requires_auth(self, client, sample_client):
        """Test deleting client requires API key."""
        response = client.delete(f'/api/v1/clients/{sample_client.id}')

        assert response.status_code == 401

    def test_delete_client_success(self, client, auth_headers, sample_client, db):
        """Test deleting a client."""
        client_id = sample_client.id

        response = client.delete(
            f'/api/v1/clients/{client_id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'deleted successfully' in data['message'].lower()

        # Verify client is deleted
        from app.models.client import Client
        deleted_client = db.query(Client).filter(Client.id == client_id).first()
        assert deleted_client is None

    def test_delete_client_not_found(self, client, auth_headers):
        """Test deleting non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = client.delete(
            f'/api/v1/clients/{fake_uuid}',
            headers=auth_headers
        )

        assert response.status_code == 404


class TestGetClientByDomain:
    """Test GET /api/v1/clients/by-domain/{domain} endpoint."""

    def test_get_by_domain_requires_auth(self, client, sample_client):
        """Test getting client by domain requires API key."""
        response = client.get(f'/api/v1/clients/by-domain/{sample_client.domain}')

        assert response.status_code == 401

    def test_get_by_domain_success(self, client, auth_headers, sample_client):
        """Test getting client by domain."""
        response = client.get(
            f'/api/v1/clients/by-domain/{sample_client.domain}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['domain'] == sample_client.domain
        assert data['name'] == sample_client.name

    def test_get_by_domain_not_found(self, client, auth_headers):
        """Test getting client by non-existent domain."""
        response = client.get(
            '/api/v1/clients/by-domain/nonexistent.com',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_by_domain_include_secrets(self, client, auth_headers, sample_client):
        """Test getting client by domain with secrets."""
        response = client.get(
            f'/api/v1/clients/by-domain/{sample_client.domain}?include_secrets=true',
            headers=auth_headers
        )

        data = response.get_json()

        assert 'cloudflare_api_token' in data
        assert data['cloudflare_api_token'] == 'test-cloudflare-token'
