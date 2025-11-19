"""
Sitemap API endpoints.

Provides endpoints for importing URLs from sitemaps.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from datetime import datetime
from uuid import UUID

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client, Page
from app.services.sitemap import sitemap_parser

sitemap_bp = Blueprint('sitemap', __name__, url_prefix='/api/v1/sitemap')


@sitemap_bp.route('/import', methods=['POST'])
@require_api_key
def import_sitemap():
    """
    Import URLs from a sitemap into the database.

    Accepts both direct sitemap URLs and domain/homepage URLs:
    - Direct sitemap: "https://example.com/sitemap.xml"
    - Domain/homepage: "https://example.com" (auto-discovers sitemap)

    Request body:
        {
            "client_id": "uuid",              // Required: Client UUID
            "sitemap_url": "https://...",     // Required: Sitemap URL or domain
            "recursive": true,                // Optional: Follow sitemap indices (default: true)
            "max_depth": 3,                   // Optional: Max recursion depth (default: 3)
            "create_pages": true,             // Optional: Create Page entries (default: true)
            "overwrite": false                // Optional: Overwrite existing pages (default: false)
        }

    Returns:
        JSON response with import summary

    Examples:
        # Using direct sitemap URL
        POST /api/v1/sitemap/import
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "client_id": "123e4567-e89b-12d3-a456-426614174000",
            "sitemap_url": "https://example.com/sitemap.xml",
            "recursive": true
        }

        # Using domain (auto-discovers sitemap)
        Body:
        {
            "client_id": "123e4567-e89b-12d3-a456-426614174000",
            "sitemap_url": "https://example.com",
            "recursive": true
        }

        Response:
        {
            "message": "Sitemap imported successfully",
            "summary": {
                "total_urls": 150,
                "created": 145,
                "skipped": 5,
                "errors": 0
            },
            "client": {
                "id": "...",
                "name": "Example Corp",
                "domain": "example.com"
            }
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate required fields
    if 'client_id' not in data:
        return jsonify({'error': 'client_id is required'}), 400

    if 'sitemap_url' not in data:
        return jsonify({'error': 'sitemap_url is required'}), 400

    client_id = data['client_id']
    sitemap_url = data['sitemap_url']
    recursive = data.get('recursive', True)
    max_depth = data.get('max_depth', 3)
    create_pages = data.get('create_pages', True)
    overwrite = data.get('overwrite', False)

    db = SessionLocal()

    try:
        # Validate client exists
        try:
            client_uuid = UUID(client_id)
        except ValueError:
            return jsonify({'error': 'Invalid client_id format'}), 400

        client = db.query(Client).filter(Client.id == client_uuid).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Parse sitemap
        sitemap_errors = []
        try:
            if recursive:
                parse_result = sitemap_parser.parse_sitemap_recursive_detailed(sitemap_url, max_depth=max_depth)
                urls = parse_result['urls']
                sitemap_errors = parse_result.get('errors', [])
            else:
                content = sitemap_parser.fetch_sitemap(sitemap_url)
                result = sitemap_parser.parse_sitemap(content)
                urls = result.get('urls', [])

        except Exception as e:
            return jsonify({
                'error': 'Failed to parse sitemap',
                'message': str(e)
            }), 400

        # Summary counters
        summary = {
            'total_urls': len(urls),
            'created': 0,
            'skipped': 0,
            'updated': 0,
            'errors': 0
        }

        # Create page entries
        if create_pages:
            for url_data in urls:
                url = url_data.get('loc')
                if not url:
                    summary['errors'] += 1
                    continue

                try:
                    # Check if page already exists
                    url_hash = Page.compute_url_hash(url)
                    existing_page = db.query(Page).filter(
                        Page.client_id == client.id,
                        Page.url == url
                    ).first()

                    if existing_page:
                        if overwrite:
                            # Update existing page
                            existing_page.url_hash = url_hash
                            existing_page.updated_at = datetime.utcnow()
                            summary['updated'] += 1
                        else:
                            # Skip existing
                            summary['skipped'] += 1
                            continue
                    else:
                        # Create new page
                        page = Page(
                            client_id=client.id,
                            url=url,
                            url_hash=url_hash,
                            last_scraped_at=None,  # Not scraped yet
                            version=1
                        )
                        db.add(page)
                        summary['created'] += 1

                except IntegrityError:
                    # Duplicate URL (race condition)
                    db.rollback()
                    summary['skipped'] += 1
                except Exception as e:
                    # Other errors
                    db.rollback()
                    summary['errors'] += 1
                    print(f"Error creating page for {url}: {e}")

        # Commit all changes
        db.commit()

        response = {
            'message': 'Sitemap imported successfully',
            'summary': summary,
            'client': {
                'id': str(client.id),
                'name': client.name,
                'domain': client.domain
            },
            'sitemap_url': sitemap_url
        }

        # Include sitemap parsing errors if any
        if sitemap_errors:
            response['sitemap_errors'] = sitemap_errors
            response['warning'] = f"{len(sitemap_errors)} sitemap(s) failed to parse during import"

        return jsonify(response), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to import sitemap',
            'message': str(e)
        }), 500
    finally:
        db.close()


@sitemap_bp.route('/parse', methods=['POST'])
@require_api_key
def parse_sitemap():
    """
    Parse a sitemap without creating database entries.

    Useful for previewing what URLs would be imported.

    Accepts both direct sitemap URLs and domain/homepage URLs:
    - Direct sitemap: "https://example.com/sitemap.xml"
    - Domain/homepage: "https://example.com" (auto-discovers sitemap)

    Request body:
        {
            "sitemap_url": "https://...",  // Required: Sitemap URL or domain
            "recursive": true,             // Optional: Follow sitemap indices
            "max_depth": 3                 // Optional: Max recursion depth
        }

    Returns:
        JSON response with parsed URLs

    Examples:
        # Using direct sitemap URL
        POST /api/v1/sitemap/parse
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "sitemap_url": "https://example.com/sitemap.xml"
        }

        # Using domain (auto-discovers sitemap)
        Body:
        {
            "sitemap_url": "https://example.com"
        }

        Response:
        {
            "sitemap_url": "https://example.com/sitemap.xml",
            "total_urls": 150,
            "urls": [
                {
                    "loc": "https://example.com/page1",
                    "lastmod": "2024-01-01",
                    "priority": "0.8"
                },
                ...
            ]
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    if 'sitemap_url' not in data:
        return jsonify({'error': 'sitemap_url is required'}), 400

    sitemap_url = data['sitemap_url']
    recursive = data.get('recursive', True)
    max_depth = data.get('max_depth', 3)

    try:
        # Parse sitemap
        if recursive:
            result = sitemap_parser.parse_sitemap_recursive_detailed(sitemap_url, max_depth=max_depth)
            urls = result['urls']

            response = {
                'sitemap_url': sitemap_url,
                'total_urls': result['total_urls'],
                'total_sitemaps': result['total_sitemaps'],
                'urls': urls[:100],  # Limit response to first 100 for performance
                'truncated': len(urls) > 100,
                'visited_sitemaps': result['visited_sitemaps']
            }

            # Include error information if any errors occurred
            if result['has_errors']:
                response['errors'] = result['errors']
                response['warning'] = f"{len(result['errors'])} sitemap(s) failed to parse"

            return jsonify(response), 200
        else:
            content = sitemap_parser.fetch_sitemap(sitemap_url)
            result = sitemap_parser.parse_sitemap(content)
            urls = result.get('urls', [])

            return jsonify({
                'sitemap_url': sitemap_url,
                'total_urls': len(urls),
                'urls': urls[:100],
                'truncated': len(urls) > 100
            }), 200

    except Exception as e:
        return jsonify({
            'error': 'Failed to parse sitemap',
            'message': str(e)
        }), 400


@sitemap_bp.route('/client/<uuid:client_id>/pages', methods=['GET'])
@require_api_key
def list_client_pages(client_id: UUID):
    """
    List all pages for a client.

    Args:
        client_id: Client UUID

    Query parameters:
        limit: Maximum number of pages to return (default: 100)
        offset: Number of pages to skip (default: 0)
        has_content: Filter by whether page has content (true/false)

    Returns:
        JSON response with pages

    Example:
        GET /api/v1/sitemap/client/{client_id}/pages?limit=50&offset=0
        Headers: X-API-Key: your-master-api-key

        Response:
        {
            "client_id": "...",
            "total_pages": 150,
            "pages": [
                {
                    "id": "...",
                    "url": "https://example.com/page1",
                    "has_raw_html": false,
                    "last_scraped_at": null,
                    ...
                }
            ],
            "limit": 50,
            "offset": 0
        }
    """
    db = SessionLocal()

    try:
        # Validate client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Get query parameters
        limit = min(int(request.args.get('limit', 100)), 1000)  # Max 1000
        offset = int(request.args.get('offset', 0))
        has_content = request.args.get('has_content')

        # Build query
        query = db.query(Page).filter(Page.client_id == client_id)

        # Filter by content
        if has_content == 'true':
            query = query.filter(Page.raw_html.isnot(None))
        elif has_content == 'false':
            query = query.filter(Page.raw_html.is_(None))

        # Get total count
        total = query.count()

        # Get paginated results
        pages = query.order_by(Page.created_at.desc()).offset(offset).limit(limit).all()

        return jsonify({
            'client_id': str(client_id),
            'client_name': client.name,
            'total_pages': total,
            'pages': [page.to_dict() for page in pages],
            'limit': limit,
            'offset': offset
        }), 200

    finally:
        db.close()
