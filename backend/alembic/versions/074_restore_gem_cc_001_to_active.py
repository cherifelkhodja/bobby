"""Data fix: restore GEM-CC-001 to active status.

Revision ID: 074
Revises: 073
"""

import sqlalchemy as sa

from alembic import op

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        UPDATE cm_contract_requests
        SET status = 'active'
        WHERE reference = 'GEM-CC-001'
        AND status = 'archived'
    """))


def downgrade() -> None:
    pass
