"""Add boond_resource_id and manager_boond_id to invitations

Revision ID: 003_add_inv_boond_ids
Revises: 002_add_roles_invites
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_add_inv_boond_ids'
down_revision: Union[str, None] = '002_add_roles_invites'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add boond_resource_id and manager_boond_id to invitations table
    op.add_column('invitations', sa.Column('boond_resource_id', sa.String(50), nullable=True))
    op.add_column('invitations', sa.Column('manager_boond_id', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('invitations', 'manager_boond_id')
    op.drop_column('invitations', 'boond_resource_id')
