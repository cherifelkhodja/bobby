"""Add view_count to job_postings table.

Revision ID: 023_add_view_count
Revises: 022_reset_hr_data
Create Date: 2026-02-12

Tracks how many times the public application page has been viewed.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "023_add_view_count"
down_revision = "022_reset_hr_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_postings",
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("job_postings", "view_count")
