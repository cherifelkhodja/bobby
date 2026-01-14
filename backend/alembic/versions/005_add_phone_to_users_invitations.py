"""Add phone field to users and invitations tables.

Revision ID: 005_add_phone_fields
Revises: 004_add_cv_transformer_tables
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_phone_fields'
down_revision: Union[str, None] = '004_add_cv_transformer_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add phone column to users table
    op.add_column('users', sa.Column('phone', sa.String(30), nullable=True))

    # Add phone column to invitations table
    op.add_column('invitations', sa.Column('phone', sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column('invitations', 'phone')
    op.drop_column('users', 'phone')
