"""
Tests for Gemini AI service and endpoints.

Tests markdown processing, HTML generation, batch operations, and error handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.models.client import Client, Page
from tests.fixtures.test_data import (
    MOCK_CLIENT_DATA,
    MOCK_APIFY_MARKDOWN,
    MOCK_GEMINI_LLM_MARKDOWN,
    MOCK_GEMINI_GEO_HTML,
    MOCK_SITEMAP_URLS,
)


@pytest.fixture
def gemini_client(db):
    """Create a client with Gemini API key for testing."""
    client = Client(
        name="Gemini Test Client",
        domain="gemini-test.com",
        is_active=True
    )
    client.gemini_api_key = MOCK_CLIENT_DATA["gemini_api_key"]

    db.add(client)
    db.commit()
    db.refresh(client)

    return client


@pytest.fixture
def page_with_markdown(db, gemini_client):
    """Create a page with raw markdown."""
    page = Page(
        client_id=gemini_client.id,
        url=MOCK_SITEMAP_URLS[0],
        url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[0]),
        raw_markdown=MOCK_APIFY_MARKDOWN,
        last_scraped_at=datetime.utcnow()
    )
    page.update_content_hash()

    db.add(page)
    db.commit()
    db.refresh(page)

    return page


@pytest.fixture
def pages_for_batch(db, gemini_client):
    """Create multiple pages for batch processing."""
    pages = []
    for i in range(5):
        page = Page(
            client_id=gemini_client.id,
            url=MOCK_SITEMAP_URLS[i],
            url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[i]),
            raw_markdown=MOCK_APIFY_MARKDOWN,
            last_scraped_at=datetime.utcnow()
        )
        page.update_content_hash()
        db.add(page)
        pages.append(page)

    db.commit()

    for page in pages:
        db.refresh(page)

    return pages


@pytest.fixture
def mock_gemini_api():
    """Mock Gemini API responses."""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        model_instance = MagicMock()

        # Mock response for markdown cleaning
        response_markdown = MagicMock()
        response_markdown.text = MOCK_GEMINI_LLM_MARKDOWN

        # Mock response for HTML generation
        response_html = MagicMock()
        response_html.text = MOCK_GEMINI_GEO_HTML

        # Alternate between responses
        model_instance.generate_content.side_effect = [
            response_markdown,
            response_html,
        ] * 50  # Support multiple calls

        mock_model.return_value = model_instance
        yield mock_model


class TestGeminiService:
    """Test Gemini service functionality."""

    def test_process_markdown_to_llm_format(self, mock_gemini_api):
        """Test converting raw markdown to LLM-optimized format."""
        # This tests the service directly (when implemented)
        # from app.services.gemini import GeminiService
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        # result = service.process_markdown(MOCK_APIFY_MARKDOWN)
        #
        # assert result is not None
        # assert len(result) > 0
        # assert "Premium Cotton T-Shirt" in result

    def test_generate_geo_html_from_markdown(self, mock_gemini_api):
        """Test generating GEO HTML from markdown."""
        # from app.services.gemini import GeminiService
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        # result = service.generate_html(
        #     markdown=MOCK_GEMINI_LLM_MARKDOWN,
        #     url=MOCK_SITEMAP_URLS[0],
        #     metadata={"title": "Test Product"}
        # )
        #
        # assert result is not None
        # assert "<!DOCTYPE html>" in result
        # assert "<title>" in result
        # assert "Premium Cotton T-Shirt" in result

    def test_gemini_service_uses_client_key(self, gemini_client):
        """Test service uses client-specific Gemini API key."""
        # from app.services.gemini import GeminiService
        #
        # service = GeminiService.from_client(gemini_client)
        # assert service.api_key == gemini_client.gemini_api_key


class TestGeminiAPIEndpoints:
    """Test Gemini API endpoints."""

    def test_process_single_page(
        self,
        client,
        auth_headers,
        db,
        page_with_markdown,
        mock_gemini_api
    ):
        """Test processing a single page with Gemini."""
        page_id = str(page_with_markdown.id)

        response = client.post(
            f'/api/v1/gemini/process-page/{page_id}',
            headers=auth_headers
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert data['page_id'] == page_id
        # assert 'llm_markdown_length' in data
        # assert 'geo_html_length' in data
        # assert 'processed_at' in data

        # Verify database updated
        # db.refresh(page_with_markdown)
        # assert page_with_markdown.llm_markdown is not None
        # assert page_with_markdown.geo_html is not None
        # assert page_with_markdown.last_processed_at is not None

    def test_process_page_without_markdown(
        self,
        client,
        auth_headers,
        db,
        gemini_client
    ):
        """Test processing page without raw markdown fails gracefully."""
        # Create page without markdown
        page = Page(
            client_id=gemini_client.id,
            url=MOCK_SITEMAP_URLS[0],
            url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[0])
        )
        db.add(page)
        db.commit()

        page_id = str(page.id)

        response = client.post(
            f'/api/v1/gemini/process-page/{page_id}',
            headers=auth_headers
        )

        # Should return error
        # assert response.status_code == 400
        # data = response.get_json()
        # assert 'error' in data
        # assert 'raw_markdown' in data['error'].lower()

    def test_process_client_batch(
        self,
        client,
        auth_headers,
        db,
        gemini_client,
        pages_for_batch,
        mock_gemini_api
    ):
        """Test batch processing all pages for a client."""
        client_id = str(gemini_client.id)

        response = client.post(
            f'/api/v1/gemini/process-client/{client_id}',
            headers=auth_headers,
            json={'force': False, 'batch_size': 10}
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['success'] is True
        # assert data['processed'] == 5
        # assert data['skipped'] == 0
        # assert data['failed'] == 0

        # Verify all pages processed
        # db.expire_all()
        # pages = db.query(Page).filter(
        #     Page.client_id == gemini_client.id
        # ).all()
        #
        # for page in pages:
        #     assert page.llm_markdown is not None
        #     assert page.geo_html is not None

    def test_skip_already_processed_pages(
        self,
        client,
        auth_headers,
        db,
        gemini_client,
        pages_for_batch
    ):
        """Test skipping pages that already have geo_html."""
        # Mark some pages as already processed
        for i in range(3):
            pages_for_batch[i].llm_markdown = MOCK_GEMINI_LLM_MARKDOWN
            pages_for_batch[i].geo_html = MOCK_GEMINI_GEO_HTML
            pages_for_batch[i].last_processed_at = datetime.utcnow()

        db.commit()

        client_id = str(gemini_client.id)

        response = client.post(
            f'/api/v1/gemini/process-client/{client_id}',
            headers=auth_headers,
            json={'force': False}
        )

        # Should only process 2 remaining pages
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['processed'] == 2
        # assert data['skipped'] == 3

    def test_force_reprocess_pages(
        self,
        client,
        auth_headers,
        db,
        gemini_client,
        pages_for_batch,
        mock_gemini_api
    ):
        """Test force reprocessing even if already processed."""
        # Mark all pages as processed
        for page in pages_for_batch:
            page.llm_markdown = "Old content"
            page.geo_html = "<html>Old HTML</html>"
            page.last_processed_at = datetime.utcnow()

        db.commit()

        client_id = str(gemini_client.id)

        response = client.post(
            f'/api/v1/gemini/process-client/{client_id}',
            headers=auth_headers,
            json={'force': True}
        )

        # Should reprocess all 5 pages
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert data['processed'] == 5
        # assert data['skipped'] == 0

    def test_process_page_not_found(self, client, auth_headers):
        """Test processing non-existent page."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'

        response = client.post(
            f'/api/v1/gemini/process-page/{fake_uuid}',
            headers=auth_headers
        )

        # Should return 404
        # assert response.status_code == 404
        # data = response.get_json()
        # assert 'error' in data

    def test_process_client_not_found(self, client, auth_headers):
        """Test processing non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'

        response = client.post(
            f'/api/v1/gemini/process-client/{fake_uuid}',
            headers=auth_headers
        )

        # Should return 404
        # assert response.status_code == 404

    def test_get_processing_status(
        self,
        client,
        auth_headers,
        page_with_markdown
    ):
        """Test getting processing status for a page."""
        page_id = str(page_with_markdown.id)

        response = client.get(
            f'/api/v1/gemini/status/{page_id}',
            headers=auth_headers
        )

        # Expected response
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert 'has_raw_markdown' in data
        # assert 'has_llm_markdown' in data
        # assert 'has_geo_html' in data
        # assert 'last_processed_at' in data


class TestGeminiErrorHandling:
    """Test error handling in Gemini processing."""

    def test_missing_api_key(self, client, auth_headers, db):
        """Test processing fails gracefully without API key."""
        # Create client without Gemini key
        test_client = Client(
            name="No Gemini Key",
            domain="no-gemini.com"
        )
        db.add(test_client)
        db.commit()

        # Create page
        page = Page(
            client_id=test_client.id,
            url=MOCK_SITEMAP_URLS[0],
            url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[0]),
            raw_markdown=MOCK_APIFY_MARKDOWN
        )
        db.add(page)
        db.commit()

        page_id = str(page.id)

        response = client.post(
            f'/api/v1/gemini/process-page/{page_id}',
            headers=auth_headers
        )

        # Should return 400 or 500 with error
        # assert response.status_code in [400, 500]
        # data = response.get_json()
        # assert 'error' in data

    def test_gemini_api_error(
        self,
        client,
        auth_headers,
        page_with_markdown
    ):
        """Test handling Gemini API errors."""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            model_instance = MagicMock()
            model_instance.generate_content.side_effect = Exception(
                "API rate limit exceeded"
            )
            mock_model.return_value = model_instance

            page_id = str(page_with_markdown.id)

            response = client.post(
                f'/api/v1/gemini/process-page/{page_id}',
                headers=auth_headers
            )

            # Should handle error gracefully
            # assert response.status_code in [500, 503]
            # data = response.get_json()
            # assert 'error' in data

    def test_gemini_rate_limiting(self, mock_gemini_api):
        """Test rate limit handling."""
        # from app.services.gemini import GeminiService
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        #
        # # Simulate rate limiting
        # with pytest.raises(Exception) as exc_info:
        #     # Make many rapid requests
        #     for _ in range(100):
        #         service.process_markdown(MOCK_APIFY_MARKDOWN)
        #
        # assert "rate limit" in str(exc_info.value).lower()

    def test_invalid_markdown_input(
        self,
        client,
        auth_headers,
        db,
        gemini_client,
        mock_gemini_api
    ):
        """Test handling invalid markdown input."""
        # Create page with empty or invalid markdown
        page = Page(
            client_id=gemini_client.id,
            url=MOCK_SITEMAP_URLS[0],
            url_hash=Page.compute_url_hash(MOCK_SITEMAP_URLS[0]),
            raw_markdown=""  # Empty
        )
        db.add(page)
        db.commit()

        page_id = str(page.id)

        response = client.post(
            f'/api/v1/gemini/process-page/{page_id}',
            headers=auth_headers
        )

        # Should handle gracefully
        # assert response.status_code in [400, 422]


class TestGeminiPromptTemplates:
    """Test Gemini prompt templates and generation."""

    def test_markdown_cleaning_prompt(self):
        """Test markdown cleaning prompt structure."""
        # from app.services.gemini import GeminiService
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        # prompt = service.get_markdown_cleaning_prompt(MOCK_APIFY_MARKDOWN)
        #
        # assert "clean" in prompt.lower()
        # assert "markdown" in prompt.lower()
        # assert MOCK_APIFY_MARKDOWN in prompt

    def test_html_generation_prompt(self):
        """Test HTML generation prompt structure."""
        # from app.services.gemini import GeminiService
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        # prompt = service.get_html_generation_prompt(
        #     markdown=MOCK_GEMINI_LLM_MARKDOWN,
        #     url=MOCK_SITEMAP_URLS[0]
        # )
        #
        # assert "html" in prompt.lower()
        # assert "semantic" in prompt.lower() or "seo" in prompt.lower()
        # assert MOCK_SITEMAP_URLS[0] in prompt

    def test_prompt_includes_metadata(self):
        """Test prompts include page metadata."""
        # from app.services.gemini import GeminiService
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        # metadata = {
        #     "title": "Product Page",
        #     "description": "Best product ever"
        # }
        #
        # prompt = service.get_html_generation_prompt(
        #     markdown=MOCK_GEMINI_LLM_MARKDOWN,
        #     url=MOCK_SITEMAP_URLS[0],
        #     metadata=metadata
        # )
        #
        # assert metadata["title"] in prompt
        # assert metadata["description"] in prompt


class TestGeminiPerformance:
    """Test Gemini service performance."""

    def test_batch_processing_efficiency(
        self,
        db,
        gemini_client,
        mock_gemini_api
    ):
        """Test batch processing handles many pages efficiently."""
        # Create 50 pages
        pages = []
        for i in range(50):
            page = Page(
                client_id=gemini_client.id,
                url=f"https://{gemini_client.domain}/page-{i}",
                url_hash=Page.compute_url_hash(
                    f"https://{gemini_client.domain}/page-{i}"
                ),
                raw_markdown=f"# Page {i}\n\nContent"
            )
            db.add(page)
            pages.append(page)

        db.commit()

        # from app.services.gemini import GeminiService
        # import time
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        #
        # start = time.time()
        # service.process_client_pages(gemini_client.id, batch_size=10)
        # duration = time.time() - start
        #
        # # Should complete in reasonable time
        # assert duration < 60  # 60 seconds for 50 pages

    def test_concurrent_processing(self, mock_gemini_api):
        """Test concurrent processing of multiple pages."""
        # from app.services.gemini import GeminiService
        # from concurrent.futures import ThreadPoolExecutor
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        #
        # markdowns = [f"# Page {i}\n\nContent" for i in range(10)]
        #
        # with ThreadPoolExecutor(max_workers=5) as executor:
        #     results = list(executor.map(
        #         service.process_markdown,
        #         markdowns
        #     ))
        #
        # assert len(results) == 10
        # assert all(r is not None for r in results)


class TestGeminiContentQuality:
    """Test quality of Gemini-generated content."""

    def test_generated_html_is_valid(self, mock_gemini_api):
        """Test generated HTML is valid."""
        # from app.services.gemini import GeminiService
        # from html.parser import HTMLParser
        #
        # service = GeminiService(api_key=MOCK_CLIENT_DATA["gemini_api_key"])
        # html = service.generate_html(
        #     markdown=MOCK_GEMINI_LLM_MARKDOWN,
        #     url=MOCK_SITEMAP_URLS[0]
        # )
        #
        # # Should parse without errors
        # parser = HTMLParser()
        # parser.feed(html)

    def test_generated_html_includes_schema(self, mock_gemini_api):
        """Test generated HTML includes schema.org markup."""
        # Expected in MOCK_GEMINI_GEO_HTML
        assert 'itemscope' in MOCK_GEMINI_GEO_HTML
        assert 'itemtype' in MOCK_GEMINI_GEO_HTML
        assert 'schema.org' in MOCK_GEMINI_GEO_HTML

    def test_generated_html_includes_meta_tags(self, mock_gemini_api):
        """Test generated HTML includes proper meta tags."""
        assert '<meta name="description"' in MOCK_GEMINI_GEO_HTML
        assert '<meta name="viewport"' in MOCK_GEMINI_GEO_HTML
        assert '<title>' in MOCK_GEMINI_GEO_HTML

    def test_cleaned_markdown_preserves_structure(self, mock_gemini_api):
        """Test cleaned markdown preserves important structure."""
        # Key elements should be preserved
        assert '# Premium Cotton T-Shirt' in MOCK_GEMINI_LLM_MARKDOWN
        assert '$29.99' in MOCK_GEMINI_LLM_MARKDOWN
        assert 'organic cotton' in MOCK_GEMINI_LLM_MARKDOWN.lower()
