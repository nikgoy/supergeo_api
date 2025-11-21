"""
Shared test data and mock responses for all tests.

This module provides mock data for external API responses, test fixtures,
and common test scenarios.
"""

# =============================================================================
# Client Test Data
# =============================================================================

MOCK_CLIENT_DATA = {
    "name": "Test Shop",
    "domain": "test-shop.myshopify.com",
    "cloudflare_account_id": "cf_account_123456",
    "cloudflare_api_token": "cf_token_abc123_secret",
    "cloudflare_kv_namespace_id": "kv_ns_123456",
    "gemini_api_key": "gemini_key_xyz789_secret",
    "is_active": True
}

MOCK_CLIENT_DATA_MINIMAL = {
    "name": "Minimal Shop",
    "domain": "minimal-shop.myshopify.com",
}

# =============================================================================
# Sitemap Test Data
# =============================================================================

MOCK_SITEMAP_URLS = [
    "https://test-shop.myshopify.com/",
    "https://test-shop.myshopify.com/products/shirt",
    "https://test-shop.myshopify.com/products/pants",
    "https://test-shop.myshopify.com/products/shoes",
    "https://test-shop.myshopify.com/collections/summer",
    "https://test-shop.myshopify.com/collections/winter",
    "https://test-shop.myshopify.com/pages/about",
    "https://test-shop.myshopify.com/pages/contact",
    "https://test-shop.myshopify.com/blogs/news/post-1",
    "https://test-shop.myshopify.com/policies/shipping",
]

MOCK_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://test-shop.myshopify.com/</loc>
    <lastmod>2025-11-01</lastmod>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/products/shirt</loc>
    <lastmod>2025-11-10</lastmod>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/products/pants</loc>
    <lastmod>2025-11-10</lastmod>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/products/shoes</loc>
    <lastmod>2025-11-12</lastmod>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/collections/summer</loc>
    <lastmod>2025-11-05</lastmod>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/collections/winter</loc>
    <lastmod>2025-11-05</lastmod>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/pages/about</loc>
    <lastmod>2025-10-15</lastmod>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/pages/contact</loc>
    <lastmod>2025-10-15</lastmod>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/blogs/news/post-1</loc>
    <lastmod>2025-11-20</lastmod>
  </url>
  <url>
    <loc>https://test-shop.myshopify.com/policies/shipping</loc>
    <lastmod>2025-09-01</lastmod>
  </url>
</urlset>"""

# =============================================================================
# Apify Test Data
# =============================================================================

MOCK_APIFY_MARKDOWN = """# Premium Cotton T-Shirt

## Product Description

High-quality cotton t-shirt perfect for everyday wear. Made from 100% organic cotton.

## Features

- 100% organic cotton
- Pre-shrunk fabric
- Available in multiple colors
- Machine washable
- Durable construction

## Specifications

- Material: 100% Cotton
- Weight: 180 GSM
- Fit: Regular
- Country of Origin: USA

## Price

$29.99

## Availability

In Stock - Ships within 2 business days
"""

MOCK_APIFY_RESPONSE_SUCCESS = {
    "markdown": MOCK_APIFY_MARKDOWN,
    "text": "Premium Cotton T-Shirt Product Description...",
    "metadata": {
        "title": "Premium Cotton T-Shirt",
        "description": "High-quality cotton t-shirt perfect for everyday wear",
        "statusCode": 200
    }
}

MOCK_APIFY_RUN_ID = "apify_run_abc123xyz"

# =============================================================================
# Gemini AI Test Data
# =============================================================================

MOCK_GEMINI_LLM_MARKDOWN = """# Premium Cotton T-Shirt

High-quality organic cotton t-shirt perfect for everyday wear.

## Key Features

- 100% organic cotton material
- Pre-shrunk, machine washable
- Available in multiple colors
- Regular fit, 180 GSM weight
- Made in USA

## Pricing

$29.99 - In Stock, ships within 2 business days
"""

MOCK_GEMINI_GEO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Premium Cotton T-Shirt - Test Shop</title>
  <meta name="description" content="High-quality organic cotton t-shirt perfect for everyday wear. $29.99 - In Stock">
  <meta name="robots" content="index, follow">
</head>
<body>
  <article itemscope itemtype="http://schema.org/Product">
    <header>
      <h1 itemprop="name">Premium Cotton T-Shirt</h1>
    </header>

    <section itemprop="description">
      <p>High-quality organic cotton t-shirt perfect for everyday wear.</p>
    </section>

    <section>
      <h2>Key Features</h2>
      <ul>
        <li>100% organic cotton material</li>
        <li>Pre-shrunk, machine washable</li>
        <li>Available in multiple colors</li>
        <li>Regular fit, 180 GSM weight</li>
        <li>Made in USA</li>
      </ul>
    </section>

    <section itemprop="offers" itemscope itemtype="http://schema.org/Offer">
      <h2>Pricing</h2>
      <p>
        <span itemprop="price" content="29.99">$29.99</span>
        <meta itemprop="priceCurrency" content="USD">
        <link itemprop="availability" href="http://schema.org/InStock">
        <span itemprop="availability">In Stock</span> - Ships within 2 business days
      </p>
    </section>
  </article>
</body>
</html>"""

MOCK_GEMINI_API_RESPONSE = {
    "candidates": [{
        "content": {
            "parts": [{
                "text": MOCK_GEMINI_LLM_MARKDOWN
            }]
        }
    }]
}

# =============================================================================
# Cloudflare KV Test Data
# =============================================================================

MOCK_KV_KEY = "https/test-shop-myshopify-com/products/shirt"
MOCK_KV_NAMESPACE_ID = "kv_ns_123456"
MOCK_KV_ACCOUNT_ID = "cf_account_123456"

MOCK_CLOUDFLARE_KV_UPLOAD_RESPONSE = {
    "success": True,
    "errors": [],
    "messages": [],
    "result": None
}

MOCK_CLOUDFLARE_KV_LIST_RESPONSE = {
    "success": True,
    "result": [
        {"name": MOCK_KV_KEY, "expiration": None}
    ],
    "result_info": {
        "count": 1,
        "cursor": ""
    }
}

# =============================================================================
# Cloudflare Worker Test Data
# =============================================================================

MOCK_WORKER_NAME = "test-shop-ai-cache-worker"
MOCK_WORKER_SCRIPT = """
// AI Cache Worker for Test Shop
// Detects AI bots and routes to cached content in KV

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const userAgent = request.headers.get('user-agent') || ''

  // Detect AI bots
  const isAIBot = detectAIBot(userAgent)

  if (isAIBot) {
    // Serve from KV cache
    const kvKey = urlToKvKey(request.url)
    const cachedContent = await KV_NAMESPACE.get(kvKey)

    if (cachedContent) {
      // Track visit
      await trackVisit(request, 'ai_bot')

      return new Response(cachedContent, {
        headers: {
          'Content-Type': 'text/html',
          'X-Cache': 'HIT',
          'X-Served-By': 'AI-Cache-Worker'
        }
      })
    }
  }

  // Pass through to origin
  return fetch(request)
}

function detectAIBot(userAgent) {
  const botPatterns = [
    'ChatGPT-User',
    'GPTBot',
    'PerplexityBot',
    'Claude-Web',
    'ClaudeBot',
    'anthropic-ai',
    'Googlebot',
    'Bingbot'
  ]

  return botPatterns.some(pattern => userAgent.includes(pattern))
}

function urlToKvKey(url) {
  const urlObj = new URL(url)
  return urlObj.pathname.replace(/\//g, '-').slice(1) || 'index'
}

async function trackVisit(request, visitorType) {
  // Send analytics to API
  const visitData = {
    url: request.url,
    user_agent: request.headers.get('user-agent'),
    referrer: request.headers.get('referer'),
    visitor_type: visitorType
  }

  await fetch('https://api.example.com/api/v1/visits/record', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(visitData)
  })
}
"""

MOCK_CLOUDFLARE_WORKER_RESPONSE = {
    "success": True,
    "errors": [],
    "messages": [],
    "result": {
        "id": "worker_abc123",
        "created_on": "2025-11-21T10:00:00Z",
        "modified_on": "2025-11-21T10:00:00Z",
        "etag": "etag123"
    }
}

MOCK_CLOUDFLARE_WORKER_STATUS_RESPONSE = {
    "success": True,
    "result": {
        "id": "worker_abc123",
        "created_on": "2025-11-21T10:00:00Z",
        "modified_on": "2025-11-21T10:00:00Z"
    }
}

# =============================================================================
# AI Bot User Agents
# =============================================================================

AI_BOT_USER_AGENTS = {
    "ChatGPT": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36 GPTBot/1.0",
    "Perplexity": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; PerplexityBot/1.0; +https://perplexity.ai/bot",
    "Claude": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; Claude-Web/1.0; +https://anthropic.com",
    "ClaudeBot": "ClaudeBot/1.0 (+https://www.anthropic.com/claudebot)",
    "GoogleBot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "BingBot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
}

HUMAN_USER_AGENTS = {
    "Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
}

# =============================================================================
# AI Referrer URLs
# =============================================================================

AI_REFERRER_URLS = {
    "ChatGPT": "https://chat.openai.com/c/abc123def456",
    "Perplexity": "https://www.perplexity.ai/search/xyz789abc123",
    "Claude": "https://claude.ai/chat/def456ghi789",
    "Google": "https://www.google.com/search?q=best+cotton+tshirts",
    "Bing": "https://www.bing.com/search?q=organic+tshirts"
}

DIRECT_REFERRERS = [
    None,  # Direct traffic
    "",  # Empty referrer
    "https://test-shop.myshopify.com/",  # Same domain
]

# =============================================================================
# llms.txt Test Data
# =============================================================================

MOCK_LLMS_TXT = """# Test Shop

> High-quality organic cotton apparel and accessories

## Pages

- Homepage: https://test-shop.myshopify.com/
  Welcome to Test Shop - Your source for premium organic cotton clothing

- Premium Cotton T-Shirt: https://test-shop.myshopify.com/products/shirt
  High-quality organic cotton t-shirt perfect for everyday wear. $29.99 - In Stock

- Organic Cotton Pants: https://test-shop.myshopify.com/products/pants
  Comfortable organic cotton pants with regular fit. $49.99 - In Stock

- Summer Collection: https://test-shop.myshopify.com/collections/summer
  Browse our latest summer collection featuring lightweight organic cotton apparel

- About Us: https://test-shop.myshopify.com/pages/about
  Learn about Test Shop's commitment to sustainable organic cotton fashion

- Contact Us: https://test-shop.myshopify.com/pages/contact
  Get in touch with our customer service team
"""

# =============================================================================
# Shopify App Proxy Headers
# =============================================================================

MOCK_SHOPIFY_PROXY_HEADERS = {
    "X-Shopify-Shop-Domain": "test-shop.myshopify.com",
    "X-Shopify-Customer-Id": "12345",
    "X-Shopify-Customer-Email": "customer@example.com",
    "X-Shopify-Hmac-Sha256": "mock_hmac_signature"
}

# =============================================================================
# Pixel Tracking Test Data
# =============================================================================

MOCK_PIXEL_PAGE_VIEW = {
    "shop_domain": "test-shop.myshopify.com",
    "event_type": "page_view",
    "url": "https://test-shop.myshopify.com/products/shirt",
    "referrer": "https://chat.openai.com/c/abc123",
    "timestamp": "2025-11-21T10:00:00Z"
}

MOCK_PIXEL_CHECKOUT_COMPLETED = {
    "shop_domain": "test-shop.myshopify.com",
    "event_type": "checkout_completed",
    "url": "https://test-shop.myshopify.com/checkout/thank-you",
    "referrer": "https://www.perplexity.ai/search/xyz789",
    "order_id": "ORDER_12345",
    "order_value": 99.99,
    "timestamp": "2025-11-21T10:05:00Z"
}

# =============================================================================
# Visit Tracking Test Data
# =============================================================================

MOCK_VISIT_BOT = {
    "client_id": None,  # Will be set in test
    "page_id": None,  # Will be set in test
    "url": "https://test-shop.myshopify.com/products/shirt",
    "user_agent": AI_BOT_USER_AGENTS["ChatGPT"],
    "ip": "203.0.113.42",
    "referrer": AI_REFERRER_URLS["ChatGPT"],
    "bot_name": "ChatGPT"
}

MOCK_VISIT_HUMAN = {
    "client_id": None,  # Will be set in test
    "page_id": None,  # Will be set in test
    "url": "https://test-shop.myshopify.com/products/shirt",
    "user_agent": HUMAN_USER_AGENTS["Chrome"],
    "ip": "203.0.113.100",
    "referrer": "https://www.google.com/search?q=cotton+shirts",
    "bot_name": None
}

# =============================================================================
# Pipeline Status Test Data
# =============================================================================

MOCK_PIPELINE_STATUS_COMPLETE = {
    "stages": {
        "urls_imported": {
            "total": 10,
            "status": "complete"
        },
        "markdown_scraped": {
            "total": 10,
            "complete": 10,
            "failed": 0,
            "status": "complete"
        },
        "html_generated": {
            "total": 10,
            "complete": 10,
            "failed": 0,
            "status": "complete"
        },
        "kv_uploaded": {
            "total": 10,
            "complete": 10,
            "failed": 0,
            "status": "complete"
        },
        "worker_deployed": True
    },
    "completion_percentage": 100.0
}

MOCK_PIPELINE_STATUS_PARTIAL = {
    "stages": {
        "urls_imported": {
            "total": 10,
            "status": "complete"
        },
        "markdown_scraped": {
            "total": 10,
            "complete": 8,
            "failed": 2,
            "status": "in_progress"
        },
        "html_generated": {
            "total": 10,
            "complete": 5,
            "failed": 0,
            "status": "in_progress"
        },
        "kv_uploaded": {
            "total": 10,
            "complete": 0,
            "failed": 0,
            "status": "pending"
        },
        "worker_deployed": False
    },
    "completion_percentage": 50.0
}
