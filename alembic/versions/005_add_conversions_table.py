"""Add conversions table for AI referrer tracking

Revision ID: 005_add_conversions_table
Revises: 004_add_apify_tracking
Create Date: 2025-11-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_add_conversions_table'
down_revision: Union[str, None] = '004_add_apify_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create conversions table for AI referrer attribution tracking."""

    op.create_table(
        'conversions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('referrer_domain', sa.String(255), nullable=True),
        sa.Column('referrer_full_url', sa.Text(), nullable=True),
        sa.Column('landing_url', sa.Text(), nullable=False),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('conversion_value', sa.Float(), nullable=True),
        sa.Column('order_id', sa.String(255), nullable=True),
        sa.Column('ai_source', sa.String(100), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False, server_default='checkout_completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['page_id'], ['pages.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('order_id', name='uq_conversions_order_id'),
    )

    # Create indexes
    op.create_index('ix_conversions_client_id', 'conversions', ['client_id'])
    op.create_index('ix_conversions_converted_at', 'conversions', ['converted_at'])
    op.create_index('ix_conversions_referrer_domain', 'conversions', ['referrer_domain'])
    op.create_index('ix_conversions_ai_source', 'conversions', ['ai_source'])
    op.create_index('ix_conversions_order_id', 'conversions', ['order_id'])


def downgrade() -> None:
    """Drop conversions table."""

    # Drop indexes
    op.drop_index('ix_conversions_order_id', 'conversions')
    op.drop_index('ix_conversions_ai_source', 'conversions')
    op.drop_index('ix_conversions_referrer_domain', 'conversions')
    op.drop_index('ix_conversions_converted_at', 'conversions')
    op.drop_index('ix_conversions_client_id', 'conversions')

    # Drop table
    op.drop_table('conversions')
