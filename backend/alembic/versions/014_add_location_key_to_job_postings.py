"""Add location_key column to job_postings table.

Revision ID: 014_add_location_key_to_job_postings
Revises: 013_add_turnoverit_skills_table
Create Date: 2026-01-19

This column stores the Turnover-IT location key for normalization
and consistency when publishing job postings.
The key uniquely identifies a location (e.g., "fr~ile-de-france~paris~").
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "014_add_location_key_to_job_postings"
down_revision = "013_add_turnoverit_skills_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add location_key column to job_postings table."""
    op.add_column(
        "job_postings",
        sa.Column("location_key", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    """Remove location_key column from job_postings table."""
    op.drop_column("job_postings", "location_key")
