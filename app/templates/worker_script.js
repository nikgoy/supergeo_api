/**
 * Cloudflare Worker for AI Bot Detection and Geo-Optimized Content Delivery
 *
 * This worker:
 * - Detects AI bots (ChatGPT, Perplexity, Claude, etc.)
 * - Routes bot traffic to KV-stored geo-optimized pages
 * - Routes human traffic to origin server
 * - Sends visit analytics to API
 * - Handles 404s gracefully
 */

// Configuration - These will be replaced during deployment
const CONFIG = {
  KV_NAMESPACE_ID: '{{KV_NAMESPACE_ID}}',
  API_ENDPOINT: '{{API_ENDPOINT}}',
  API_KEY: '{{API_KEY}}',
  ZONE_NAME: '{{ZONE_NAME}}',
  CLIENT_ID: '{{CLIENT_ID}}'
};

// AI Bot User Agent patterns
const AI_BOT_PATTERNS = [
  // OpenAI
  /ChatGPT-User/i,
  /GPTBot/i,
  /OpenAI/i,

  // Anthropic
  /Claude-Web/i,
  /Anthropic-AI/i,
  /claudebot/i,

  // Perplexity
  /PerplexityBot/i,
  /Perplexity/i,

  // Google AI
  /Google-Extended/i,
  /Gemini/i,
  /Bard/i,

  // Meta
  /Meta-ExternalAgent/i,
  /FacebookBot/i,

  // Common AI crawlers
  /AI2Bot/i,
  /anthropic-ai/i,
  /Bytespider/i,  // ByteDance AI
  /CCBot/i,       // Common Crawl (used by AI training)
  /Diffbot/i,
  /omgili/i,
  /YouBot/i,      // You.com

  // Generic patterns
  /AI-bot/i,
  /LLM/i,
  /language-model/i
];

/**
 * Check if request is from an AI bot
 */
function isAIBot(userAgent) {
  if (!userAgent) return false;

  return AI_BOT_PATTERNS.some(pattern => pattern.test(userAgent));
}

/**
 * Generate KV key from URL path
 */
function generateKVKey(url) {
  try {
    const urlObj = new URL(url);
    let path = urlObj.pathname;

    // Remove trailing slash
    if (path.endsWith('/') && path.length > 1) {
      path = path.slice(0, -1);
    }

    // Remove leading slash
    if (path.startsWith('/')) {
      path = path.slice(1);
    }

    // Handle root path
    if (path === '') {
      path = 'index';
    }

    // Replace slashes with underscores and lowercase
    const key = path.replace(/\//g, '_').toLowerCase();

    return key;
  } catch (e) {
    console.error('Error generating KV key:', e);
    return null;
  }
}

/**
 * Send analytics to API (async, don't wait for response)
 */
async function sendAnalytics(request, isBot, kvHit, responseStatus) {
  try {
    const url = new URL(request.url);

    const analyticsData = {
      client_id: CONFIG.CLIENT_ID,
      url: request.url,
      path: url.pathname,
      user_agent: request.headers.get('User-Agent') || '',
      referer: request.headers.get('Referer') || '',
      is_bot: isBot,
      kv_hit: kvHit,
      response_status: responseStatus,
      timestamp: new Date().toISOString(),
      cf_country: request.cf?.country || '',
      cf_city: request.cf?.city || '',
      cf_region: request.cf?.region || '',
      cf_asn: request.cf?.asn || '',
      cf_colo: request.cf?.colo || ''
    };

    // Send to API (fire and forget)
    fetch(`${CONFIG.API_ENDPOINT}/api/v1/analytics/visit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': CONFIG.API_KEY
      },
      body: JSON.stringify(analyticsData)
    }).catch(err => {
      console.error('Failed to send analytics:', err);
    });
  } catch (e) {
    console.error('Error sending analytics:', e);
  }
}

/**
 * Create a 404 response
 */
function create404Response() {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>404 - Page Not Found</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }
    .container {
      text-align: center;
      padding: 2rem;
    }
    h1 {
      font-size: 6rem;
      margin: 0;
      font-weight: 700;
    }
    p {
      font-size: 1.5rem;
      margin: 1rem 0;
    }
    a {
      color: white;
      text-decoration: none;
      border: 2px solid white;
      padding: 0.75rem 1.5rem;
      border-radius: 5px;
      display: inline-block;
      margin-top: 1rem;
      transition: all 0.3s;
    }
    a:hover {
      background: white;
      color: #667eea;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>404</h1>
    <p>Page Not Found</p>
    <p style="font-size: 1rem; opacity: 0.9;">The page you're looking for doesn't exist.</p>
    <a href="/">Go Home</a>
  </div>
</body>
</html>`;

  return new Response(html, {
    status: 404,
    headers: {
      'Content-Type': 'text/html;charset=UTF-8',
      'Cache-Control': 'public, max-age=300'
    }
  });
}

/**
 * Main worker handler
 */
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const userAgent = request.headers.get('User-Agent') || '';
  const isBot = isAIBot(userAgent);
  const url = new URL(request.url);

  console.log(`[Worker] ${isBot ? 'BOT' : 'HUMAN'} request: ${url.pathname}`);

  // If it's an AI bot, try to serve from KV
  if (isBot) {
    try {
      const kvKey = generateKVKey(request.url);

      if (kvKey) {
        console.log(`[Worker] Looking up KV key: ${kvKey}`);

        // Get from KV (assuming KV namespace is bound as 'GEO_PAGES')
        const kvValue = await GEO_PAGES.get(kvKey);

        if (kvValue) {
          console.log(`[Worker] KV HIT for key: ${kvKey}`);

          // Send analytics (async)
          sendAnalytics(request, true, true, 200);

          // Return geo-optimized content
          return new Response(kvValue, {
            status: 200,
            headers: {
              'Content-Type': 'text/html;charset=UTF-8',
              'Cache-Control': 'public, max-age=3600',
              'X-Served-By': 'cloudflare-worker-kv',
              'X-Bot-Detected': 'true',
              'X-KV-Key': kvKey
            }
          });
        } else {
          console.log(`[Worker] KV MISS for key: ${kvKey}`);

          // KV miss - serve 404 for bots
          sendAnalytics(request, true, false, 404);
          return create404Response();
        }
      } else {
        console.log(`[Worker] Failed to generate KV key`);
        sendAnalytics(request, true, false, 404);
        return create404Response();
      }
    } catch (e) {
      console.error('[Worker] Error serving from KV:', e);

      // On error, send analytics and serve 404
      sendAnalytics(request, true, false, 500);
      return create404Response();
    }
  }

  // Human traffic - proxy to origin
  console.log(`[Worker] Proxying human request to origin`);

  try {
    const response = await fetch(request);

    // Send analytics (async)
    sendAnalytics(request, false, false, response.status);

    // Add custom header to indicate it went through worker
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('X-Served-By', 'cloudflare-worker-origin');
    newResponse.headers.set('X-Bot-Detected', 'false');

    return newResponse;
  } catch (e) {
    console.error('[Worker] Error proxying to origin:', e);

    // On origin error, send analytics and serve 404
    sendAnalytics(request, false, false, 502);
    return create404Response();
  }
}
