"""
Gemini API endpoints for markdown processing and HTML generation.

Endpoints:
- POST /api/v1/gemini/process-page/{page_id} - Process single page
- POST /api/v1/gemini/process-client/{client_id} - Batch process client pages
- GET /api/v1/gemini/status/{page_id} - Get processing status
"""
from uuid import UUID
from flask import Blueprint, jsonify, request

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client, Page
from app.services.gemini import GeminiService


gemini_bp = Blueprint('gemini', __name__, url_prefix='/api/v1/gemini')


@gemini_bp.route('/process-page/<uuid:page_id>', methods=['POST'])
@require_api_key
def process_page(page_id: UUID):
    """
    Process a single page with Gemini.

    Cleans raw_markdown and generates SEO-optimized geo_html.

    Path Parameters:
        page_id (UUID): Page ID to process

    Returns:
        200: Processing successful
        {
            "success": true,
            "page_id": "uuid",
            "url": "https://example.com/page",
            "llm_markdown_length": 1234,
            "geo_html_length": 5678,
            "processed_at": "2025-11-21T10:00:00"
        }

        400: Missing raw_markdown or validation error
        404: Page not found
        500: Processing error

    Example:
        POST /api/v1/gemini/process-page/123e4567-e89b-12d3-a456-426614174000
        Headers: X-API-Key: your-api-key
    """
    db = SessionLocal()
    try:
        # Get page and client
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            return jsonify({
                'error': f'Page {page_id} not found'
            }), 404

        # Validate page has raw markdown
        if not page.raw_markdown:
            return jsonify({
                'error': 'Page has no raw_markdown to process. Please scrape the page first.'
            }), 400

        # Get client for API key
        client = db.query(Client).filter(Client.id == page.client_id).first()
        if not client:
            return jsonify({
                'error': 'Client not found for this page'
            }), 404

        # Create service with client-specific API key
        try:
            gemini_service = GeminiService.from_client(client)
        except ValueError as e:
            return jsonify({
                'error': f'Gemini API key not configured: {str(e)}'
            }), 400

        # Process page
        result = gemini_service.process_page(db, page_id)

        return jsonify({
            'success': True,
            **result
        }), 200

    except ValueError as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({
            'error': f'Failed to process page: {str(e)}'
        }), 500
    finally:
        db.close()


@gemini_bp.route('/process-client/<uuid:client_id>', methods=['POST'])
@require_api_key
def process_client(client_id: UUID):
    """
    Batch process all pages for a client.

    Processes pages that have raw_markdown but not yet geo_html.

    Path Parameters:
        client_id (UUID): Client ID

    Request Body (optional):
        {
            "force": false,        # Reprocess already-processed pages
            "batch_size": 10       # Number of pages to process (default: 10)
        }

    Returns:
        200: Processing completed
        {
            "success": true,
            "client_id": "uuid",
            "processed": 8,
            "skipped": 2,
            "failed": 0,
            "errors": [],
            "total_pages": 10
        }

        404: Client not found
        400: Configuration error
        500: Processing error

    Example:
        POST /api/v1/gemini/process-client/123e4567-e89b-12d3-a456-426614174000
        Headers: X-API-Key: your-api-key
        Body: {"force": false, "batch_size": 20}
    """
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        force = data.get('force', False)
        batch_size = data.get('batch_size', 10)

        # Validate batch_size
        if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 100:
            return jsonify({
                'error': 'batch_size must be an integer between 1 and 100'
            }), 400

        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({
                'error': f'Client {client_id} not found'
            }), 404

        # Create service with client-specific API key
        try:
            gemini_service = GeminiService.from_client(client)
        except ValueError as e:
            return jsonify({
                'error': f'Gemini API key not configured: {str(e)}'
            }), 400

        # Process pages
        result = gemini_service.process_client_pages(
            db=db,
            client_id=client_id,
            force=force,
            batch_size=batch_size
        )

        return jsonify({
            'success': True,
            **result
        }), 200

    except ValueError as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({
            'error': f'Failed to process client pages: {str(e)}'
        }), 500
    finally:
        db.close()


@gemini_bp.route('/status/<uuid:page_id>', methods=['GET'])
@require_api_key
def get_status(page_id: UUID):
    """
    Get processing status for a page.

    Path Parameters:
        page_id (UUID): Page ID

    Returns:
        200: Status retrieved
        {
            "page_id": "uuid",
            "url": "https://example.com/page",
            "has_raw_markdown": true,
            "has_llm_markdown": true,
            "has_geo_html": true,
            "last_scraped_at": "2025-11-21T09:00:00",
            "last_processed_at": "2025-11-21T10:00:00",
            "llm_markdown_length": 1234,
            "geo_html_length": 5678,
            "content_hash": "abc123...",
            "processing_status": "complete"  # pending|processing|complete|failed
        }

        404: Page not found

    Example:
        GET /api/v1/gemini/status/123e4567-e89b-12d3-a456-426614174000
        Headers: X-API-Key: your-api-key
    """
    db = SessionLocal()
    try:
        # Get page
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            return jsonify({
                'error': f'Page {page_id} not found'
            }), 404

        # Determine processing status
        if not page.raw_markdown:
            status = "pending"  # No content to process yet
        elif page.geo_html:
            status = "complete"  # Fully processed
        elif page.llm_markdown:
            status = "processing"  # Partial processing
        else:
            status = "pending"  # Has raw markdown but not processed

        return jsonify({
            'page_id': str(page.id),
            'url': page.url,
            'has_raw_markdown': page.raw_markdown is not None,
            'has_llm_markdown': page.llm_markdown is not None,
            'has_geo_html': page.geo_html is not None,
            'last_scraped_at': page.last_scraped_at.isoformat() if page.last_scraped_at else None,
            'last_processed_at': page.last_processed_at.isoformat() if page.last_processed_at else None,
            'llm_markdown_length': len(page.llm_markdown) if page.llm_markdown else 0,
            'geo_html_length': len(page.geo_html) if page.geo_html else 0,
            'content_hash': page.content_hash,
            'processing_status': status
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Failed to get status: {str(e)}'
        }), 500
    finally:
        db.close()
