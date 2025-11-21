"""
Pixel Tracking API endpoints.

Provides endpoints for tracking pixel events from Shopify stores and
analyzing conversion attribution from AI sources.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from uuid import UUID
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client, Page, Visit, Conversion
from app.services.referrer_analytics import (
    detect_ai_source_from_referrer,
    extract_referrer_domain,
    get_referrer_analytics_dashboard
)

pixel_bp = Blueprint('pixel', __name__, url_prefix='/api/v1/pixel')


@pixel_bp.route('/track', methods=['POST'])
@require_api_key
def track_pixel_event():
    """
    Track pixel event from Shopify store.

    Handles page_view and checkout_completed events. Creates Visit records
    for page views and Conversion records for checkouts.

    Request body:
        {
            "shop_domain": "shop.myshopify.com",  // Required: Shop domain
            "event_type": "page_view",            // Required: Event type
            "url": "https://...",                 // Required: Page URL
            "referrer": "https://...",            // Optional: Referrer URL
            "timestamp": "2025-11-21T10:00:00Z",  // Optional: Event timestamp
            "order_id": "ORDER_123",              // Required for checkout_completed
            "order_value": 99.99                  // Required for checkout_completed
        }

    Returns:
        JSON response with tracking result

    Example (Page View):
        POST /api/v1/pixel/track
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "shop_domain": "test-shop.myshopify.com",
            "event_type": "page_view",
            "url": "https://test-shop.myshopify.com/products/shirt",
            "referrer": "https://chat.openai.com/c/abc123",
            "timestamp": "2025-11-21T10:00:00Z"
        }

        Response:
        {
            "success": true,
            "event_type": "page_view",
            "ai_source": "ChatGPT",
            "visit_id": "uuid"
        }

    Example (Checkout Completed):
        Body:
        {
            "shop_domain": "test-shop.myshopify.com",
            "event_type": "checkout_completed",
            "url": "https://test-shop.myshopify.com/checkout/thank-you",
            "referrer": "https://www.perplexity.ai/search/xyz789",
            "order_id": "ORDER_12345",
            "order_value": 149.99,
            "timestamp": "2025-11-21T10:05:00Z"
        }

        Response:
        {
            "success": true,
            "event_type": "checkout_completed",
            "ai_source": "Perplexity",
            "conversion_id": "uuid",
            "conversion_value": 149.99
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate required fields
    required_fields = ['shop_domain', 'event_type', 'url']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    shop_domain = data['shop_domain']
    event_type = data['event_type']
    url = data['url']
    referrer = data.get('referrer')
    timestamp_str = data.get('timestamp')

    # Parse timestamp
    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            timestamp = datetime.utcnow()
    else:
        timestamp = datetime.utcnow()

    db = SessionLocal()
    try:
        # Find client by domain
        client = db.query(Client).filter(
            Client.domain == shop_domain,
            Client.is_active == True
        ).first()

        if not client:
            return jsonify({
                'error': 'Client not found',
                'message': f'No active client found with domain: {shop_domain}'
            }), 404

        # Detect AI source from referrer
        ai_source = detect_ai_source_from_referrer(referrer)
        referrer_domain = extract_referrer_domain(referrer)

        # Try to find page by URL
        page = db.query(Page).filter(
            Page.client_id == client.id,
            Page.url == url
        ).first()

        page_id = page.id if page else None

        # Handle different event types
        if event_type == 'page_view':
            # Create Visit record
            visit = Visit(
                client_id=client.id,
                page_id=page_id,
                url=url,
                visitor_type='direct',  # Pixel events are from actual visitors
                referrer=referrer,
                bot_name=ai_source if ai_source else None,
                visited_at=timestamp
            )

            db.add(visit)
            db.commit()
            db.refresh(visit)

            return jsonify({
                'success': True,
                'event_type': 'page_view',
                'ai_source': ai_source,
                'visit_id': str(visit.id)
            }), 200

        elif event_type == 'checkout_completed':
            # Validate checkout fields
            if 'order_id' not in data:
                return jsonify({'error': 'order_id is required for checkout_completed'}), 400

            order_id = data['order_id']
            order_value = data.get('order_value')

            # Check for duplicate order_id
            existing = db.query(Conversion).filter(
                Conversion.order_id == order_id
            ).first()

            if existing:
                # Return success but indicate duplicate
                return jsonify({
                    'success': True,
                    'event_type': 'checkout_completed',
                    'conversion_id': str(existing.id),
                    'duplicate': True,
                    'message': 'Conversion already tracked'
                }), 200

            # Create Conversion record
            conversion = Conversion(
                client_id=client.id,
                page_id=page_id,
                referrer_domain=referrer_domain,
                referrer_full_url=referrer,
                landing_url=url,
                converted_at=timestamp,
                conversion_value=order_value,
                order_id=order_id,
                ai_source=ai_source,
                event_type='checkout_completed'
            )

            db.add(conversion)
            db.commit()
            db.refresh(conversion)

            return jsonify({
                'success': True,
                'event_type': 'checkout_completed',
                'ai_source': ai_source,
                'conversion_id': str(conversion.id),
                'conversion_value': order_value
            }), 200

        else:
            # Unsupported event type
            return jsonify({
                'error': 'Unsupported event type',
                'message': f'Event type "{event_type}" is not supported. Use "page_view" or "checkout_completed".'
            }), 400

    except IntegrityError as e:
        db.rollback()
        # Handle unique constraint violations
        return jsonify({
            'error': 'Duplicate conversion',
            'message': 'This order has already been tracked'
        }), 409
    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to track pixel event',
            'message': str(e)
        }), 500
    finally:
        db.close()


@pixel_bp.route('/analytics/referrers/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_referrer_analytics(client_id: UUID):
    """
    Get referrer analytics for a client.

    Returns comprehensive analytics about conversions from different AI sources,
    including revenue attribution and top converting pages.

    Query parameters:
        days: Number of days to analyze (default: 30, max: 365)

    Returns:
        JSON response with referrer analytics

    Example:
        GET /api/v1/pixel/analytics/referrers/123e4567-e89b-12d3-a456-426614174000
        GET /api/v1/pixel/analytics/referrers/123e4567-e89b-12d3-a456-426614174000?days=7

        Response:
        {
            "summary": {
                "total_conversions": 50,
                "total_revenue": 2500.00,
                "ai_conversions": 35,
                "ai_revenue": 1750.00,
                "ai_conversion_rate": 70.0,
                "ai_revenue_rate": 70.0
            },
            "by_ai_source": [
                {
                    "ai_source": "ChatGPT",
                    "conversion_count": 20,
                    "total_revenue": 1000.00,
                    "avg_order_value": 50.00
                },
                {
                    "ai_source": "Perplexity",
                    "conversion_count": 10,
                    "total_revenue": 500.00,
                    "avg_order_value": 50.00
                }
            ],
            "top_converting_pages": [
                {
                    "landing_url": "https://...",
                    "conversion_count": 15,
                    "total_revenue": 750.00
                }
            ],
            "time_series": [...],
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

        # Get analytics dashboard
        analytics = get_referrer_analytics_dashboard(client_id, days=days)

        return jsonify(analytics), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to get referrer analytics',
            'message': str(e)
        }), 500
    finally:
        db.close()
