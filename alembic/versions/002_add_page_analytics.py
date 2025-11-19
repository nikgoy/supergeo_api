"""Add page_analytics table for tracking pipeline progress

Revision ID: 002_add_page_analytics
Revises: 001_initial_schema
Create Date: 2025-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_page_analytics'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create page_analytics table."""

    op.create_table(
        'page_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_urls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('urls_with_raw_html', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('urls_with_markdown', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('urls_with_simple_html', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('urls_with_kv_key', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('html_completion_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('markdown_completion_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('simple_html_completion_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('kv_upload_completion_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('pages_updated_last_30_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('client_id', name='uq_page_analytics_client_id'),
    )
    op.create_index('ix_page_analytics_client_id', 'page_analytics', ['client_id'])
    op.create_index('ix_page_analytics_last_calculated_at', 'page_analytics', ['last_calculated_at'])

    # Create trigger for page_analytics table
    op.execute("""
        CREATE TRIGGER update_page_analytics_updated_at
        BEFORE UPDATE ON page_analytics
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop page_analytics table."""

    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS update_page_analytics_updated_at ON page_analytics;')

    # Drop table
    op.drop_table('page_analytics')
