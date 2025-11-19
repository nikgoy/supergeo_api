"""
Page Analytics API endpoints.

Provides endpoints for calculating and retrieving page analytics.
All endpoints require API key authentication via X-API-Key header.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from uuid import UUID

from flask import Blueprint, jsonify, request

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.services.page_analytics import page_analytics_service

page_analytics_bp = Blueprint('page_analytics', __name__, url_prefix='/api/v1/pages_analytics')


@page_analytics_bp.route('/client/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_client_analytics(client_id: UUID):
    """
    Get analytics for a specific client.

    Args:
        client_id: Client UUID

    Returns:
        JSON object with page analytics

    Example:
        GET /api/v1/pages_analytics/client/{client_id}
        Headers: X-API-Key: your-master-api-key

        Response:
        {
            "id": "...",
            "client_id": "...",
            "total_urls": 100,
            "urls_with_raw_html": 80,
            "urls_with_markdown": 60,
            "urls_with_simple_html": 50,
            "urls_with_kv_key": 40,
            "html_completion_rate": 80.0,
            "markdown_completion_rate": 60.0,
            "simple_html_completion_rate": 50.0,
            "kv_upload_completion_rate": 40.0,
            "pages_updated_last_30_days": 15,
            "last_calculated_at": "2025-11-19T10:30:00",
            "created_at": "2025-11-19T10:00:00",
            "updated_at": "2025-11-19T10:30:00"
        }
    """
    db = SessionLocal()
    try:
        analytics = page_analytics_service.get_analytics(db, client_id)

        if not analytics:
            return jsonify({
                'error': 'Analytics not found for this client',
                'message': 'Use POST /api/v1/pages_analytics/calculate/{client_id} to generate analytics first'
            }), 404

        return jsonify(analytics.to_dict()), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get analytics: {str(e)}'}), 500
    finally:
        db.close()


@page_analytics_bp.route('/calculate/<uuid:client_id>', methods=['POST'])
@require_api_key
def calculate_client_analytics(client_id: UUID):
    """
    Trigger analytics calculation for a specific client.

    This endpoint calculates fresh analytics from the pages table
    and updates or creates the analytics record.

    Args:
        client_id: Client UUID

    Returns:
        JSON object with calculated analytics

    Example:
        POST /api/v1/pages_analytics/calculate/{client_id}
        Headers: X-API-Key: your-master-api-key

        Response:
        {
            "message": "Analytics calculated successfully",
            "analytics": {
                "id": "...",
                "client_id": "...",
                "total_urls": 100,
                ...
            }
        }
    """
    db = SessionLocal()
    try:
        analytics = page_analytics_service.calculate_analytics(db, client_id)

        return jsonify({
            'message': 'Analytics calculated successfully',
            'analytics': analytics.to_dict()
        }), 200

    except ValueError as e:
        # Client not found
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to calculate analytics: {str(e)}'}), 500
    finally:
        db.close()


@page_analytics_bp.route('', methods=['GET'])
@require_api_key
def get_all_analytics():
    """
    Get analytics for all clients with pagination.

    Query parameters:
        - limit: Maximum number of results (default: 100, max: 1000)
        - offset: Pagination offset (default: 0)

    Returns:
        JSON array of analytics with pagination info

    Example:
        GET /api/v1/pages_analytics?limit=10&offset=0
        Headers: X-API-Key: your-master-api-key

        Response:
        {
            "analytics": [
                {
                    "id": "...",
                    "client_id": "...",
                    "total_urls": 100,
                    ...
                },
                ...
            ],
            "count": 10,
            "total": 25,
            "limit": 10,
            "offset": 0
        }
    """
    db = SessionLocal()
    try:
        # Get pagination parameters
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))

        analytics_list, total = page_analytics_service.get_all_analytics(
            db, limit=limit, offset=offset
        )

        return jsonify({
            'analytics': [analytics.to_dict() for analytics in analytics_list],
            'count': len(analytics_list),
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200

    except ValueError as e:
        return jsonify({'error': f'Invalid parameters: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to get analytics: {str(e)}'}), 500
    finally:
        db.close()


@page_analytics_bp.route('/calculate-all', methods=['POST'])
@require_api_key
def calculate_all_analytics():
    """
    Trigger analytics calculation for all active clients.

    This endpoint calculates fresh analytics for all clients
    and updates or creates their analytics records.

    Returns:
        JSON object with calculation summary

    Example:
        POST /api/v1/pages_analytics/calculate-all
        Headers: X-API-Key: your-master-api-key

        Response:
        {
            "message": "Analytics calculated for all clients",
            "total_calculated": 5,
            "analytics": [
                {
                    "id": "...",
                    "client_id": "...",
                    "total_urls": 100,
                    ...
                },
                ...
            ]
        }
    """
    db = SessionLocal()
    try:
        analytics_list = page_analytics_service.calculate_all_analytics(db)

        return jsonify({
            'message': 'Analytics calculated for all clients',
            'total_calculated': len(analytics_list),
            'analytics': [analytics.to_dict() for analytics in analytics_list]
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to calculate analytics: {str(e)}'}), 500
    finally:
        db.close()
