"""Add quotation templates table.

Revision ID: 007_add_quotation_templates
Revises: 006_add_names_invitations
Create Date: 2026-01-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '007_add_quotation_templates'
down_revision: Union[str, None] = '006_add_names_invitations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create quotation_templates table
    op.create_table(
        'quotation_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_content', sa.LargeBinary(), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('quotation_templates')
