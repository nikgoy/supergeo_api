"""
Shopify App Proxy endpoints.

Provides endpoints for serving content through Shopify's app proxy system.
App proxies allow you to serve dynamic content on the storefront using URLs
like: https://shop.myshopify.com/apps/your-app/llms.txt

Configuration in Shopify Partner Dashboard:
- Subpath: /apps/ai-cache (or your chosen path)
- Proxy URL: https://your-api.com/app-proxy

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from typing import Optional

from flask import Blueprint, request, Response

from app.models.base import SessionLocal
from app.models.client import Client
from app.services.llms_txt import llms_txt_service

app_proxy_bp = Blueprint('app_proxy', __name__, url_prefix='/app-proxy')


def extract_shop_domain() -> Optional[str]:
    """
    Extract shop domain from Shopify headers or query parameters.

    Shopify forwards the shop domain via:
    - X-Shopify-Shop-Domain header
    - shop query parameter

    Returns:
        Shop domain string (e.g., "shop.myshopify.com") or None
    """
    # Try header first (most reliable)
    shop_domain = request.headers.get('X-Shopify-Shop-Domain')

    if shop_domain:
        return shop_domain

    # Fallback to query parameter
    shop_domain = request.args.get('shop')

    if shop_domain:
        return shop_domain

    return None


def find_client_by_domain(domain: str) -> Optional[Client]:
    """
    Find client by shop domain.

    Args:
        domain: Shop domain (e.g., "shop.myshopify.com")

    Returns:
        Client object or None
    """
    db = SessionLocal()
    try:
        client = db.query(Client).filter(
            Client.domain == domain,
            Client.is_active == True
        ).first()

        return client
    finally:
        db.close()


@app_proxy_bp.route('/llms.txt', methods=['GET'])
def serve_llms_txt():
    """
    Serve llms.txt via Shopify app proxy.

    This endpoint is accessed through Shopify's app proxy system:
    - Store URL: https://shop.myshopify.com/apps/ai-cache/llms.txt
    - Proxied to: https://your-api.com/app-proxy/llms.txt

    Shopify forwards the shop domain via headers/query parameters,
    allowing us to identify which client's content to serve.

    Returns:
        text/plain response with llms.txt content

    Example:
        GET /app-proxy/llms.txt
        Headers:
            X-Shopify-Shop-Domain: test-shop.myshopify.com

        Response (text/plain):
        # Test Shop

        > AI-optimized content from test-shop.myshopify.com...

        ## Pages

        - Homepage: https://test-shop.myshopify.com/
          Welcome to our shop
        ...
    """
    # Extract shop domain
    shop_domain = extract_shop_domain()

    if not shop_domain:
        return Response(
            "Error: Unable to identify shop. Missing X-Shopify-Shop-Domain header or shop parameter.",
            status=400,
            mimetype='text/plain'
        )

    # Find client by domain
    client = find_client_by_domain(shop_domain)

    if not client:
        return Response(
            f"Error: Shop not found: {shop_domain}",
            status=404,
            mimetype='text/plain'
        )

    # Generate llms.txt using the service (with caching)
    try:
        result = llms_txt_service.generate_for_client(client.id)
        llms_txt_content = result['llms_txt']

        # Return as plain text with UTF-8 encoding
        response = Response(
            llms_txt_content,
            status=200,
            mimetype='text/plain; charset=utf-8'
        )

        # Add cache headers for better performance
        # Cache for 1 hour (3600 seconds)
        response.headers['Cache-Control'] = 'public, max-age=3600'

        # Add ETag based on content hash for conditional requests
        import hashlib
        etag = hashlib.md5(llms_txt_content.encode()).hexdigest()
        response.headers['ETag'] = f'"{etag}"'

        # Check if client sent If-None-Match (ETag)
        if_none_match = request.headers.get('If-None-Match')
        if if_none_match and if_none_match == f'"{etag}"':
            # Content hasn't changed, return 304 Not Modified
            return Response(status=304)

        return response

    except Exception as e:
        print(f"[AppProxy] Error generating llms.txt for {shop_domain}: {e}")
        return Response(
            f"Error: Failed to generate llms.txt",
            status=500,
            mimetype='text/plain'
        )


@app_proxy_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for app proxy.

    Returns:
        Simple OK response

    Example:
        GET /app-proxy/health

        Response:
        OK
    """
    return Response(
        "OK",
        status=200,
        mimetype='text/plain'
    )


@app_proxy_bp.route('/', methods=['GET'])
def app_proxy_info():
    """
    App proxy root endpoint with information.

    Returns:
        Information about available app proxy endpoints

    Example:
        GET /app-proxy/

        Response:
        AI Cache App Proxy

        Available endpoints:
        - /app-proxy/llms.txt - LLM-optimized site content
        - /app-proxy/health - Health check
    """
    info = """AI Cache App Proxy

Available endpoints:
- /app-proxy/llms.txt - LLM-optimized site content
- /app-proxy/health - Health check

To access via Shopify store:
https://your-shop.myshopify.com/apps/ai-cache/llms.txt
"""

    return Response(
        info,
        status=200,
        mimetype='text/plain'
    )
