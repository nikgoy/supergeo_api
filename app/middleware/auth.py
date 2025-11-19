"""
Authentication middleware.

Provides simple API key authentication via X-API-Key header.
For production, consider using more robust authentication (OAuth2, JWT, etc.).
"""
from functools import wraps
from typing import Callable, Optional, Tuple

from flask import request, jsonify

from app.config import settings


def require_api_key(f: Callable) -> Callable:
    """
    Decorator to require API key authentication.

    Checks for X-API-Key header and validates against MASTER_API_KEY.

    Usage:
        @app.route('/protected')
        @require_api_key
        def protected_route():
            return {'message': 'success'}

    Returns:
        Wrapped function that checks API key before executing

    Raises:
        401: If API key is missing or invalid
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return jsonify({
                'error': 'Missing API key',
                'message': 'X-API-Key header is required'
            }), 401

        if api_key != settings.master_api_key:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is invalid'
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def get_client_ip() -> str:
    """
    Get client IP address from request.

    Handles proxy headers (X-Forwarded-For, X-Real-IP).

    Returns:
        Client IP address as string
    """
    # Check for proxy headers
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For can contain multiple IPs, take the first one
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()

    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')

    # Fallback to remote_addr
    return request.remote_addr or 'unknown'


def detect_bot(user_agent: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if user agent is a known AI bot.

    Args:
        user_agent: User agent string

    Returns:
        Tuple of (is_bot, bot_name)
    """
    if not user_agent:
        return False, None

    user_agent_lower = user_agent.lower()

    # Known AI bots
    ai_bots = {
        'gptbot': 'GPTBot',
        'chatgpt': 'ChatGPT',
        'claudebot': 'ClaudeBot',
        'claude-web': 'Claude',
        'anthropic-ai': 'Anthropic',
        'google-extended': 'Google-Extended',
        'bingbot': 'BingBot',
        'bingpreview': 'BingPreview',
        'slurp': 'Yahoo',
        'duckduckbot': 'DuckDuckBot',
        'baiduspider': 'BaiduSpider',
        'yandexbot': 'YandexBot',
        'facebookexternalhit': 'FacebookBot',
        'twitterbot': 'TwitterBot',
        'linkedinbot': 'LinkedInBot',
        'slackbot': 'SlackBot',
        'discordbot': 'DiscordBot',
        'telegrambot': 'TelegramBot',
        'whatsapp': 'WhatsApp',
        'applebot': 'AppleBot',
        'amazonbot': 'AmazonBot',
        'petalbot': 'PetalBot',
    }

    for bot_signature, bot_name in ai_bots.items():
        if bot_signature in user_agent_lower:
            return True, bot_name

    return False, None
