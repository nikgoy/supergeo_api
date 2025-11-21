"""Separate bot crawlers from AI referrals

Revision ID: 007_separate_bot_crawlers_from_ai_referrals
Revises: 006_add_worker_fields
Create Date: 2025-11-21 23:50:00.000000

This migration separates the tracking of bot crawlers from AI chat app referrals:

1. Adds ai_source column to visits table
   - bot_name: Bot crawlers (GPTBot, ClaudeBot, etc.)
   - ai_source: AI chat app sources (ChatGPT, Perplexity, etc.)
   - visitor_type: 'ai_bot', 'ai_referral', 'direct', or 'worker_proxy'

2. Renames conversions table to orders
   - Better reflects the business purpose (order tracking)
   - Keeps semantic separation: visits track traffic, orders track revenue
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_separate_bot_crawlers_from_ai_referrals'
down_revision: Union[str, None] = '006_add_worker_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ai_source to visits and rename conversions to orders."""

    # 1. Add ai_source column to visits table
    op.add_column('visits', sa.Column('ai_source', sa.String(100), nullable=True))
    op.create_index('ix_visits_ai_source', 'visits', ['ai_source'])

    # 2. Rename conversions table to orders
    op.rename_table('conversions', 'orders')

    # 3. Rename all conversions indexes to orders
    op.execute('ALTER INDEX ix_conversions_client_id RENAME TO ix_orders_client_id')
    op.execute('ALTER INDEX ix_conversions_converted_at RENAME TO ix_orders_converted_at')
    op.execute('ALTER INDEX ix_conversions_referrer_domain RENAME TO ix_orders_referrer_domain')
    op.execute('ALTER INDEX ix_conversions_ai_source RENAME TO ix_orders_ai_source')
    op.execute('ALTER INDEX ix_conversions_order_id RENAME TO ix_orders_order_id')

    # 4. Rename unique constraint
    op.execute('ALTER TABLE orders RENAME CONSTRAINT uq_conversions_order_id TO uq_orders_order_id')


def downgrade() -> None:
    """Remove ai_source from visits and rename orders back to conversions."""

    # 1. Rename orders table back to conversions
    op.rename_table('orders', 'conversions')

    # 2. Rename all orders indexes back to conversions
    op.execute('ALTER INDEX ix_orders_client_id RENAME TO ix_conversions_client_id')
    op.execute('ALTER INDEX ix_orders_converted_at RENAME TO ix_conversions_converted_at')
    op.execute('ALTER INDEX ix_orders_referrer_domain RENAME TO ix_conversions_referrer_domain')
    op.execute('ALTER INDEX ix_orders_ai_source RENAME TO ix_conversions_ai_source')
    op.execute('ALTER INDEX ix_orders_order_id RENAME TO ix_conversions_order_id')

    # 3. Rename unique constraint back
    op.execute('ALTER TABLE conversions RENAME CONSTRAINT uq_orders_order_id TO uq_conversions_order_id')

    # 4. Remove ai_source column from visits
    op.drop_index('ix_visits_ai_source', 'visits')
    op.drop_column('visits', 'ai_source')
