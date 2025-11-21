"""
Visit Tracking API endpoints.

Provides endpoints for recording visits and retrieving analytics.
Designed to be called by Cloudflare Workers to track bot and human visits.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from uuid import UUID
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client, Page, Visit
from app.services.visit_analytics import (
    detect_bot_from_user_agent,
    determine_visitor_type,
    get_visit_stats,
    get_dashboard_analytics,
    get_page_visit_stats,
    get_top_bots,
    get_top_pages
)

visits_bp = Blueprint('visits', __name__, url_prefix='/api/v1/visits')


@visits_bp.route('/record', methods=['POST'])
@require_api_key
def record_visit():
    """
    Record a visit from Cloudflare Worker.

    Called by the Cloudflare Worker to track both AI bot and human visits.
    IP addresses are hashed for privacy.

    Request body:
        {
            "client_id": "uuid",          // Required: Client UUID
            "url": "https://...",         // Required: Visited URL
            "user_agent": "...",          // Required: User agent string
            "ip": "192.168.1.1",          // Required: IP address (will be hashed)
            "page_id": "uuid",            // Optional: Page UUID (auto-lookup if not provided)
            "referrer": "https://...",    // Optional: Referrer URL
            "bot_name": "ChatGPT"         // Optional: Bot name (auto-detected if not provided)
        }

    Returns:
        JSON response with visit_id

    Example:
        POST /api/v1/visits/record
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "client_id": "123e4567-e89b-12d3-a456-426614174000",
            "url": "https://shop.myshopify.com/products/shirt",
            "user_agent": "Mozilla/5.0 AppleWebKit/537.36; ChatGPT-User/1.0",
            "ip": "203.0.113.42",
            "referrer": "https://chat.openai.com/c/abc123",
            "bot_name": "ChatGPT"
        }

        Response:
        {
            "success": true,
            "visit_id": "456e7890-e89b-12d3-a456-426614174111",
            "visitor_type": "ai_bot",
            "bot_detected": true,
            "bot_name": "ChatGPT"
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate required fields
    required_fields = ['client_id', 'url', 'user_agent', 'ip']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    client_id = data['client_id']
    url = data['url']
    user_agent = data['user_agent']
    ip = data['ip']
    page_id = data.get('page_id')
    referrer = data.get('referrer')
    bot_name = data.get('bot_name')

    db = SessionLocal()
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({
                'error': 'Client not found',
                'message': f'No client found with ID: {client_id}'
            }), 404

        # Auto-detect bot if not provided
        bot_detected = False
        if not bot_name:
            bot_name = detect_bot_from_user_agent(user_agent)
            if bot_name:
                bot_detected = True
        else:
            bot_detected = True

        # Determine visitor type
        visitor_type = determine_visitor_type(user_agent, bot_name)

        # Try to find page_id by URL if not provided
        if not page_id:
            page = db.query(Page).filter(
                Page.client_id == client_id,
                Page.url == url
            ).first()

            if page:
                page_id = page.id

        # Hash IP address for privacy
        ip_hash = Visit.hash_ip(ip)

        # Create visit record
        visit = Visit(
            client_id=client_id,
            page_id=page_id,
            url=url,
            visitor_type=visitor_type,
            user_agent=user_agent,
            ip_hash=ip_hash,
            referrer=referrer,
            bot_name=bot_name
        )

        db.add(visit)
        db.commit()
        db.refresh(visit)

        return jsonify({
            'success': True,
            'visit_id': str(visit.id),
            'visitor_type': visitor_type,
            'bot_detected': bot_detected,
            'bot_name': bot_name
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to record visit',
            'message': str(e)
        }), 500
    finally:
        db.close()


@visits_bp.route('/client/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_client_visits(client_id: UUID):
    """
    Get visit statistics for a client.

    Query parameters:
        start_date: ISO 8601 date (optional)
        end_date: ISO 8601 date (optional)

    Returns:
        JSON response with visit statistics

    Example:
        GET /api/v1/visits/client/123e4567-e89b-12d3-a456-426614174000
        GET /api/v1/visits/client/123e4567-e89b-12d3-a456-426614174000?start_date=2025-01-01T00:00:00Z

        Response:
        {
            "total_visits": 150,
            "bot_visits": 100,
            "human_visits": 50,
            "unique_pages": 25,
            "bot_percentage": 66.67,
            "human_percentage": 33.33,
            "top_bots": [
                {"bot_name": "ChatGPT", "count": 45},
                {"bot_name": "ClaudeBot", "count": 30}
            ],
            "top_pages": [
                {"url": "https://...", "count": 35},
                {"url": "https://...", "count": 28}
            ]
        }
    """
    db = SessionLocal()
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({
                'error': 'Client not found',
                'message': f'No client found with ID: {client_id}'
            }), 404

        # Parse date filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use ISO 8601.'}), 400

        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use ISO 8601.'}), 400

        # Get visit stats
        stats = get_visit_stats(client_id, start_date, end_date)

        # Get top bots
        days = 30  # Default to 30 days for top lists
        if start_date:
            days = max((datetime.utcnow() - start_date).days, 1)

        stats['top_bots'] = get_top_bots(client_id, limit=10, days=days)
        stats['top_pages'] = get_top_pages(client_id, limit=10, days=days)

        return jsonify(stats), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to get visit statistics',
            'message': str(e)
        }), 500
    finally:
        db.close()


@visits_bp.route('/page/<uuid:page_id>', methods=['GET'])
@require_api_key
def get_page_visits(page_id: UUID):
    """
    Get visits for a specific page.

    Query parameters:
        limit: Maximum number of visits to return (default: 100, max: 1000)

    Returns:
        JSON response with page visit data

    Example:
        GET /api/v1/visits/page/456e7890-e89b-12d3-a456-426614174111
        GET /api/v1/visits/page/456e7890-e89b-12d3-a456-426614174111?limit=50

        Response:
        {
            "page_id": "456e7890-e89b-12d3-a456-426614174111",
            "url": "https://shop.myshopify.com/products/shirt",
            "total_visits": 45,
            "bot_visits": 30,
            "human_visits": 15,
            "visits": [
                {
                    "id": "...",
                    "visitor_type": "ai_bot",
                    "bot_name": "ChatGPT",
                    "visited_at": "2025-11-21T10:00:00Z",
                    ...
                }
            ]
        }
    """
    # Get limit parameter
    limit = request.args.get('limit', 100, type=int)
    limit = min(limit, 1000)  # Cap at 1000

    db = SessionLocal()
    try:
        # Verify page exists
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            return jsonify({
                'error': 'Page not found',
                'message': f'No page found with ID: {page_id}'
            }), 404

        # Get page visit stats
        stats = get_page_visit_stats(page_id, limit=limit)

        return jsonify(stats), 200

    except ValueError as e:
        return jsonify({
            'error': 'Page not found',
            'message': str(e)
        }), 404
    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to get page visits',
            'message': str(e)
        }), 500
    finally:
        db.close()


@visits_bp.route('/analytics/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_visit_analytics_dashboard(client_id: UUID):
    """
    Get comprehensive analytics dashboard data for a client.

    Query parameters:
        days: Number of days to analyze (default: 30, max: 365)

    Returns:
        JSON response with dashboard analytics

    Example:
        GET /api/v1/visits/analytics/123e4567-e89b-12d3-a456-426614174000
        GET /api/v1/visits/analytics/123e4567-e89b-12d3-a456-426614174000?days=7

        Response:
        {
            "summary": {
                "total_visits": 500,
                "bot_visits": 350,
                "human_visits": 150,
                "bot_percentage": 70.0,
                "human_percentage": 30.0
            },
            "time_series": [
                {
                    "date": "2025-11-15T00:00:00Z",
                    "bot_visits": 45,
                    "human_visits": 15,
                    "total_visits": 60
                },
                ...
            ],
            "bot_breakdown": [
                {"name": "ChatGPT", "value": 120},
                {"name": "ClaudeBot", "value": 85}
            ],
            "page_breakdown": [
                {"url": "https://...", "value": 75},
                {"url": "https://...", "value": 50}
            ],
            "top_bots": [...],
            "top_pages": [...],
            "period_days": 30
        }
    """
    db = SessionLocal()
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({
                'error': 'Client not found',
                'message': f'No client found with ID: {client_id}'
            }), 404

        # Get days parameter
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)  # Cap at 365 days

        # Get dashboard analytics
        analytics = get_dashboard_analytics(client_id, days=days)

        return jsonify(analytics), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to get analytics dashboard',
            'message': str(e)
        }), 500
    finally:
        db.close()
