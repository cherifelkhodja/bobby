"""Reset published opportunities and cooptations data.

Revision ID: 024_reset_opps_coopts
Revises: 023_add_view_count
Create Date: 2026-02-12

One-time data migration for clean redeployment:
- Delete all cooptations (FK depends on candidates and opportunities)
- Delete all candidates (referenced by cooptations)
- Delete all published opportunities
"""

import sqlalchemy as sa

from alembic import op

revision = "024_reset_opps_coopts"
down_revision = "023_add_view_count"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete cooptations first (FK on candidates + opportunities)
    op.execute(sa.text("DELETE FROM cooptations"))
    # Then delete candidates
    op.execute(sa.text("DELETE FROM candidates"))
    # Then delete published opportunities
    op.execute(sa.text("DELETE FROM published_opportunities"))


def downgrade() -> None:
    # Data migration — cannot be reversed automatically
    pass
