"""
Cloudflare Workers API endpoints.

Provides endpoints for deploying, updating, and managing Cloudflare Workers for AI bot detection.
Supports worker deployment, status checking, and deletion.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from datetime import datetime
from uuid import UUID

from flask import Blueprint, jsonify, request

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client
from app.services.cloudflare_worker import CloudflareWorkerService
from app.config import settings

cloudflare_worker_bp = Blueprint('cloudflare_worker', __name__, url_prefix='/api/v1/cloudflare/worker')


@cloudflare_worker_bp.route('/create/<uuid:client_id>', methods=['POST'])
@require_api_key
def create_worker(client_id: UUID):
    """
    Deploy a Cloudflare Worker for AI bot detection.

    Creates and deploys a worker script that:
    - Detects AI bots (ChatGPT, Perplexity, Claude, etc.)
    - Routes bot traffic to KV-stored pages
    - Routes human traffic to origin
    - Sends analytics to API

    Args:
        client_id: Client UUID

    Request body:
        {
            "api_endpoint": "https://api.example.com",  // Optional: API endpoint for analytics (default: request host)
            "route_pattern": "*example.com/*",          // Optional: Worker route pattern (default: "*{domain}/*")
            "auto_create_route": true                    // Optional: Automatically create route (default: true)
        }

    Returns:
        JSON response with deployment result and updated client data

    Example:
        POST /api/v1/cloudflare/worker/create/{client_id}
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "api_endpoint": "https://api.myapp.com",
            "auto_create_route": true
        }

        Response:
        {
            "message": "Worker deployed successfully",
            "worker": {
                "script_name": "geo-bot-detector-abc123",
                "deployed": true,
                "route_created": true,
                "route_pattern": "*example.com/*"
            },
            "client": {
                "id": "...",
                "name": "Example Client",
                "worker_script_name": "geo-bot-detector-abc123",
                "worker_deployed_at": "2025-11-21T10:30:00",
                "worker_route_id": "route123",
                ...
            }
        }
    """
    data = request.get_json() or {}

    api_endpoint = data.get('api_endpoint', f"https://{request.host}")
    auto_create_route = data.get('auto_create_route', True)
    route_pattern = data.get('route_pattern', None)

    db = SessionLocal()

    try:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Validate client has required Cloudflare credentials
        if not all([
            client.cloudflare_account_id,
            client.cloudflare_api_token,
            client.cloudflare_kv_namespace_id
        ]):
            return jsonify({
                'error': 'Client missing required Cloudflare credentials',
                'message': 'Please configure cloudflare_account_id, cloudflare_api_token, and cloudflare_kv_namespace_id'
            }), 400

        # Validate zone_id if auto_create_route is enabled
        if auto_create_route and not client.cloudflare_zone_id:
            return jsonify({
                'error': 'Client missing cloudflare_zone_id',
                'message': 'Zone ID is required for automatic route creation. Set auto_create_route to false or configure zone_id.'
            }), 400

        # Generate worker script name
        worker_name = CloudflareWorkerService.generate_worker_name(str(client.id))

        print(f"[API] Deploying worker for client {client.name}: {worker_name}")

        # Create worker service
        worker_service = CloudflareWorkerService.from_client(client)
        if not worker_service:
            return jsonify({
                'error': 'Failed to create worker service',
                'message': 'Invalid Cloudflare credentials'
            }), 500

        # Load and prepare worker script
        try:
            template = CloudflareWorkerService.load_worker_template()
            script_content = CloudflareWorkerService.prepare_worker_script(
                template=template,
                kv_namespace_id=client.cloudflare_kv_namespace_id,
                api_endpoint=api_endpoint,
                api_key=settings.master_api_key,
                zone_name=client.domain,
                client_id=str(client.id)
            )
        except Exception as e:
            return jsonify({
                'error': 'Failed to prepare worker script',
                'message': str(e)
            }), 500

        # Deploy worker
        deploy_result = worker_service.deploy_worker(
            script_name=worker_name,
            script_content=script_content,
            kv_namespace_id=client.cloudflare_kv_namespace_id
        )

        if not deploy_result['success']:
            return jsonify({
                'message': 'Worker deployment failed',
                'error': deploy_result.get('error'),
                'worker': deploy_result
            }), 500

        # Update client with worker info
        client.worker_script_name = worker_name
        client.worker_deployed_at = datetime.utcnow()

        # Create route if requested
        route_created = False
        route_id = None
        final_route_pattern = None

        if auto_create_route:
            # Generate route pattern if not provided
            if not route_pattern:
                final_route_pattern = f"*{client.domain}/*"
            else:
                final_route_pattern = route_pattern

            print(f"[API] Creating route: {final_route_pattern} -> {worker_name}")

            route_result = worker_service.add_route(
                pattern=final_route_pattern,
                script_name=worker_name
            )

            if route_result['success']:
                route_created = True
                route_id = route_result.get('route_id')
                client.worker_route_id = route_id
                print(f"[API] Route created successfully: {route_id}")
            else:
                print(f"[API] Route creation failed: {route_result.get('error')}")

        db.commit()

        return jsonify({
            'message': 'Worker deployed successfully',
            'worker': {
                'script_name': worker_name,
                'deployed': True,
                'route_created': route_created,
                'route_pattern': final_route_pattern,
                'route_id': route_id
            },
            'client': client.to_dict()
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to deploy worker',
            'message': str(e)
        }), 500
    finally:
        db.close()


@cloudflare_worker_bp.route('/update/<uuid:client_id>', methods=['PUT'])
@require_api_key
def update_worker(client_id: UUID):
    """
    Update an existing Cloudflare Worker script.

    Re-deploys the worker with updated configuration or script template.

    Args:
        client_id: Client UUID

    Request body:
        {
            "api_endpoint": "https://api.example.com",  // Optional: Update API endpoint
        }

    Returns:
        JSON response with update result

    Example:
        PUT /api/v1/cloudflare/worker/update/{client_id}
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "api_endpoint": "https://api.myapp.com"
        }

        Response:
        {
            "message": "Worker updated successfully",
            "worker": {
                "script_name": "geo-bot-detector-abc123",
                "updated": true
            },
            "client": {...}
        }
    """
    data = request.get_json() or {}

    api_endpoint = data.get('api_endpoint', f"https://{request.host}")

    db = SessionLocal()

    try:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Check if worker is deployed
        if not client.worker_script_name:
            return jsonify({
                'error': 'Worker not deployed',
                'message': 'Use /create endpoint to deploy a worker first'
            }), 400

        # Validate credentials
        if not all([
            client.cloudflare_account_id,
            client.cloudflare_api_token,
            client.cloudflare_kv_namespace_id
        ]):
            return jsonify({
                'error': 'Client missing required Cloudflare credentials',
                'message': 'Please configure cloudflare_account_id, cloudflare_api_token, and cloudflare_kv_namespace_id'
            }), 400

        print(f"[API] Updating worker for client {client.name}: {client.worker_script_name}")

        # Create worker service
        worker_service = CloudflareWorkerService.from_client(client)
        if not worker_service:
            return jsonify({
                'error': 'Failed to create worker service',
                'message': 'Invalid Cloudflare credentials'
            }), 500

        # Load and prepare worker script
        try:
            template = CloudflareWorkerService.load_worker_template()
            script_content = CloudflareWorkerService.prepare_worker_script(
                template=template,
                kv_namespace_id=client.cloudflare_kv_namespace_id,
                api_endpoint=api_endpoint,
                api_key=settings.master_api_key,
                zone_name=client.domain,
                client_id=str(client.id)
            )
        except Exception as e:
            return jsonify({
                'error': 'Failed to prepare worker script',
                'message': str(e)
            }), 500

        # Re-deploy worker (PUT replaces existing script)
        deploy_result = worker_service.deploy_worker(
            script_name=client.worker_script_name,
            script_content=script_content,
            kv_namespace_id=client.cloudflare_kv_namespace_id
        )

        if not deploy_result['success']:
            return jsonify({
                'message': 'Worker update failed',
                'error': deploy_result.get('error'),
                'worker': deploy_result
            }), 500

        # Update timestamp
        client.worker_deployed_at = datetime.utcnow()
        db.commit()

        return jsonify({
            'message': 'Worker updated successfully',
            'worker': {
                'script_name': client.worker_script_name,
                'updated': True
            },
            'client': client.to_dict()
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to update worker',
            'message': str(e)
        }), 500
    finally:
        db.close()


@cloudflare_worker_bp.route('/status/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_worker_status(client_id: UUID):
    """
    Get status of Cloudflare Worker deployment.

    Returns information about the worker script and routes.

    Args:
        client_id: Client UUID

    Returns:
        JSON response with worker status

    Example:
        GET /api/v1/cloudflare/worker/status/{client_id}
        Headers:
            X-API-Key: your-master-api-key

        Response:
        {
            "worker": {
                "script_name": "geo-bot-detector-abc123",
                "deployed": true,
                "exists": true,
                "created_on": "2025-11-20T10:00:00",
                "modified_on": "2025-11-21T10:30:00"
            },
            "routes": [
                {
                    "id": "route123",
                    "pattern": "*example.com/*",
                    "script": "geo-bot-detector-abc123"
                }
            ],
            "client": {...}
        }
    """
    db = SessionLocal()

    try:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Check if worker is deployed
        if not client.worker_script_name:
            return jsonify({
                'worker': {
                    'deployed': False,
                    'exists': False,
                    'message': 'No worker deployed for this client'
                },
                'routes': [],
                'client': client.to_dict()
            }), 200

        # Validate credentials
        if not all([
            client.cloudflare_account_id,
            client.cloudflare_api_token
        ]):
            return jsonify({
                'error': 'Client missing required Cloudflare credentials',
                'message': 'Please configure cloudflare_account_id and cloudflare_api_token'
            }), 400

        # Create worker service
        worker_service = CloudflareWorkerService.from_client(client)
        if not worker_service:
            return jsonify({
                'error': 'Failed to create worker service',
                'message': 'Invalid Cloudflare credentials'
            }), 500

        # Get worker status
        worker_result = worker_service.get_worker(client.worker_script_name)

        # Get routes if zone_id is configured
        routes_result = {'success': False, 'routes': [], 'count': 0}
        if client.cloudflare_zone_id:
            routes_result = worker_service.list_routes()

        return jsonify({
            'worker': {
                'script_name': client.worker_script_name,
                'deployed': client.worker_deployed_at is not None,
                'deployed_at': client.worker_deployed_at.isoformat() if client.worker_deployed_at else None,
                'exists': worker_result.get('exists', False),
                'created_on': worker_result.get('created_on'),
                'modified_on': worker_result.get('modified_on'),
                'error': worker_result.get('error')
            },
            'routes': routes_result.get('routes', []),
            'route_count': routes_result.get('count', 0),
            'client': client.to_dict()
        }), 200

    except Exception as e:
        return jsonify({
            'error': 'Failed to get worker status',
            'message': str(e)
        }), 500
    finally:
        db.close()


@cloudflare_worker_bp.route('/delete/<uuid:client_id>', methods=['DELETE'])
@require_api_key
def delete_worker(client_id: UUID):
    """
    Delete a Cloudflare Worker deployment.

    Removes the worker script and optionally removes routes.

    Args:
        client_id: Client UUID

    Request body:
        {
            "delete_routes": true  // Optional: Also delete associated routes (default: true)
        }

    Returns:
        JSON response with deletion result

    Example:
        DELETE /api/v1/cloudflare/worker/delete/{client_id}
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "delete_routes": true
        }

        Response:
        {
            "message": "Worker deleted successfully",
            "worker": {
                "script_name": "geo-bot-detector-abc123",
                "deleted": true,
                "routes_deleted": true
            },
            "client": {...}
        }
    """
    data = request.get_json() or {}

    delete_routes = data.get('delete_routes', True)

    db = SessionLocal()

    try:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Check if worker is deployed
        if not client.worker_script_name:
            return jsonify({
                'error': 'Worker not deployed',
                'message': 'No worker to delete'
            }), 400

        # Validate credentials
        if not all([
            client.cloudflare_account_id,
            client.cloudflare_api_token
        ]):
            return jsonify({
                'error': 'Client missing required Cloudflare credentials',
                'message': 'Please configure cloudflare_account_id and cloudflare_api_token'
            }), 400

        print(f"[API] Deleting worker for client {client.name}: {client.worker_script_name}")

        # Create worker service
        worker_service = CloudflareWorkerService.from_client(client)
        if not worker_service:
            return jsonify({
                'error': 'Failed to create worker service',
                'message': 'Invalid Cloudflare credentials'
            }), 500

        # Delete routes if requested
        routes_deleted = False
        if delete_routes and client.worker_route_id and client.cloudflare_zone_id:
            print(f"[API] Deleting route: {client.worker_route_id}")

            route_result = worker_service.delete_route(client.worker_route_id)
            if route_result['success']:
                routes_deleted = True
                print(f"[API] Route deleted successfully")
            else:
                print(f"[API] Route deletion failed: {route_result.get('error')}")

        # Delete worker script
        delete_result = worker_service.delete_worker(client.worker_script_name)

        if not delete_result['success']:
            return jsonify({
                'message': 'Worker deletion failed',
                'error': delete_result.get('error'),
                'worker': delete_result
            }), 500

        # Clear worker metadata from client
        worker_name = client.worker_script_name
        client.worker_script_name = None
        client.worker_deployed_at = None
        client.worker_route_id = None

        db.commit()

        return jsonify({
            'message': 'Worker deleted successfully',
            'worker': {
                'script_name': worker_name,
                'deleted': True,
                'routes_deleted': routes_deleted
            },
            'client': client.to_dict()
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to delete worker',
            'message': str(e)
        }), 500
    finally:
        db.close()
