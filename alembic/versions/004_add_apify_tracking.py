"""Add Apify tracking fields to pages table

Revision ID: 004_add_apify_tracking
Revises: 003_rename_page_columns
Create Date: 2025-11-20 00:00:00.000000

Adds tracking fields for Apify RAG Web Browser integration:
- apify_run_id: Track Apify Actor run ID
- scrape_error: Store error messages if scraping fails
- scrape_attempts: Track number of scrape attempts for retry logic
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_apify_tracking'
down_revision: Union[str, None] = '003_rename_page_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Apify tracking fields to pages table."""

    # Add Apify tracking columns
    op.add_column('pages', sa.Column('apify_run_id', sa.Text(), nullable=True))
    op.add_column('pages', sa.Column('scrape_error', sa.Text(), nullable=True))
    op.add_column('pages', sa.Column('scrape_attempts', sa.Integer(), nullable=False, server_default='0'))

    # Add index on apify_run_id for faster lookups
    op.create_index('ix_pages_apify_run_id', 'pages', ['apify_run_id'])


def downgrade() -> None:
    """Remove Apify tracking fields."""

    # Remove index
    op.drop_index('ix_pages_apify_run_id', table_name='pages')

    # Remove columns
    op.drop_column('pages', 'scrape_attempts')
    op.drop_column('pages', 'scrape_error')
    op.drop_column('pages', 'apify_run_id')
