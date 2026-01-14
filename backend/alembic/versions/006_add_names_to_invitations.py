"""Add first_name and last_name to invitations table.

Revision ID: 006_add_names_invitations
Revises: 005_add_phone_fields
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_names_invitations'
down_revision: Union[str, None] = '005_add_phone_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add first_name and last_name columns to invitations table
    op.add_column('invitations', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('invitations', sa.Column('last_name', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('invitations', 'last_name')
    op.drop_column('invitations', 'first_name')
