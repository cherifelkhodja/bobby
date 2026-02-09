"""Add Turnover-IT skills cache table.

Revision ID: 011_add_turnoverit_skills_table
Revises: 010_add_row_level_security
Create Date: 2026-01-18

This table caches skills from the Turnover-IT API to avoid frequent API calls
during job posting anonymization.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "011_add_turnoverit_skills_table"
down_revision = "010_add_row_level_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create turnoverit_skills table."""
    op.create_table(
        "turnoverit_skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create index for fast name searches
    op.create_index("ix_turnoverit_skills_name", "turnoverit_skills", ["name"])
    op.create_index("ix_turnoverit_skills_slug", "turnoverit_skills", ["slug"])

    # Create metadata table to track last sync
    op.create_table(
        "turnoverit_skills_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("total_skills", sa.Integer(), default=0),
    )

    # Insert initial metadata row
    op.execute("INSERT INTO turnoverit_skills_metadata (id, total_skills) VALUES (1, 0)")


def downgrade() -> None:
    """Drop turnoverit_skills tables."""
    op.drop_table("turnoverit_skills_metadata")
    op.drop_index("ix_turnoverit_skills_slug", table_name="turnoverit_skills")
    op.drop_index("ix_turnoverit_skills_name", table_name="turnoverit_skills")
    op.drop_table("turnoverit_skills")
