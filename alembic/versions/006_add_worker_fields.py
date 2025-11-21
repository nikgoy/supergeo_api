"""Add Cloudflare Worker fields to clients table

Revision ID: 006_add_worker_fields
Revises: 005_add_conversions_table
Create Date: 2025-11-21 00:00:00.000000

Adds fields for Cloudflare Worker management:
- cloudflare_zone_id: Zone ID for Workers routing
- worker_script_name: Deployed worker script name
- worker_deployed_at: When worker was deployed
- worker_route_id: Route ID connecting worker to zone
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_add_worker_fields'
down_revision: Union[str, None] = '005_add_conversions_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Cloudflare Worker fields to clients table."""

    # Add Cloudflare Worker columns
    op.add_column('clients', sa.Column('cloudflare_zone_id', sa.Text(), nullable=True))
    op.add_column('clients', sa.Column('worker_script_name', sa.Text(), nullable=True))
    op.add_column('clients', sa.Column('worker_deployed_at', sa.DateTime(), nullable=True))
    op.add_column('clients', sa.Column('worker_route_id', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove Cloudflare Worker fields."""

    # Remove columns
    op.drop_column('clients', 'worker_route_id')
    op.drop_column('clients', 'worker_deployed_at')
    op.drop_column('clients', 'worker_script_name')
    op.drop_column('clients', 'cloudflare_zone_id')
