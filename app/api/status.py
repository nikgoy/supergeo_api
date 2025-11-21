"""
Pipeline Status API Endpoints

Provides endpoints for checking the overall status of the content pipeline
for a given client, including progress through scraping, processing, KV upload,
and worker deployment stages.
"""

from flask import Blueprint, jsonify
from uuid import UUID
from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client, PageAnalytics

status_bp = Blueprint('status', __name__, url_prefix='/api/v1/status')


@status_bp.route('/pipeline/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_pipeline_status(client_id: UUID):
    """
    Get overall pipeline status for a client.

    Returns the progress of each pipeline stage:
    - URLs imported (total pages)
    - Markdown scraped (raw_markdown populated)
    - HTML generated (geo_html populated)
    - KV uploaded (kv_key populated)
    - Worker deployed (worker deployment status)

    Args:
        client_id: UUID of the client

    Returns:
        JSON object with pipeline stage statuses and overall completion percentage

    Example response:
        {
            "client_id": "123e4567-e89b-12d3-a456-426614174000",
            "stages": {
                "urls_imported": {"total": 10, "status": "complete"},
                "markdown_scraped": {"complete": 10, "status": "complete"},
                "html_generated": {"complete": 10, "status": "complete"},
                "kv_uploaded": {"complete": 10, "status": "complete"},
                "worker_deployed": true
            },
            "completion_percentage": 100.0
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

        # Get analytics for the client (contains pre-calculated pipeline metrics)
        analytics = db.query(PageAnalytics).filter(
            PageAnalytics.client_id == client_id
        ).first()

        # Initialize default values if no analytics exist yet
        total_urls = analytics.total_urls if analytics else 0
        urls_with_raw_markdown = analytics.urls_with_raw_markdown if analytics else 0
        urls_with_geo_html = analytics.urls_with_geo_html if analytics else 0
        urls_with_kv_key = analytics.urls_with_kv_key if analytics else 0

        # Determine status for each stage
        def get_stage_status(complete: int, total: int) -> str:
            """Helper to determine stage status"""
            if total == 0:
                return "no_data"
            elif complete == 0:
                return "not_started"
            elif complete < total:
                return "in_progress"
            else:
                return "complete"

        # Build stages response
        stages = {
            "urls_imported": {
                "total": total_urls,
                "status": "complete" if total_urls > 0 else "no_data"
            },
            "markdown_scraped": {
                "complete": urls_with_raw_markdown,
                "total": total_urls,
                "status": get_stage_status(urls_with_raw_markdown, total_urls)
            },
            "html_generated": {
                "complete": urls_with_geo_html,
                "total": total_urls,
                "status": get_stage_status(urls_with_geo_html, total_urls)
            },
            "kv_uploaded": {
                "complete": urls_with_kv_key,
                "total": total_urls,
                "status": get_stage_status(urls_with_kv_key, total_urls)
            },
            "worker_deployed": client.worker_deployed_at is not None
        }

        # Calculate overall completion percentage
        # Each stage contributes 20% to the total (5 stages = 100%)
        completion_percentage = 0.0

        if total_urls > 0:
            # Stage 1: URLs imported (20%)
            completion_percentage += 20.0

            # Stage 2: Markdown scraped (20%)
            completion_percentage += (urls_with_raw_markdown / total_urls) * 20.0

            # Stage 3: HTML generated (20%)
            completion_percentage += (urls_with_geo_html / total_urls) * 20.0

            # Stage 4: KV uploaded (20%)
            completion_percentage += (urls_with_kv_key / total_urls) * 20.0

            # Stage 5: Worker deployed (20%)
            if client.worker_deployed_at is not None:
                completion_percentage += 20.0

        # Round to 2 decimal places
        completion_percentage = round(completion_percentage, 2)

        return jsonify({
            'client_id': str(client_id),
            'stages': stages,
            'completion_percentage': completion_percentage
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to get pipeline status',
            'message': str(e)
        }), 500
    finally:
        db.close()
