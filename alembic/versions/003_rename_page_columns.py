"""Rename page content columns for clarity

Revision ID: 003_rename_page_columns
Revises: 002_add_page_analytics
Create Date: 2025-11-20 00:00:00.000000

Column changes:
- raw_html -> raw_markdown (reflects actual content type)
- markdown_content -> llm_markdown (clarifies LLM-processed content)
- simple_html -> geo_html (GeoGuide-specific HTML format)

Note: Text type in PostgreSQL already supports large data (up to 1GB),
which is appropriate for these content fields.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_rename_page_columns'
down_revision: Union[str, None] = '002_add_page_analytics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename page content columns for clarity."""

    # Rename columns in pages table
    op.alter_column('pages', 'raw_html', new_column_name='raw_markdown')
    op.alter_column('pages', 'markdown_content', new_column_name='llm_markdown')
    op.alter_column('pages', 'simple_html', new_column_name='geo_html')

    # Also update the PageAnalytics column names to match
    op.alter_column('page_analytics', 'urls_with_raw_html', new_column_name='urls_with_raw_markdown')
    op.alter_column('page_analytics', 'urls_with_simple_html', new_column_name='urls_with_geo_html')

    # Update completion rate column names for consistency
    op.alter_column('page_analytics', 'simple_html_completion_rate', new_column_name='geo_html_completion_rate')


def downgrade() -> None:
    """Revert column name changes."""

    # Revert pages table column names
    op.alter_column('pages', 'raw_markdown', new_column_name='raw_html')
    op.alter_column('pages', 'llm_markdown', new_column_name='markdown_content')
    op.alter_column('pages', 'geo_html', new_column_name='simple_html')

    # Revert PageAnalytics column names
    op.alter_column('page_analytics', 'urls_with_raw_markdown', new_column_name='urls_with_raw_html')
    op.alter_column('page_analytics', 'urls_with_geo_html', new_column_name='urls_with_simple_html')

    # Revert completion rate column names
    op.alter_column('page_analytics', 'geo_html_completion_rate', new_column_name='simple_html_completion_rate')
