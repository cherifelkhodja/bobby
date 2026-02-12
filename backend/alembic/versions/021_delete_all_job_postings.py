"""Delete all job postings and applications for clean restart.

Revision ID: 021_delete_all_job_postings
Revises: 020_reset_apps_revalidation
Create Date: 2026-02-12

One-time data migration:
- Delete all job applications (FK depends on job_postings)
- Delete all job postings
- Allows recreating postings from scratch
"""

import sqlalchemy as sa

from alembic import op

revision = "021_delete_all_job_postings"
down_revision = "020_reset_apps_revalidation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete applications first (FK constraint)
    op.execute(sa.text("DELETE FROM job_applications"))
    # Then delete all postings
    op.execute(sa.text("DELETE FROM job_postings"))


def downgrade() -> None:
    # Data migration — cannot be reversed automatically
    pass
