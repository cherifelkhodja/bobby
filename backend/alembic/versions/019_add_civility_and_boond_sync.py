"""Add civility and Boond sync tracking fields to job_applications.

Revision ID: 019
Revises: 018
Create Date: 2026-02-09

Changes:
- Add civility field (M/Mme) for BoondManager candidate creation
- Add boond_sync_error field to track auto-sync failures
- Add boond_synced_at field to track successful sync timestamp
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_applications",
        sa.Column("civility", sa.String(10), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("boond_sync_error", sa.Text, nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("boond_synced_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_applications", "boond_synced_at")
    op.drop_column("job_applications", "boond_sync_error")
    op.drop_column("job_applications", "civility")
