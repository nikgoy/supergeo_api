"""
llms.txt API endpoints.

Provides endpoints for generating llms.txt format content from client pages.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from uuid import UUID

from flask import Blueprint, jsonify, request

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client
from app.services.llms_txt import llms_txt_service

llms_txt_bp = Blueprint('llms_txt', __name__, url_prefix='/api/v1/llms-txt')


@llms_txt_bp.route('/generate/<uuid:client_id>', methods=['GET'])
@require_api_key
def generate_llms_txt(client_id: UUID):
    """
    Generate llms.txt for a client.

    Generates llms.txt format (https://llmstxt.org/) containing all pages
    with geo_html content. The format includes:
    - Site name (H1)
    - Site description (blockquote)
    - List of pages with titles, URLs, and descriptions

    Args:
        client_id: UUID of the client

    Query Parameters:
        force_regenerate: (optional) Force regeneration, bypassing cache

    Returns:
        JSON response with llms.txt content

    Example:
        GET /api/v1/llms-txt/generate/123e4567-e89b-12d3-a456-426614174000
        Headers:
            X-API-Key: your-master-api-key

        Response:
        {
            "llms_txt": "# Test Shop\\n\\n> Site description...\\n\\n## Pages\\n...",
            "page_count": 5,
            "generated_at": "2025-11-21T10:00:00.000000",
            "client": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Test Shop",
                "domain": "test-shop.myshopify.com"
            }
        }
    """
    db = SessionLocal()
    try:
        # Check if client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({
                'error': 'Client not found',
                'message': f'No client found with ID: {client_id}'
            }), 404

        # Check for force_regenerate parameter
        force_regenerate = request.args.get('force_regenerate', 'false').lower() == 'true'

        if force_regenerate:
            llms_txt_service.invalidate_cache(client_id)

        # Generate llms.txt
        try:
            result = llms_txt_service.generate_for_client(client_id)
        except ValueError as e:
            return jsonify({
                'error': 'Generation failed',
                'message': str(e)
            }), 400

        # Add client info to response
        result['client'] = {
            'id': str(client.id),
            'name': client.name,
            'domain': client.domain
        }

        return jsonify(result), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to generate llms.txt',
            'message': str(e)
        }), 500
    finally:
        db.close()


@llms_txt_bp.route('/invalidate-cache/<uuid:client_id>', methods=['POST'])
@require_api_key
def invalidate_cache(client_id: UUID):
    """
    Invalidate llms.txt cache for a client.

    Useful when pages are updated and you want to force regeneration
    on the next request.

    Args:
        client_id: UUID of the client

    Returns:
        JSON response confirming cache invalidation

    Example:
        POST /api/v1/llms-txt/invalidate-cache/123e4567-e89b-12d3-a456-426614174000
        Headers:
            X-API-Key: your-master-api-key

        Response:
        {
            "message": "Cache invalidated successfully",
            "client_id": "123e4567-e89b-12d3-a456-426614174000"
        }
    """
    db = SessionLocal()
    try:
        # Check if client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({
                'error': 'Client not found',
                'message': f'No client found with ID: {client_id}'
            }), 404

        # Invalidate cache
        llms_txt_service.invalidate_cache(client_id)

        return jsonify({
            'message': 'Cache invalidated successfully',
            'client_id': str(client_id)
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to invalidate cache',
            'message': str(e)
        }), 500
    finally:
        db.close()
