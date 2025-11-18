"""
Client CRUD API endpoints.

Provides REST API for managing clients and their Cloudflare credentials.
All endpoints require API key authentication via X-API-Key header.
"""
from uuid import UUID

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client

clients_bp = Blueprint('clients', __name__, url_prefix='/api/v1/clients')


@clients_bp.route('', methods=['GET'])
@require_api_key
def list_clients():
    """
    List all clients.

    Returns:
        JSON array of clients (without decrypted secrets)

    Example:
        GET /api/v1/clients
        Headers: X-API-Key: your-master-api-key

        Response:
        {
            "clients": [
                {
                    "id": "...",
                    "name": "Example Corp",
                    "domain": "example.com",
                    ...
                }
            ],
            "count": 1
        }
    """
    db = SessionLocal()
    try:
        clients = db.query(Client).all()
        return jsonify({
            'clients': [client.to_dict() for client in clients],
            'count': len(clients)
        }), 200
    finally:
        db.close()


@clients_bp.route('/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_client(client_id: UUID):
    """
    Get a specific client by ID.

    Args:
        client_id: Client UUID

    Returns:
        JSON object with client details

    Example:
        GET /api/v1/clients/{client_id}
        Headers: X-API-Key: your-master-api-key
    """
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()

        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Include secrets if requested via query param
        include_secrets = request.args.get('include_secrets', 'false').lower() == 'true'

        return jsonify(client.to_dict(include_secrets=include_secrets)), 200
    finally:
        db.close()


@clients_bp.route('', methods=['POST'])
@require_api_key
def create_client():
    """
    Create a new client.

    Request body:
        {
            "name": "Client Name",
            "domain": "example.com",
            "cloudflare_account_id": "...",  // optional
            "cloudflare_api_token": "...",   // optional, will be encrypted
            "cloudflare_kv_namespace_id": "...",  // optional
            "gemini_api_key": "...",  // optional, will be encrypted
            "is_active": true  // optional, defaults to true
        }

    Returns:
        JSON object with created client

    Example:
        POST /api/v1/clients
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "name": "Example Corp",
            "domain": "example.com",
            "cloudflare_account_id": "abc123",
            "cloudflare_api_token": "secret-token",
            "cloudflare_kv_namespace_id": "kv123"
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate required fields
    if 'name' not in data or 'domain' not in data:
        return jsonify({'error': 'name and domain are required'}), 400

    db = SessionLocal()
    try:
        # Create new client
        client = Client(
            name=data['name'],
            domain=data['domain'],
            cloudflare_account_id=data.get('cloudflare_account_id'),
            cloudflare_kv_namespace_id=data.get('cloudflare_kv_namespace_id'),
            is_active=data.get('is_active', True)
        )

        # Set encrypted fields using properties
        if 'cloudflare_api_token' in data and data['cloudflare_api_token']:
            client.cloudflare_api_token = data['cloudflare_api_token']

        if 'gemini_api_key' in data and data['gemini_api_key']:
            client.gemini_api_key = data['gemini_api_key']

        db.add(client)
        db.commit()
        db.refresh(client)

        return jsonify({
            'message': 'Client created successfully',
            'client': client.to_dict()
        }), 201

    except IntegrityError as e:
        db.rollback()
        # Check if it's a uniqueness violation
        if 'unique' in str(e).lower():
            return jsonify({
                'error': 'Client with this name or domain already exists'
            }), 409
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to create client: {str(e)}'}), 500
    finally:
        db.close()


@clients_bp.route('/<uuid:client_id>', methods=['PUT', 'PATCH'])
@require_api_key
def update_client(client_id: UUID):
    """
    Update an existing client.

    Args:
        client_id: Client UUID

    Request body: Same as create_client (all fields optional)

    Returns:
        JSON object with updated client

    Example:
        PUT /api/v1/clients/{client_id}
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "cloudflare_api_token": "new-secret-token",
            "is_active": false
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()

        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Update fields
        if 'name' in data:
            client.name = data['name']
        if 'domain' in data:
            client.domain = data['domain']
        if 'cloudflare_account_id' in data:
            client.cloudflare_account_id = data['cloudflare_account_id']
        if 'cloudflare_kv_namespace_id' in data:
            client.cloudflare_kv_namespace_id = data['cloudflare_kv_namespace_id']
        if 'is_active' in data:
            client.is_active = data['is_active']

        # Update encrypted fields
        if 'cloudflare_api_token' in data:
            if data['cloudflare_api_token']:
                client.cloudflare_api_token = data['cloudflare_api_token']
            else:
                client.cloudflare_api_token = None

        if 'gemini_api_key' in data:
            if data['gemini_api_key']:
                client.gemini_api_key = data['gemini_api_key']
            else:
                client.gemini_api_key = None

        db.commit()
        db.refresh(client)

        return jsonify({
            'message': 'Client updated successfully',
            'client': client.to_dict()
        }), 200

    except IntegrityError as e:
        db.rollback()
        if 'unique' in str(e).lower():
            return jsonify({
                'error': 'Client with this name or domain already exists'
            }), 409
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to update client: {str(e)}'}), 500
    finally:
        db.close()


@clients_bp.route('/<uuid:client_id>', methods=['DELETE'])
@require_api_key
def delete_client(client_id: UUID):
    """
    Delete a client.

    Args:
        client_id: Client UUID

    Returns:
        JSON confirmation message

    Note:
        This will cascade delete all associated pages and visits.

    Example:
        DELETE /api/v1/clients/{client_id}
        Headers: X-API-Key: your-master-api-key
    """
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()

        if not client:
            return jsonify({'error': 'Client not found'}), 404

        client_name = client.name
        db.delete(client)
        db.commit()

        return jsonify({
            'message': f'Client {client_name} deleted successfully'
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to delete client: {str(e)}'}), 500
    finally:
        db.close()


@clients_bp.route('/by-domain/<domain>', methods=['GET'])
@require_api_key
def get_client_by_domain(domain: str):
    """
    Get a client by domain name.

    Args:
        domain: Domain name (e.g., example.com)

    Returns:
        JSON object with client details

    Example:
        GET /api/v1/clients/by-domain/example.com
        Headers: X-API-Key: your-master-api-key
    """
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.domain == domain).first()

        if not client:
            return jsonify({'error': 'Client not found'}), 404

        include_secrets = request.args.get('include_secrets', 'false').lower() == 'true'
        return jsonify(client.to_dict(include_secrets=include_secrets)), 200
    finally:
        db.close()
