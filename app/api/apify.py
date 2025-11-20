"""
Apify RAG Web Browser API endpoints.

Provides endpoints for scraping URLs using Apify's RAG Web Browser actor.
Supports both single URL and batch scraping with parallel processing.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from datetime import datetime
from uuid import UUID

from flask import Blueprint, jsonify, request

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client, Page
from app.services.apify_rag import apify_rag_service

apify_bp = Blueprint('apify', __name__, url_prefix='/api/v1/apify')


@apify_bp.route('/scrape-url', methods=['POST'])
@require_api_key
def scrape_single_url():
    """
    Scrape a single URL using Apify RAG Web Browser.

    Fetches raw markdown content and stores it in the Page.raw_markdown field.
    Automatically updates content_hash and last_scraped_at timestamp.

    Request body:
        {
            "page_id": "uuid",                  // Optional: Page UUID
            "url": "https://...",               // Optional: URL (if page_id not provided)
            "client_id": "uuid",                // Optional: Client UUID (required if using url)
            "force_rescrape": false,            // Optional: Re-scrape even if raw_markdown exists
            "create_if_missing": true           // Optional: Create page if doesn't exist (default: true)
        }

    Returns:
        JSON response with scrape result and updated page data

    Examples:
        # Using page_id
        POST /api/v1/apify/scrape-url
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "page_id": "123e4567-e89b-12d3-a456-426614174000",
            "force_rescrape": false
        }

        # Using url + client_id
        Body:
        {
            "url": "https://example.com/page1",
            "client_id": "123e4567-e89b-12d3-a456-426614174000",
            "create_if_missing": true
        }

        Response:
        {
            "message": "URL scraped successfully",
            "scrape_result": {
                "status": "success",
                "run_id": "apify_run_123",
                "markdown_length": 12450,
                "url": "https://example.com/page1"
            },
            "page": {
                "id": "...",
                "url": "https://example.com/page1",
                "has_raw_markdown": true,
                "last_scraped_at": "2025-11-20T10:30:00",
                "apify_run_id": "apify_run_123",
                "scrape_attempts": 1,
                ...
            }
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    page_id = data.get('page_id')
    url = data.get('url')
    client_id = data.get('client_id')
    force_rescrape = data.get('force_rescrape', False)
    create_if_missing = data.get('create_if_missing', True)

    # Validate input
    if not page_id and not url:
        return jsonify({'error': 'Either page_id or url is required'}), 400

    if url and not client_id and not page_id:
        return jsonify({'error': 'client_id is required when using url'}), 400

    db = SessionLocal()

    try:
        # Get or create page
        page = None

        if page_id:
            # Find by page_id
            try:
                page_uuid = UUID(page_id)
            except ValueError:
                return jsonify({'error': 'Invalid page_id format'}), 400

            page = db.query(Page).filter(Page.id == page_uuid).first()
            if not page:
                return jsonify({'error': 'Page not found'}), 404

        elif url:
            # Find by url + client_id
            try:
                client_uuid = UUID(client_id)
            except ValueError:
                return jsonify({'error': 'Invalid client_id format'}), 400

            # Validate client exists
            client = db.query(Client).filter(Client.id == client_uuid).first()
            if not client:
                return jsonify({'error': 'Client not found'}), 404

            # Check if page exists
            page = db.query(Page).filter(
                Page.client_id == client_uuid,
                Page.url == url
            ).first()

            if not page and create_if_missing:
                # Create new page
                page = Page(
                    client_id=client_uuid,
                    url=url,
                    url_hash=Page.compute_url_hash(url),
                    version=1
                )
                db.add(page)
                db.flush()  # Get page ID
            elif not page:
                return jsonify({'error': 'Page not found and create_if_missing is false'}), 404

        # Check if already scraped
        if page.raw_markdown and not force_rescrape:
            return jsonify({
                'message': 'Page already has raw_markdown content. Use force_rescrape=true to re-scrape.',
                'page': page.to_dict(),
                'skipped': True
            }), 200

        # Scrape URL
        url_to_scrape = page.url
        print(f"[API] Scraping URL: {url_to_scrape}")

        scrape_result = apify_rag_service.scrape_url(url_to_scrape)

        # Update page based on result
        page.scrape_attempts = (page.scrape_attempts or 0) + 1
        page.apify_run_id = scrape_result.get('run_id')

        if scrape_result['status'] == 'success':
            # Store markdown
            markdown = scrape_result.get('markdown', '')
            page.raw_markdown = markdown
            page.update_content_hash()
            page.last_scraped_at = datetime.utcnow()
            page.scrape_error = None  # Clear any previous errors

            db.commit()

            return jsonify({
                'message': 'URL scraped successfully',
                'scrape_result': {
                    'status': scrape_result['status'],
                    'run_id': scrape_result.get('run_id'),
                    'markdown_length': len(markdown),
                    'url': url_to_scrape,
                    'metadata': scrape_result.get('metadata', {})
                },
                'page': page.to_dict()
            }), 200

        else:
            # Store error
            error_message = scrape_result.get('error', 'Unknown error')
            page.scrape_error = error_message

            db.commit()

            return jsonify({
                'message': 'URL scraping failed',
                'scrape_result': {
                    'status': scrape_result['status'],
                    'run_id': scrape_result.get('run_id'),
                    'error': error_message,
                    'url': url_to_scrape
                },
                'page': page.to_dict()
            }), 500

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to scrape URL',
            'message': str(e)
        }), 500
    finally:
        db.close()


@apify_bp.route('/scrape-client/<uuid:client_id>', methods=['POST'])
@require_api_key
def scrape_client_urls(client_id: UUID):
    """
    Scrape all URLs for a client using parallel processing.

    Fetches raw markdown content for multiple pages concurrently.
    Updates Page.raw_markdown, content_hash, and last_scraped_at for each page.

    Args:
        client_id: Client UUID

    Request body:
        {
            "only_missing": true,           // Optional: Only scrape pages without raw_markdown (default: true)
            "max_pages": 100,               // Optional: Maximum pages to scrape (default: 100)
            "force_rescrape": false,        // Optional: Re-scrape even if raw_markdown exists (default: false)
            "max_workers": 5                // Optional: Parallel workers (default: from settings)
        }

    Returns:
        JSON response with batch scrape summary

    Example:
        POST /api/v1/apify/scrape-client/{client_id}
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "only_missing": true,
            "max_pages": 50
        }

        Response:
        {
            "message": "Batch scraping completed",
            "client": {
                "id": "...",
                "name": "Example Corp",
                "domain": "example.com"
            },
            "summary": {
                "total_pages": 50,
                "successful": 48,
                "failed": 2,
                "skipped": 0
            },
            "results": [
                {
                    "page_id": "...",
                    "url": "https://example.com/page1",
                    "status": "success",
                    "markdown_length": 12450,
                    "run_id": "apify_run_123"
                },
                ...
            ]
        }
    """
    data = request.get_json() or {}

    only_missing = data.get('only_missing', True)
    max_pages = min(int(data.get('max_pages', 100)), 1000)  # Cap at 1000
    force_rescrape = data.get('force_rescrape', False)
    max_workers = data.get('max_workers', None)

    db = SessionLocal()

    try:
        # Validate client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Build query for pages to scrape
        query = db.query(Page).filter(Page.client_id == client_id)

        # Filter by missing content
        if only_missing and not force_rescrape:
            query = query.filter(Page.raw_markdown.is_(None))

        # Get pages
        pages = query.order_by(Page.created_at.asc()).limit(max_pages).all()

        if not pages:
            return jsonify({
                'message': 'No pages to scrape',
                'client': {
                    'id': str(client.id),
                    'name': client.name,
                    'domain': client.domain
                },
                'summary': {
                    'total_pages': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0
                }
            }), 200

        # Extract URLs
        urls = [page.url for page in pages]
        page_by_url = {page.url: page for page in pages}

        print(f"[API] Starting batch scrape of {len(urls)} URLs for client {client.name}")

        # Scrape in parallel
        scrape_results = apify_rag_service.scrape_urls_parallel(urls, max_workers=max_workers)

        # Process results
        summary = {
            'total_pages': len(scrape_results),
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

        results_detail = []

        for scrape_result in scrape_results:
            url = scrape_result['url']
            page = page_by_url.get(url)

            if not page:
                continue

            # Update page
            page.scrape_attempts = (page.scrape_attempts or 0) + 1
            page.apify_run_id = scrape_result.get('run_id')

            if scrape_result['status'] == 'success':
                markdown = scrape_result.get('markdown', '')
                page.raw_markdown = markdown
                page.update_content_hash()
                page.last_scraped_at = datetime.utcnow()
                page.scrape_error = None
                summary['successful'] += 1

                results_detail.append({
                    'page_id': str(page.id),
                    'url': url,
                    'status': 'success',
                    'markdown_length': len(markdown),
                    'run_id': scrape_result.get('run_id')
                })

            else:
                error_message = scrape_result.get('error', 'Unknown error')
                page.scrape_error = error_message
                summary['failed'] += 1

                results_detail.append({
                    'page_id': str(page.id),
                    'url': url,
                    'status': 'failed',
                    'error': error_message,
                    'run_id': scrape_result.get('run_id')
                })

        # Commit all changes
        db.commit()

        return jsonify({
            'message': 'Batch scraping completed',
            'client': {
                'id': str(client.id),
                'name': client.name,
                'domain': client.domain
            },
            'summary': summary,
            'results': results_detail
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to scrape client URLs',
            'message': str(e)
        }), 500
    finally:
        db.close()


@apify_bp.route('/status/<uuid:page_id>', methods=['GET'])
@require_api_key
def get_scrape_status(page_id: UUID):
    """
    Get scraping status for a specific page.

    Args:
        page_id: Page UUID

    Returns:
        JSON response with page scraping status

    Example:
        GET /api/v1/apify/status/{page_id}
        Headers: X-API-Key: your-master-api-key

        Response:
        {
            "page_id": "...",
            "url": "https://example.com/page1",
            "has_raw_markdown": true,
            "last_scraped_at": "2025-11-20T10:30:00",
            "apify_run_id": "apify_run_123",
            "scrape_attempts": 1,
            "scrape_error": null,
            "content_hash": "abc123...",
            "apify_run_status": {
                "run_id": "apify_run_123",
                "status": "SUCCEEDED",
                "finished_at": "2025-11-20T10:30:00"
            }
        }
    """
    db = SessionLocal()

    try:
        # Get page
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            return jsonify({'error': 'Page not found'}), 404

        response = {
            'page_id': str(page.id),
            'url': page.url,
            'has_raw_markdown': page.raw_markdown is not None,
            'last_scraped_at': page.last_scraped_at.isoformat() if page.last_scraped_at else None,
            'apify_run_id': page.apify_run_id,
            'scrape_attempts': page.scrape_attempts or 0,
            'scrape_error': page.scrape_error,
            'content_hash': page.content_hash
        }

        # Optionally fetch Apify run status
        if page.apify_run_id:
            try:
                run_status = apify_rag_service.get_run_status(page.apify_run_id)
                response['apify_run_status'] = run_status
            except Exception as e:
                response['apify_run_status_error'] = str(e)

        return jsonify(response), 200

    finally:
        db.close()
