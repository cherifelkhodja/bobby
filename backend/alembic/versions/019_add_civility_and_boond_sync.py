"""Add civility and Boond sync tracking fields to job_applications.

Revision ID: 019_add_civility_and_boond_sync
Revises: 018_simplify_application_status
Create Date: 2026-02-09

Changes:
- Add civility field (M/Mme) to job_applications
- Add boond_sync_error field for tracking sync failures
- Add boond_synced_at timestamp for last sync
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "019_add_civility_and_boond_sync"
down_revision = "018_simplify_application_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add civility and Boond sync tracking columns."""
    op.add_column(
        "job_applications",
        sa.Column("civility", sa.String(10), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("boond_sync_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("boond_synced_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Remove civility and Boond sync tracking columns."""
    op.drop_column("job_applications", "boond_synced_at")
    op.drop_column("job_applications", "boond_sync_error")
    op.drop_column("job_applications", "civility")
