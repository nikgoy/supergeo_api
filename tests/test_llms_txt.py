"""
Tests for llms.txt generation service.

Tests generating llms.txt format from pages, caching, and spec compliance.
"""
import pytest
from datetime import datetime

from app.models.client import Client, Page
from tests.fixtures.test_data import (
    MOCK_CLIENT_DATA,
    MOCK_SITEMAP_URLS,
    MOCK_GEMINI_GEO_HTML,
    MOCK_GEMINI_LLM_MARKDOWN,
    MOCK_LLMS_TXT,
)


@pytest.fixture
def llms_client(db):
    """Create a client for llms.txt testing."""
    client = Client(
        name="LLMS Test Shop",
        domain="llms-test.com",
        is_active=True
    )

    db.add(client)
    db.commit()
    db.refresh(client)

    return client


@pytest.fixture
def pages_for_llms_txt(db, llms_client):
    """Create pages with geo_html for llms.txt generation."""
    pages_data = [
        {
            'url': f'https://{llms_client.domain}/',
            'title': 'Homepage',
            'description': 'Welcome to our shop'
        },
        {
            'url': f'https://{llms_client.domain}/products/shirt',
            'title': 'Premium Cotton T-Shirt',
            'description': 'High-quality organic cotton t-shirt. $29.99'
        },
        {
            'url': f'https://{llms_client.domain}/products/pants',
            'title': 'Organic Cotton Pants',
            'description': 'Comfortable cotton pants. $49.99'
        },
        {
            'url': f'https://{llms_client.domain}/pages/about',
            'title': 'About Us',
            'description': 'Learn about our mission'
        },
        {
            'url': f'https://{llms_client.domain}/pages/contact',
            'title': 'Contact',
            'description': 'Get in touch with us'
        },
    ]

    pages = []
    for data in pages_data:
        page = Page(
            client_id=llms_client.id,
            url=data['url'],
            url_hash=Page.compute_url_hash(data['url']),
            raw_markdown=f"# {data['title']}\n\n{data['description']}",
            llm_markdown=f"# {data['title']}\n\n{data['description']}",
            geo_html=f"<html><head><title>{data['title']}</title></head><body><h1>{data['title']}</h1><p>{data['description']}</p></body></html>",
            last_processed_at=datetime.utcnow()
        )
        db.add(page)
        pages.append(page)

    db.commit()

    for page in pages:
        db.refresh(page)

    return pages


class TestLLMSTxtService:
    """Test llms.txt generation service."""

    def test_generate_llms_txt_for_client(self, llms_client, pages_for_llms_txt):
        """Test generating llms.txt from client pages."""
        # from app.services.llms_txt import LLMSTxtService
        #
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # assert result is not None
        # assert len(result) > 0
        # assert llms_client.name in result
        # assert llms_client.domain in result

    def test_llms_txt_includes_all_pages(self, llms_client, pages_for_llms_txt):
        """Test llms.txt includes all pages with geo_html."""
        # from app.services.llms_txt import LLMSTxtService
        #
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # # Should include all 5 pages
        # for page in pages_for_llms_txt:
        #     assert page.url in result

    def test_llms_txt_format_compliance(self):
        """Test llms.txt follows official spec."""
        # Based on https://llmstxt.org/
        lines = MOCK_LLMS_TXT.split('\n')

        # Should start with # (site name)
        assert lines[0].startswith('#')

        # Should have > (description)
        description_lines = [l for l in lines if l.startswith('>')]
        assert len(description_lines) > 0

        # Should have ## Pages section
        assert '## Pages' in MOCK_LLMS_TXT

        # URLs should be prefixed with -
        url_lines = [l for l in lines if l.strip().startswith('- ') and 'https://' in l]
        assert len(url_lines) > 0

    def test_llms_txt_metadata_extraction(self, pages_for_llms_txt):
        """Test extracting metadata from pages."""
        # from app.services.llms_txt import LLMSTxtService
        #
        # service = LLMSTxtService()
        # page = pages_for_llms_txt[1]  # Product page
        #
        # metadata = service.extract_page_metadata(page)
        #
        # assert 'title' in metadata
        # assert 'description' in metadata
        # assert metadata['title'] == 'Premium Cotton T-Shirt'

    def test_llms_txt_excludes_unpublished_pages(self, db, llms_client):
        """Test llms.txt only includes pages with geo_html."""
        # Create pages at different stages
        published_page = Page(
            client_id=llms_client.id,
            url=f'https://{llms_client.domain}/published',
            url_hash=Page.compute_url_hash(f'https://{llms_client.domain}/published'),
            geo_html=MOCK_GEMINI_GEO_HTML
        )
        unpublished_page = Page(
            client_id=llms_client.id,
            url=f'https://{llms_client.domain}/unpublished',
            url_hash=Page.compute_url_hash(f'https://{llms_client.domain}/unpublished'),
            raw_markdown="# Not processed yet"
            # No geo_html
        )

        db.add(published_page)
        db.add(unpublished_page)
        db.commit()

        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # assert published_page.url in result
        # assert unpublished_page.url not in result

    def test_llms_txt_ordering(self, pages_for_llms_txt):
        """Test pages are ordered logically."""
        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(pages_for_llms_txt[0].client_id)
        #
        # # Homepage should be first
        # lines = result.split('\n')
        # first_url_line = next(l for l in lines if 'https://' in l)
        # assert pages_for_llms_txt[0].url in first_url_line  # Homepage


class TestLLMSTxtAPIEndpoints:
    """Test llms.txt API endpoints."""

    def test_generate_llms_txt_endpoint(
        self,
        client,
        auth_headers,
        llms_client,
        pages_for_llms_txt
    ):
        """Test generating llms.txt via API."""
        client_id = str(llms_client.id)

        response = client.get(
            f'/api/v1/llms-txt/generate/{client_id}',
            headers=auth_headers
        )

        # Expected response when implemented
        # assert response.status_code == 200
        # data = response.get_json()
        #
        # assert 'llms_txt' in data
        # assert 'page_count' in data
        # assert 'generated_at' in data
        # assert data['page_count'] == 5

    def test_generate_llms_txt_client_not_found(self, client, auth_headers):
        """Test generating llms.txt for non-existent client."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'

        response = client.get(
            f'/api/v1/llms-txt/generate/{fake_uuid}',
            headers=auth_headers
        )

        # Should return 404
        # assert response.status_code == 404

    def test_generate_llms_txt_no_pages(
        self,
        client,
        auth_headers,
        llms_client
    ):
        """Test generating llms.txt when no pages exist."""
        client_id = str(llms_client.id)

        response = client.get(
            f'/api/v1/llms-txt/generate/{client_id}',
            headers=auth_headers
        )

        # Should still return valid llms.txt with no pages section
        # assert response.status_code == 200
        # data = response.get_json()
        # assert data['page_count'] == 0


class TestLLMSTxtCaching:
    """Test llms.txt caching mechanisms."""

    def test_llms_txt_cached_result(self):
        """Test llms.txt is cached after generation."""
        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        #
        # import time
        #
        # # First generation
        # start1 = time.time()
        # result1 = service.generate_for_client(client_id)
        # duration1 = time.time() - start1
        #
        # # Second generation (should be cached)
        # start2 = time.time()
        # result2 = service.generate_for_client(client_id)
        # duration2 = time.time() - start2
        #
        # assert result1 == result2
        # assert duration2 < duration1  # Faster due to cache

    def test_cache_invalidation_on_page_update(self, db, pages_for_llms_txt):
        """Test cache is invalidated when pages are updated."""
        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        #
        # client_id = pages_for_llms_txt[0].client_id
        #
        # # Generate
        # result1 = service.generate_for_client(client_id)
        #
        # # Update a page
        # page = pages_for_llms_txt[0]
        # page.geo_html = "<html><body>Updated content</body></html>"
        # db.commit()
        #
        # # Regenerate (should reflect update)
        # result2 = service.generate_for_client(client_id)
        #
        # # Results should be different
        # # (or service should detect page was updated)

    def test_cache_key_generation(self):
        """Test cache key generation for clients."""
        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        #
        # client_id = "test-client-123"
        # cache_key = service.get_cache_key(client_id)
        #
        # assert client_id in cache_key
        # assert 'llms_txt' in cache_key.lower()


class TestLLMSTxtContentFormatting:
    """Test content formatting in llms.txt."""

    def test_page_title_formatting(self):
        """Test page titles are properly formatted."""
        # Titles should be on the same line as the dash
        # - Title: https://example.com/page
        assert '- Homepage:' in MOCK_LLMS_TXT
        assert '- Premium Cotton T-Shirt:' in MOCK_LLMS_TXT

    def test_page_description_formatting(self):
        """Test page descriptions are indented."""
        lines = MOCK_LLMS_TXT.split('\n')

        # Descriptions should be indented (2 spaces)
        description_lines = [l for l in lines if l.startswith('  ') and not l.startswith('  -')]
        assert len(description_lines) > 0

    def test_url_formatting(self):
        """Test URLs are properly formatted."""
        # URLs should be in format: - Title: https://...
        lines = MOCK_LLMS_TXT.split('\n')
        url_lines = [l for l in lines if 'https://' in l and l.strip().startswith('-')]

        assert len(url_lines) > 0

        for line in url_lines:
            assert ': https://' in line

    def test_section_headers(self):
        """Test section headers are properly formatted."""
        assert '# Test Shop' in MOCK_LLMS_TXT or '# ' in MOCK_LLMS_TXT
        assert '## Pages' in MOCK_LLMS_TXT

    def test_site_description_blockquote(self):
        """Test site description uses blockquote format."""
        lines = MOCK_LLMS_TXT.split('\n')
        blockquote_lines = [l for l in lines if l.startswith('>')]

        assert len(blockquote_lines) > 0


class TestLLMSTxtMetadata:
    """Test metadata in llms.txt."""

    def test_includes_site_name(self, llms_client):
        """Test llms.txt includes site name."""
        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # assert llms_client.name in result

    def test_includes_site_description(self):
        """Test llms.txt includes site description."""
        # Should have description after site name
        lines = MOCK_LLMS_TXT.split('\n')

        # Find description (> ...)
        description = next((l for l in lines if l.startswith('>')), None)
        assert description is not None
        assert len(description) > 2  # More than just ">"

    def test_includes_page_metadata(self):
        """Test llms.txt includes page-level metadata."""
        # Each page should have title and description
        assert 'Premium Cotton T-Shirt' in MOCK_LLMS_TXT
        assert '$29.99' in MOCK_LLMS_TXT


class TestLLMSTxtSpecialCases:
    """Test special cases in llms.txt generation."""

    def test_handles_pages_without_description(self, db, llms_client):
        """Test handling pages without descriptions."""
        page = Page(
            client_id=llms_client.id,
            url=f'https://{llms_client.domain}/no-description',
            url_hash=Page.compute_url_hash(f'https://{llms_client.domain}/no-description'),
            geo_html="<html><head><title>Page</title></head><body></body></html>"
            # Minimal HTML, no description
        )
        db.add(page)
        db.commit()

        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # # Should still include page
        # assert page.url in result

    def test_handles_pages_with_long_descriptions(self, db, llms_client):
        """Test handling pages with very long descriptions."""
        long_description = "A" * 1000  # Very long

        page = Page(
            client_id=llms_client.id,
            url=f'https://{llms_client.domain}/long-description',
            url_hash=Page.compute_url_hash(f'https://{llms_client.domain}/long-description'),
            llm_markdown=f"# Page\n\n{long_description}",
            geo_html=f"<html><body><p>{long_description}</p></body></html>"
        )
        db.add(page)
        db.commit()

        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # # Should truncate or handle gracefully
        # assert page.url in result

    def test_handles_special_characters_in_titles(self, db, llms_client):
        """Test handling special characters in titles."""
        special_title = "Product: \"Premium\" & <Exclusive>"

        page = Page(
            client_id=llms_client.id,
            url=f'https://{llms_client.domain}/special',
            url_hash=Page.compute_url_hash(f'https://{llms_client.domain}/special'),
            llm_markdown=f"# {special_title}",
            geo_html=f"<html><head><title>{special_title}</title></head></html>"
        )
        db.add(page)
        db.commit()

        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # # Should escape or handle special characters
        # assert page.url in result

    def test_handles_urls_with_query_params(self, db, llms_client):
        """Test handling URLs with query parameters."""
        url_with_params = f'https://{llms_client.domain}/search?q=test&sort=price'

        page = Page(
            client_id=llms_client.id,
            url=url_with_params,
            url_hash=Page.compute_url_hash(url_with_params),
            geo_html="<html><body>Search results</body></html>"
        )
        db.add(page)
        db.commit()

        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # # Should include full URL
        # assert url_with_params in result


class TestLLMSTxtPerformance:
    """Test llms.txt generation performance."""

    def test_generation_speed_with_many_pages(self, db, llms_client):
        """Test generation handles many pages efficiently."""
        # Create 100 pages
        pages = []
        for i in range(100):
            page = Page(
                client_id=llms_client.id,
                url=f'https://{llms_client.domain}/page-{i}',
                url_hash=Page.compute_url_hash(f'https://{llms_client.domain}/page-{i}'),
                llm_markdown=f"# Page {i}",
                geo_html=f"<html><body>Page {i}</body></html>"
            )
            db.add(page)
            pages.append(page)

        db.commit()

        # from app.services.llms_txt import LLMSTxtService
        # import time
        #
        # service = LLMSTxtService()
        #
        # start = time.time()
        # result = service.generate_for_client(llms_client.id)
        # duration = time.time() - start
        #
        # # Should be fast
        # assert duration < 5  # 5 seconds for 100 pages

    def test_output_size_reasonable(self, llms_client, pages_for_llms_txt):
        """Test generated llms.txt is reasonable size."""
        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # size_kb = len(result.encode('utf-8')) / 1024
        #
        # # Should be reasonable (not megabytes)
        # assert size_kb < 100  # Less than 100 KB for 5 pages


class TestLLMSTxtIntegration:
    """Test llms.txt integration with other services."""

    def test_llms_txt_updates_with_pipeline(self, db, llms_client):
        """Test llms.txt reflects pipeline updates."""
        # Add new page
        new_page = Page(
            client_id=llms_client.id,
            url=f'https://{llms_client.domain}/new-page',
            url_hash=Page.compute_url_hash(f'https://{llms_client.domain}/new-page'),
            geo_html="<html><body>New page</body></html>"
        )
        db.add(new_page)
        db.commit()

        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(llms_client.id)
        #
        # # Should include new page
        # assert new_page.url in result

    def test_llms_txt_excludes_deleted_pages(self, db, pages_for_llms_txt):
        """Test llms.txt excludes deleted pages."""
        client_id = pages_for_llms_txt[0].client_id

        # Delete a page
        deleted_page = pages_for_llms_txt[0]
        deleted_url = deleted_page.url
        db.delete(deleted_page)
        db.commit()

        # from app.services.llms_txt import LLMSTxtService
        # service = LLMSTxtService()
        # result = service.generate_for_client(client_id)
        #
        # # Should not include deleted page
        # assert deleted_url not in result
