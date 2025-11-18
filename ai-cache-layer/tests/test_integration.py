"""
Integration tests.

Tests complete workflows and interactions between components.
"""
import pytest
from datetime import datetime

from app.models.client import Client, Page, Visit


class TestClientWorkflow:
    """Test complete client workflow."""

    def test_create_client_and_add_pages(self, client, auth_headers, db):
        """Test creating a client and adding pages."""
        # Create client via API
        client_payload = {
            'name': 'Integration Test Corp',
            'domain': 'integration.com',
            'cloudflare_account_id': 'test-account',
            'cloudflare_api_token': 'test-token'
        }

        create_response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            json=client_payload
        )

        assert create_response.status_code == 201
        client_data = create_response.get_json()['client']
        client_id = client_data['id']

        # Add pages to the client
        from app.models.client import Client as ClientModel, Page

        db_client = db.query(ClientModel).filter(ClientModel.id == client_id).first()

        page1 = Page(
            client_id=db_client.id,
            url='https://integration.com/page1',
            url_hash=Page.compute_url_hash('https://integration.com/page1'),
            raw_html='<html>Page 1</html>'
        )
        page2 = Page(
            client_id=db_client.id,
            url='https://integration.com/page2',
            url_hash=Page.compute_url_hash('https://integration.com/page2'),
            raw_html='<html>Page 2</html>'
        )

        db.add(page1)
        db.add(page2)
        db.commit()

        # Verify relationship
        assert len(db_client.pages) == 2

        # Delete client should cascade delete pages
        delete_response = client.delete(
            f'/api/v1/clients/{client_id}',
            headers=auth_headers
        )

        assert delete_response.status_code == 200

        # Verify pages are deleted
        pages = db.query(Page).filter(Page.client_id == client_id).all()
        assert len(pages) == 0

    def test_update_client_credentials(self, client, auth_headers, sample_client, db):
        """Test updating client credentials."""
        client_id = str(sample_client.id)

        # Update credentials
        update_payload = {
            'cloudflare_api_token': 'new-updated-token',
            'cloudflare_account_id': 'new-account-id'
        }

        update_response = client.put(
            f'/api/v1/clients/{client_id}',
            headers=auth_headers,
            json=update_payload
        )

        assert update_response.status_code == 200

        # Get with secrets to verify
        get_response = client.get(
            f'/api/v1/clients/{client_id}?include_secrets=true',
            headers=auth_headers
        )

        data = get_response.get_json()
        assert data['cloudflare_api_token'] == 'new-updated-token'
        assert data['cloudflare_account_id'] == 'new-account-id'


class TestPageProcessingWorkflow:
    """Test page processing workflow."""

    def test_complete_page_pipeline(self, db, sample_client):
        """Test complete page processing pipeline."""
        # 1. Scrape page (simulated)
        page = Page(
            client_id=sample_client.id,
            url='https://test.com/article',
            url_hash=Page.compute_url_hash('https://test.com/article'),
            raw_html='<html><body><h1>Article Title</h1><p>Content here</p></body></html>'
        )
        page.update_content_hash()
        page.last_scraped_at = datetime.utcnow()

        db.add(page)
        db.commit()

        # 2. Process with Gemini (simulated)
        page.markdown_content = '# Article Title\n\nContent here'
        page.last_processed_at = datetime.utcnow()

        db.commit()

        # 3. Generate simple HTML (simulated)
        page.simple_html = '<h1>Article Title</h1><p>Content here</p>'

        db.commit()

        # 4. Upload to KV (simulated)
        page.kv_key = 'https/test-com/article'
        page.kv_uploaded_at = datetime.utcnow()
        page.version += 1

        db.commit()
        db.refresh(page)

        # Verify complete pipeline
        assert page.raw_html is not None
        assert page.markdown_content is not None
        assert page.simple_html is not None
        assert page.kv_key is not None
        assert page.version == 2
        assert page.last_scraped_at is not None
        assert page.last_processed_at is not None
        assert page.kv_uploaded_at is not None

    def test_page_update_detection(self, db, sample_client):
        """Test detecting page content changes."""
        # Create page
        page = Page(
            client_id=sample_client.id,
            url='https://test.com/dynamic',
            url_hash=Page.compute_url_hash('https://test.com/dynamic'),
            raw_html='<html>Version 1</html>'
        )
        page.update_content_hash()

        db.add(page)
        db.commit()

        original_hash = page.content_hash

        # Update content
        page.raw_html = '<html>Version 2</html>'
        page.update_content_hash()

        db.commit()

        new_hash = page.content_hash

        # Hashes should be different
        assert original_hash != new_hash

    def test_page_version_incrementing(self, db, sample_client):
        """Test incrementing page versions."""
        page = Page(
            client_id=sample_client.id,
            url='https://test.com/versioned',
            url_hash=Page.compute_url_hash('https://test.com/versioned'),
            raw_html='<html>Content</html>',
            version=1
        )

        db.add(page)
        db.commit()

        # Simulate multiple updates
        for i in range(3):
            page.version += 1
            db.commit()

        db.refresh(page)
        assert page.version == 4


class TestVisitTracking:
    """Test visit tracking workflow."""

    def test_track_ai_bot_visit(self, db, sample_client, sample_page):
        """Test tracking an AI bot visit."""
        # Simulate AI bot visit
        visit = Visit(
            page_id=sample_page.id,
            client_id=sample_client.id,
            url=sample_page.url,
            visitor_type='ai_bot',
            user_agent='Mozilla/5.0 (compatible; GPTBot/1.0)',
            ip_hash=Visit.hash_ip('192.168.1.100'),
            bot_name='GPTBot'
        )

        db.add(visit)
        db.commit()
        db.refresh(visit)

        assert visit.id is not None
        assert visit.visitor_type == 'ai_bot'
        assert visit.bot_name == 'GPTBot'

        # Verify relationships
        assert visit.page == sample_page
        assert visit.client == sample_client

    def test_track_multiple_visits_to_same_page(self, db, sample_client, sample_page):
        """Test tracking multiple visits to the same page."""
        # Create multiple visits
        visits = []
        for i in range(5):
            visit = Visit(
                page_id=sample_page.id,
                client_id=sample_client.id,
                url=sample_page.url,
                visitor_type='ai_bot' if i % 2 == 0 else 'direct',
                ip_hash=Visit.hash_ip(f'192.168.1.{i}')
            )
            db.add(visit)
            visits.append(visit)

        db.commit()

        # Query visits for page
        page_visits = db.query(Visit).filter(Visit.page_id == sample_page.id).all()

        assert len(page_visits) == 5

        # Count by type
        ai_visits = [v for v in page_visits if v.visitor_type == 'ai_bot']
        direct_visits = [v for v in page_visits if v.visitor_type == 'direct']

        assert len(ai_visits) == 3
        assert len(direct_visits) == 2

    def test_visit_without_page(self, db, sample_client):
        """Test tracking visit to non-cached page."""
        # Visit to a URL that doesn't have a cached page
        visit = Visit(
            page_id=None,  # No page yet
            client_id=sample_client.id,
            url='https://test.com/new-uncached-page',
            visitor_type='ai_bot',
            bot_name='ClaudeBot'
        )

        db.add(visit)
        db.commit()
        db.refresh(visit)

        assert visit.id is not None
        assert visit.page_id is None
        assert visit.url == 'https://test.com/new-uncached-page'


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation."""

    def test_clients_have_isolated_pages(self, db):
        """Test that pages are isolated per client."""
        # Create two clients
        client1 = Client(name='Client 1', domain='client1.com')
        client2 = Client(name='Client 2', domain='client2.com')

        db.add(client1)
        db.add(client2)
        db.commit()

        # Add pages to each client
        page1 = Page(
            client_id=client1.id,
            url='https://client1.com/page',
            url_hash=Page.compute_url_hash('https://client1.com/page')
        )
        page2 = Page(
            client_id=client2.id,
            url='https://client2.com/page',
            url_hash=Page.compute_url_hash('https://client2.com/page')
        )

        db.add(page1)
        db.add(page2)
        db.commit()

        # Verify isolation
        client1_pages = db.query(Page).filter(Page.client_id == client1.id).all()
        client2_pages = db.query(Page).filter(Page.client_id == client2.id).all()

        assert len(client1_pages) == 1
        assert len(client2_pages) == 1
        assert client1_pages[0].url == 'https://client1.com/page'
        assert client2_pages[0].url == 'https://client2.com/page'

    def test_same_url_different_clients(self, db):
        """Test that same URL can exist for different clients."""
        # Create two clients
        client1 = Client(name='Client A', domain='clienta.com')
        client2 = Client(name='Client B', domain='clientb.com')

        db.add(client1)
        db.add(client2)
        db.commit()

        # Same URL for both clients (different domains, but same path)
        same_path = '/products/item-123'
        page1 = Page(
            client_id=client1.id,
            url=f'https://clienta.com{same_path}',
            url_hash=Page.compute_url_hash(f'https://clienta.com{same_path}')
        )
        page2 = Page(
            client_id=client2.id,
            url=f'https://clientb.com{same_path}',
            url_hash=Page.compute_url_hash(f'https://clientb.com{same_path}')
        )

        db.add(page1)
        db.add(page2)
        db.commit()

        # Both should exist
        assert page1.id is not None
        assert page2.id is not None
        assert page1.id != page2.id


class TestErrorHandling:
    """Test error handling in workflows."""

    def test_api_error_handling_invalid_json(self, client, auth_headers):
        """Test API handles invalid JSON gracefully."""
        response = client.post(
            '/api/v1/clients',
            headers=auth_headers,
            data='invalid-json',
            content_type='application/json'
        )

        # Should return error, not crash
        assert response.status_code in [400, 415]

    def test_api_error_handling_invalid_uuid(self, client, auth_headers):
        """Test API handles invalid UUID gracefully."""
        response = client.get(
            '/api/v1/clients/not-a-valid-uuid',
            headers=auth_headers
        )

        # Should return error, not crash
        assert response.status_code in [400, 404]

    def test_database_constraint_violations(self, db, sample_client):
        """Test handling database constraint violations."""
        # Try to create page without required fields
        page = Page(
            client_id=sample_client.id,
            # Missing url and url_hash
        )

        db.add(page)

        with pytest.raises(Exception):  # Should raise integrity error
            db.commit()

        db.rollback()  # Clean up

    def test_encryption_with_invalid_data(self):
        """Test encryption service with invalid data."""
        from app.services.encryption import EncryptionService

        service = EncryptionService()

        # Empty string should raise error
        with pytest.raises(ValueError):
            service.encrypt('')

        # Empty bytes should raise error
        with pytest.raises(ValueError):
            service.decrypt(b'')
