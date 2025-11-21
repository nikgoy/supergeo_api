"""
Cloudflare Workers KV API endpoints.

Provides endpoints for uploading, deleting, and managing geo_html content in Cloudflare KV.
Supports both single page and batch operations with progress tracking.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from datetime import datetime
from uuid import UUID

from flask import Blueprint, jsonify, request

from app.middleware.auth import require_api_key
from app.models.base import SessionLocal
from app.models.client import Client, Page
from app.services.cloudflare_kv import CloudflareKVService

cloudflare_kv_bp = Blueprint('cloudflare_kv', __name__, url_prefix='/api/v1/cloudflare/kv')


@cloudflare_kv_bp.route('/upload/<uuid:page_id>', methods=['POST'])
@require_api_key
def upload_single_page(page_id: UUID):
    """
    Upload a single page's geo_html to Cloudflare KV.

    Uploads Page.geo_html to the client's KV namespace and updates kv_key and kv_uploaded_at.
    The KV key is generated from the page URL using CloudflareKVService.generate_kv_key().

    Args:
        page_id: Page UUID

    Request body:
        {
            "force_reupload": false,        // Optional: Re-upload even if already uploaded (default: false)
            "use_hash_key": false,          // Optional: Use URL hash as key instead of path-based (default: false)
            "expiration_ttl": null          // Optional: Seconds until expiration (min 60)
        }

    Returns:
        JSON response with upload result and updated page data

    Example:
        POST /api/v1/cloudflare/kv/upload/{page_id}
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "force_reupload": false,
            "use_hash_key": false
        }

        Response:
        {
            "message": "Page uploaded to KV successfully",
            "upload_result": {
                "success": true,
                "key": "https/example.com/page1",
                "value_size": 12450
            },
            "page": {
                "id": "...",
                "url": "https://example.com/page1",
                "kv_key": "https/example.com/page1",
                "kv_uploaded_at": "2025-11-21T10:30:00",
                "has_geo_html": true,
                ...
            }
        }
    """
    data = request.get_json() or {}

    force_reupload = data.get('force_reupload', False)
    use_hash_key = data.get('use_hash_key', False)
    expiration_ttl = data.get('expiration_ttl', None)

    db = SessionLocal()

    try:
        # Get page
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            return jsonify({'error': 'Page not found'}), 404

        # Check if page has geo_html
        if not page.geo_html:
            return jsonify({
                'error': 'Page does not have geo_html content',
                'message': 'Process the page with Gemini first to generate geo_html'
            }), 400

        # Get client
        client = db.query(Client).filter(Client.id == page.client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Check if already uploaded
        if page.kv_key and page.kv_uploaded_at and not force_reupload:
            return jsonify({
                'message': 'Page already uploaded to KV. Use force_reupload=true to re-upload.',
                'page': page.to_dict(),
                'skipped': True
            }), 200

        # Create KV service
        kv_service = CloudflareKVService.from_client(client)
        if not kv_service:
            return jsonify({
                'error': 'Client missing Cloudflare KV credentials',
                'message': 'Please configure cloudflare_account_id, cloudflare_api_token, and cloudflare_kv_namespace_id'
            }), 400

        # Generate KV key
        if use_hash_key:
            kv_key = CloudflareKVService.generate_kv_key_from_hash(page.url)
        else:
            kv_key = CloudflareKVService.generate_kv_key(page.url)

        print(f"[API] Uploading page {page_id} to KV with key: {kv_key}")

        # Upload to KV
        upload_result = kv_service.upload_value(
            key=kv_key,
            value=page.geo_html,
            expiration_ttl=expiration_ttl
        )

        if upload_result['success']:
            # Update page
            page.kv_key = kv_key
            page.kv_uploaded_at = datetime.utcnow()
            db.commit()

            return jsonify({
                'message': 'Page uploaded to KV successfully',
                'upload_result': {
                    'success': True,
                    'key': kv_key,
                    'value_size': len(page.geo_html)
                },
                'page': page.to_dict()
            }), 200

        else:
            # Upload failed
            return jsonify({
                'message': 'Failed to upload page to KV',
                'upload_result': {
                    'success': False,
                    'key': kv_key,
                    'error': upload_result.get('error')
                },
                'page': page.to_dict()
            }), 500

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to upload page to KV',
            'message': str(e)
        }), 500
    finally:
        db.close()


@cloudflare_kv_bp.route('/upload-client/<uuid:client_id>', methods=['POST'])
@require_api_key
def upload_client_pages(client_id: UUID):
    """
    Upload all pages with geo_html for a client to Cloudflare KV.

    Batch uploads geo_html content to the client's KV namespace.
    Updates kv_key and kv_uploaded_at for each successfully uploaded page.

    Args:
        client_id: Client UUID

    Request body:
        {
            "only_missing": true,           // Optional: Only upload pages without kv_key (default: true)
            "max_pages": 100,               // Optional: Maximum pages to upload (default: 100)
            "force_reupload": false,        // Optional: Re-upload even if already uploaded (default: false)
            "use_hash_key": false,          // Optional: Use URL hash as key instead of path-based (default: false)
            "use_bulk_api": true            // Optional: Use bulk API for better performance (default: true)
        }

    Returns:
        JSON response with batch upload summary

    Example:
        POST /api/v1/cloudflare/kv/upload-client/{client_id}
        Headers:
            X-API-Key: your-master-api-key
            Content-Type: application/json

        Body:
        {
            "only_missing": true,
            "max_pages": 50,
            "use_bulk_api": true
        }

        Response:
        {
            "message": "Batch upload to KV completed",
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
                    "kv_key": "https/example.com/page1",
                    "value_size": 12450
                },
                ...
            ]
        }
    """
    data = request.get_json() or {}

    only_missing = data.get('only_missing', True)
    max_pages = min(int(data.get('max_pages', 100)), 1000)  # Cap at 1000
    force_reupload = data.get('force_reupload', False)
    use_hash_key = data.get('use_hash_key', False)
    use_bulk_api = data.get('use_bulk_api', True)

    db = SessionLocal()

    try:
        # Validate client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Create KV service
        kv_service = CloudflareKVService.from_client(client)
        if not kv_service:
            return jsonify({
                'error': 'Client missing Cloudflare KV credentials',
                'message': 'Please configure cloudflare_account_id, cloudflare_api_token, and cloudflare_kv_namespace_id'
            }), 400

        # Build query for pages to upload
        query = db.query(Page).filter(
            Page.client_id == client_id,
            Page.geo_html.isnot(None)  # Must have geo_html
        )

        # Filter by missing kv_key
        if only_missing and not force_reupload:
            query = query.filter(Page.kv_key.is_(None))

        # Get pages
        pages = query.order_by(Page.created_at.asc()).limit(max_pages).all()

        if not pages:
            return jsonify({
                'message': 'No pages to upload',
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

        print(f"[API] Starting batch upload of {len(pages)} pages to KV for client {client.name}")

        summary = {
            'total_pages': len(pages),
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

        results_detail = []

        # Use bulk API if requested and available
        if use_bulk_api and len(pages) > 1:
            # Prepare bulk upload payload
            key_value_pairs = []
            page_by_key = {}

            for page in pages:
                if use_hash_key:
                    kv_key = CloudflareKVService.generate_kv_key_from_hash(page.url)
                else:
                    kv_key = CloudflareKVService.generate_kv_key(page.url)

                key_value_pairs.append({
                    'key': kv_key,
                    'value': page.geo_html
                })
                page_by_key[kv_key] = page

            # Upload bulk
            print(f"[API] Using bulk API to upload {len(key_value_pairs)} pages")
            bulk_result = kv_service.upload_bulk(key_value_pairs)

            if bulk_result['success']:
                successful_count = bulk_result.get('successful_count', 0)
                unsuccessful_keys = bulk_result.get('unsuccessful_keys', [])

                # Update pages that succeeded
                for kv_key, page in page_by_key.items():
                    if kv_key not in unsuccessful_keys:
                        page.kv_key = kv_key
                        page.kv_uploaded_at = datetime.utcnow()
                        summary['successful'] += 1

                        results_detail.append({
                            'page_id': str(page.id),
                            'url': page.url,
                            'status': 'success',
                            'kv_key': kv_key,
                            'value_size': len(page.geo_html)
                        })
                    else:
                        summary['failed'] += 1
                        results_detail.append({
                            'page_id': str(page.id),
                            'url': page.url,
                            'status': 'failed',
                            'kv_key': kv_key,
                            'error': 'Bulk upload failed for this key'
                        })

                db.commit()

            else:
                # Bulk upload failed entirely
                summary['failed'] = len(pages)
                for page in pages:
                    if use_hash_key:
                        kv_key = CloudflareKVService.generate_kv_key_from_hash(page.url)
                    else:
                        kv_key = CloudflareKVService.generate_kv_key(page.url)

                    results_detail.append({
                        'page_id': str(page.id),
                        'url': page.url,
                        'status': 'failed',
                        'kv_key': kv_key,
                        'error': bulk_result.get('error', 'Bulk upload failed')
                    })

        else:
            # Upload individually
            print(f"[API] Using individual API calls to upload {len(pages)} pages")

            for page in pages:
                if use_hash_key:
                    kv_key = CloudflareKVService.generate_kv_key_from_hash(page.url)
                else:
                    kv_key = CloudflareKVService.generate_kv_key(page.url)

                upload_result = kv_service.upload_value(
                    key=kv_key,
                    value=page.geo_html
                )

                if upload_result['success']:
                    page.kv_key = kv_key
                    page.kv_uploaded_at = datetime.utcnow()
                    summary['successful'] += 1

                    results_detail.append({
                        'page_id': str(page.id),
                        'url': page.url,
                        'status': 'success',
                        'kv_key': kv_key,
                        'value_size': len(page.geo_html)
                    })
                else:
                    summary['failed'] += 1
                    results_detail.append({
                        'page_id': str(page.id),
                        'url': page.url,
                        'status': 'failed',
                        'kv_key': kv_key,
                        'error': upload_result.get('error')
                    })

            # Commit all changes
            db.commit()

        return jsonify({
            'message': 'Batch upload to KV completed',
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
            'error': 'Failed to upload client pages to KV',
            'message': str(e)
        }), 500
    finally:
        db.close()


@cloudflare_kv_bp.route('/delete/<uuid:page_id>', methods=['DELETE'])
@require_api_key
def delete_page_from_kv(page_id: UUID):
    """
    Delete a page's content from Cloudflare KV.

    Removes the key-value pair from KV and clears kv_key and kv_uploaded_at from the page.

    Args:
        page_id: Page UUID

    Returns:
        JSON response with deletion result

    Example:
        DELETE /api/v1/cloudflare/kv/delete/{page_id}
        Headers:
            X-API-Key: your-master-api-key

        Response:
        {
            "message": "Page deleted from KV successfully",
            "delete_result": {
                "success": true,
                "key": "https/example.com/page1"
            },
            "page": {
                "id": "...",
                "url": "https://example.com/page1",
                "kv_key": null,
                "kv_uploaded_at": null,
                ...
            }
        }
    """
    db = SessionLocal()

    try:
        # Get page
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            return jsonify({'error': 'Page not found'}), 404

        # Check if page has kv_key
        if not page.kv_key:
            return jsonify({
                'message': 'Page does not have a KV key',
                'page': page.to_dict(),
                'skipped': True
            }), 200

        # Get client
        client = db.query(Client).filter(Client.id == page.client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Create KV service
        kv_service = CloudflareKVService.from_client(client)
        if not kv_service:
            return jsonify({
                'error': 'Client missing Cloudflare KV credentials',
                'message': 'Please configure cloudflare_account_id, cloudflare_api_token, and cloudflare_kv_namespace_id'
            }), 400

        kv_key = page.kv_key
        print(f"[API] Deleting page {page_id} from KV with key: {kv_key}")

        # Delete from KV
        delete_result = kv_service.delete_value(kv_key)

        if delete_result['success']:
            # Clear KV fields
            page.kv_key = None
            page.kv_uploaded_at = None
            db.commit()

            return jsonify({
                'message': 'Page deleted from KV successfully',
                'delete_result': {
                    'success': True,
                    'key': kv_key
                },
                'page': page.to_dict()
            }), 200

        else:
            # Delete failed
            return jsonify({
                'message': 'Failed to delete page from KV',
                'delete_result': {
                    'success': False,
                    'key': kv_key,
                    'error': delete_result.get('error')
                },
                'page': page.to_dict()
            }), 500

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Failed to delete page from KV',
            'message': str(e)
        }), 500
    finally:
        db.close()


@cloudflare_kv_bp.route('/status/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_kv_namespace_status(client_id: UUID):
    """
    Get Cloudflare KV namespace status for a client.

    Returns information about the client's KV namespace, including sample key count
    and statistics about uploaded pages.

    Args:
        client_id: Client UUID

    Returns:
        JSON response with namespace status

    Example:
        GET /api/v1/cloudflare/kv/status/{client_id}
        Headers:
            X-API-Key: your-master-api-key

        Response:
        {
            "client": {
                "id": "...",
                "name": "Example Corp",
                "domain": "example.com",
                "has_kv_credentials": true
            },
            "database_stats": {
                "total_pages": 100,
                "pages_with_geo_html": 80,
                "pages_uploaded_to_kv": 75,
                "upload_completion_rate": 93.75
            },
            "kv_namespace": {
                "success": true,
                "namespace_id": "abc123...",
                "sample_key_count": 75,
                "has_keys": true
            }
        }
    """
    db = SessionLocal()

    try:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Database statistics
        total_pages = db.query(Page).filter(Page.client_id == client_id).count()
        pages_with_geo_html = db.query(Page).filter(
            Page.client_id == client_id,
            Page.geo_html.isnot(None)
        ).count()
        pages_uploaded_to_kv = db.query(Page).filter(
            Page.client_id == client_id,
            Page.kv_key.isnot(None)
        ).count()

        # Calculate completion rate
        if pages_with_geo_html > 0:
            upload_completion_rate = (pages_uploaded_to_kv / pages_with_geo_html) * 100
        else:
            upload_completion_rate = 0.0

        database_stats = {
            'total_pages': total_pages,
            'pages_with_geo_html': pages_with_geo_html,
            'pages_uploaded_to_kv': pages_uploaded_to_kv,
            'upload_completion_rate': round(upload_completion_rate, 2)
        }

        # Try to get KV namespace status
        kv_namespace = None
        has_kv_credentials = all([
            client.cloudflare_account_id,
            client.cloudflare_api_token,
            client.cloudflare_kv_namespace_id
        ])

        if has_kv_credentials:
            kv_service = CloudflareKVService.from_client(client)
            kv_namespace = kv_service.get_namespace_status()

        return jsonify({
            'client': {
                'id': str(client.id),
                'name': client.name,
                'domain': client.domain,
                'has_kv_credentials': has_kv_credentials,
                'cloudflare_account_id': client.cloudflare_account_id,
                'cloudflare_kv_namespace_id': client.cloudflare_kv_namespace_id
            },
            'database_stats': database_stats,
            'kv_namespace': kv_namespace
        }), 200

    finally:
        db.close()
