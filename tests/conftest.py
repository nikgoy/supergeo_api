"""
Test configuration and shared fixtures.

This module provides pytest fixtures used across all test modules.
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment variables before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['GEMINI_API_KEY'] = 'test-gemini-key'
os.environ['MASTER_API_KEY'] = 'test-master-api-key'
os.environ['FERNET_KEY'] = 'K8JbF7YzQ_8qPjQ8_K8JbF7YzQ_8qPjQ8_K8JbF7YzQ='
os.environ['SECRET_KEY'] = 'test-secret-key'

from app import create_app
from app.models.base import Base, init_db, SessionLocal
from app.models.client import Client, Page, Visit


@pytest.fixture(scope='session')
def app():
    """
    Create Flask app for testing.

    Yields:
        Flask app configured for testing
    """
    # Create app - it will initialize the database using DATABASE_URL env var
    # (set to sqlite:///:memory: on line 13 above)
    app = create_app({
        'TESTING': True,
        'DEBUG': False
    })

    yield app


@pytest.fixture(scope='session')
def _db(app):
    """
    Create database tables.

    Args:
        app: Flask app fixture

    Yields:
        Database with tables created
    """
    # Create all tables
    from app.models.base import engine
    Base.metadata.create_all(bind=engine)

    yield engine

    # Drop all tables after tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope='function')
def db(_db):
    """
    Provide a database session with transaction rollback.

    Each test gets a fresh database state.

    Yields:
        Database session
    """
    connection = _db.connect()
    transaction = connection.begin()

    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope='function')
def client(app):
    """
    Provide Flask test client.

    Args:
        app: Flask app fixture

    Yields:
        Flask test client
    """
    return app.test_client()


@pytest.fixture(scope='function')
def auth_headers():
    """
    Provide authentication headers for API requests.

    Returns:
        Dictionary with X-API-Key header
    """
    return {'X-API-Key': 'test-master-api-key'}


@pytest.fixture(scope='function')
def sample_client(db):
    """
    Create a sample client for testing.

    Args:
        db: Database session fixture

    Returns:
        Sample Client instance
    """
    client = Client(
        name='Test Corp',
        domain='test.com',
        cloudflare_account_id='test-account-id',
        cloudflare_kv_namespace_id='test-kv-namespace',
        is_active=True
    )
    client.cloudflare_api_token = 'test-cloudflare-token'
    client.gemini_api_key = 'test-gemini-key'

    db.add(client)
    db.commit()
    db.refresh(client)

    return client


@pytest.fixture(scope='function')
def sample_page(db, sample_client):
    """
    Create a sample page for testing.

    Args:
        db: Database session fixture
        sample_client: Sample client fixture

    Returns:
        Sample Page instance
    """
    page = Page(
        client_id=sample_client.id,
        url='https://test.com/page1',
        url_hash=Page.compute_url_hash('https://test.com/page1'),
        raw_html='<html><body>Test content</body></html>',
        markdown_content='# Test content',
        simple_html='<h1>Test content</h1>',
        kv_key='https/test-com/page1',
        version=1
    )
    page.update_content_hash()

    db.add(page)
    db.commit()
    db.refresh(page)

    return page


@pytest.fixture(scope='function')
def sample_visit(db, sample_client, sample_page):
    """
    Create a sample visit for testing.

    Args:
        db: Database session fixture
        sample_client: Sample client fixture
        sample_page: Sample page fixture

    Returns:
        Sample Visit instance
    """
    visit = Visit(
        page_id=sample_page.id,
        client_id=sample_client.id,
        url=sample_page.url,
        visitor_type='ai_bot',
        user_agent='Mozilla/5.0 (compatible; GPTBot/1.0)',
        ip_hash=Visit.hash_ip('192.168.1.1'),
        bot_name='GPTBot'
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)

    return visit


@pytest.fixture(scope='function')
def multiple_clients(db):
    """
    Create multiple clients for testing pagination/listing.

    Args:
        db: Database session fixture

    Returns:
        List of Client instances
    """
    clients = []
    for i in range(5):
        client = Client(
            name=f'Test Corp {i}',
            domain=f'test{i}.com',
            cloudflare_account_id=f'account-{i}',
            is_active=i % 2 == 0  # Alternate active/inactive
        )
        if i % 2 == 0:
            client.cloudflare_api_token = f'token-{i}'

        db.add(client)
        clients.append(client)

    db.commit()

    for client in clients:
        db.refresh(client)

    return clients
