"""Add published_opportunities table for anonymized opportunities.

Revision ID: 008_add_published_opportunities
Revises: 007_add_quotation_templates
Create Date: 2026-01-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY


# revision identifiers, used by Alembic.
revision: str = '008_add_published_opportunities'
down_revision: Union[str, None] = '007_add_quotation_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'published_opportunities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('boond_opportunity_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('skills', ARRAY(sa.String(100)), nullable=True),
        sa.Column('original_title', sa.String(255), nullable=True),
        sa.Column('original_data', sa.JSON(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='published', index=True),
        sa.Column('published_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('published_opportunities')
