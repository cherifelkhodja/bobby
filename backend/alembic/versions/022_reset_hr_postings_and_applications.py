"""Reset all HR job postings and applications for first redeployment.

Revision ID: 022_reset_hr_data
Revises: 021_delete_all_job_postings
Create Date: 2026-02-12

One-time data migration for the HR recruitment workflow redeployment:
- Delete all job applications (FK depends on job_postings)
- Delete all job postings
- Allows a clean restart with the new BoondManager/Turnover-IT integrations
"""

import sqlalchemy as sa

from alembic import op

revision = "022_reset_hr_data"
down_revision = "021_delete_all_job_postings"
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
