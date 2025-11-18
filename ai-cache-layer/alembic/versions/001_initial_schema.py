"""Initial schema with clients, pages, and visits tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-11-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""

    # Enable pgcrypto extension for uuid_generate_v4()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # Create clients table
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('domain', sa.Text(), nullable=False),
        sa.Column('cloudflare_account_id', sa.Text(), nullable=True),
        sa.Column('cloudflare_api_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('cloudflare_kv_namespace_id', sa.Text(), nullable=True),
        sa.Column('gemini_api_key_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('name', name='uq_client_name'),
        sa.UniqueConstraint('domain', name='uq_client_domain'),
    )
    op.create_index('ix_clients_name', 'clients', ['name'])
    op.create_index('ix_clients_domain', 'clients', ['domain'])

    # Create pages table
    op.create_table(
        'pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('url_hash', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.Text(), nullable=True),
        sa.Column('raw_html', sa.Text(), nullable=True),
        sa.Column('markdown_content', sa.Text(), nullable=True),
        sa.Column('simple_html', sa.Text(), nullable=True),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('kv_uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('kv_key', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('client_id', 'url', name='uq_client_url'),
    )
    op.create_index('ix_pages_url', 'pages', ['url'])
    op.create_index('ix_pages_url_hash', 'pages', ['url_hash'])

    # Create visits table
    op.create_table(
        'visits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('visitor_type', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_hash', sa.Text(), nullable=True),
        sa.Column('referrer', sa.Text(), nullable=True),
        sa.Column('bot_name', sa.Text(), nullable=True),
        sa.Column('visited_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['page_id'], ['pages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_visits_visited_at', 'visits', ['visited_at'])
    op.create_index('ix_visits_visitor_type', 'visits', ['visitor_type'])

    # Create trigger function for updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create triggers for clients table
    op.execute("""
        CREATE TRIGGER update_clients_updated_at
        BEFORE UPDATE ON clients
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Create triggers for pages table
    op.execute("""
        CREATE TRIGGER update_pages_updated_at
        BEFORE UPDATE ON pages
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop all tables and extensions."""

    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_pages_updated_at ON pages;')
    op.execute('DROP TRIGGER IF EXISTS update_clients_updated_at ON clients;')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column();')

    # Drop tables
    op.drop_table('visits')
    op.drop_table('pages')
    op.drop_table('clients')

    # Note: We don't drop the pgcrypto extension as it might be used by other schemas
