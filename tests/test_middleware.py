"""
Tests for middleware functions.

Tests authentication and bot detection.
"""
import pytest
from unittest.mock import Mock, patch

from app.middleware.auth import require_api_key, get_client_ip, detect_bot


class TestRequireApiKey:
    """Test require_api_key decorator."""

    def test_endpoint_without_api_key(self, client):
        """Test that protected endpoint rejects requests without API key."""
        response = client.get('/api/v1/clients')

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Missing API key'

    def test_endpoint_with_invalid_api_key(self, client):
        """Test that protected endpoint rejects invalid API key."""
        response = client.get(
            '/api/v1/clients',
            headers={'X-API-Key': 'wrong-key'}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Invalid API key'

    def test_endpoint_with_valid_api_key(self, client, auth_headers):
        """Test that protected endpoint accepts valid API key."""
        response = client.get('/api/v1/clients', headers=auth_headers)

        # Should not return 401 (may return 200 or other status)
        assert response.status_code != 401


class TestGetClientIp:
    """Test get_client_ip function."""

    @patch('app.middleware.auth.request')
    def test_get_ip_from_x_forwarded_for(self, mock_request):
        """Test getting IP from X-Forwarded-For header."""
        mock_request.headers.get.side_effect = lambda h: {
            'X-Forwarded-For': '1.2.3.4, 5.6.7.8'
        }.get(h)

        ip = get_client_ip()

        assert ip == '1.2.3.4'  # First IP in chain

    @patch('app.middleware.auth.request')
    def test_get_ip_from_x_real_ip(self, mock_request):
        """Test getting IP from X-Real-IP header."""
        mock_request.headers.get.side_effect = lambda h: {
            'X-Real-IP': '9.10.11.12'
        }.get(h)

        ip = get_client_ip()

        assert ip == '9.10.11.12'

    @patch('app.middleware.auth.request')
    def test_get_ip_from_remote_addr(self, mock_request):
        """Test getting IP from remote_addr as fallback."""
        mock_request.headers.get.return_value = None
        mock_request.remote_addr = '13.14.15.16'

        ip = get_client_ip()

        assert ip == '13.14.15.16'

    @patch('app.middleware.auth.request')
    def test_get_ip_unknown_when_none(self, mock_request):
        """Test getting 'unknown' when no IP available."""
        mock_request.headers.get.return_value = None
        mock_request.remote_addr = None

        ip = get_client_ip()

        assert ip == 'unknown'

    @patch('app.middleware.auth.request')
    def test_x_forwarded_for_with_spaces(self, mock_request):
        """Test handling X-Forwarded-For with extra spaces."""
        mock_request.headers.get.side_effect = lambda h: {
            'X-Forwarded-For': '  1.2.3.4  ,  5.6.7.8  '
        }.get(h)

        ip = get_client_ip()

        assert ip == '1.2.3.4'  # Should be trimmed


class TestDetectBot:
    """Test detect_bot function."""

    def test_detect_gptbot(self):
        """Test detecting GPTBot."""
        user_agent = 'Mozilla/5.0 (compatible; GPTBot/1.0)'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        assert bot_name == 'GPTBot'

    def test_detect_claudebot(self):
        """Test detecting ClaudeBot."""
        user_agent = 'Mozilla/5.0 (compatible; ClaudeBot/1.0)'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        assert bot_name == 'ClaudeBot'

    def test_detect_google_extended(self):
        """Test detecting Google-Extended."""
        user_agent = 'Mozilla/5.0 (compatible; Google-Extended)'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        assert bot_name == 'Google-Extended'

    def test_detect_bingbot(self):
        """Test detecting BingBot."""
        user_agent = 'Mozilla/5.0 (compatible; bingbot/2.0)'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        assert bot_name == 'BingBot'

    def test_detect_chatgpt(self):
        """Test detecting ChatGPT user agent."""
        user_agent = 'Mozilla/5.0 ChatGPT-User'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        assert bot_name == 'ChatGPT'

    def test_detect_multiple_bot_signatures(self):
        """Test that first matching bot is detected."""
        user_agent = 'Mozilla/5.0 (compatible; GPTBot/1.0; ClaudeBot/1.0)'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        # Should match first bot in the list
        assert bot_name in ['GPTBot', 'ClaudeBot']

    def test_regular_browser_not_detected(self):
        """Test that regular browsers are not detected as bots."""
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is False
        assert bot_name is None

    def test_empty_user_agent(self):
        """Test handling empty user agent."""
        is_bot, bot_name = detect_bot('')

        assert is_bot is False
        assert bot_name is None

    def test_none_user_agent(self):
        """Test handling None user agent."""
        is_bot, bot_name = detect_bot(None)

        assert is_bot is False
        assert bot_name is None

    def test_case_insensitive_detection(self):
        """Test that bot detection is case-insensitive."""
        user_agent = 'Mozilla/5.0 (compatible; GPTBOT/1.0)'  # Uppercase
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        assert bot_name == 'GPTBot'

    def test_detect_social_bots(self):
        """Test detecting social media bots."""
        test_cases = [
            ('Twitterbot/1.0', True, 'TwitterBot'),
            ('LinkedInBot/1.0', True, 'LinkedInBot'),
            ('facebookexternalhit/1.1', True, 'FacebookBot'),
        ]

        for user_agent, expected_is_bot, expected_name in test_cases:
            is_bot, bot_name = detect_bot(user_agent)
            assert is_bot == expected_is_bot
            assert bot_name == expected_name

    def test_detect_applebot(self):
        """Test detecting AppleBot."""
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/600.2.5 (KHTML, like Gecko) Version/8.0.2 Safari/600.2.5 (Applebot/0.1)'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        assert bot_name == 'AppleBot'

    def test_detect_duckduckbot(self):
        """Test detecting DuckDuckBot."""
        user_agent = 'DuckDuckBot/1.0'
        is_bot, bot_name = detect_bot(user_agent)

        assert is_bot is True
        assert bot_name == 'DuckDuckBot'
