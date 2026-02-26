"""Add partial unique index on cooptations (positionings).

Revision ID: 026_partial_uniq_pos
Revises: 024_reset_opps_coopts
Create Date: 2026-02-26

NOTE: This migration was applied directly on production but the file
was never committed. Re-created as a placeholder so Alembic can locate
the revision. The upgrade/downgrade are no-ops since the changes
already exist in the database.
"""

revision = "026_partial_uniq_pos"
down_revision = "024_reset_opps_coopts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Already applied on production — no-op placeholder
    pass


def downgrade() -> None:
    pass
