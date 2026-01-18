"""Add Turnover-IT skills cache table.

Revision ID: 013_add_turnoverit_skills_table
Revises: 012_add_app_settings_table
Create Date: 2026-01-18

This table caches skills from the Turnover-IT API to avoid frequent API calls
during job posting anonymization.

Note: This is a re-creation of migration 011 which was skipped in some environments.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "013_add_turnoverit_skills_table"
down_revision = "012_add_app_settings_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create turnoverit_skills table if not exists."""
    # Check if table already exists (from migration 011)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "turnoverit_skills" not in existing_tables:
        op.create_table(
            "turnoverit_skills",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("slug", sa.String(255), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

        # Create index for fast name searches
        op.create_index("ix_turnoverit_skills_name", "turnoverit_skills", ["name"])
        op.create_index("ix_turnoverit_skills_slug", "turnoverit_skills", ["slug"])

    if "turnoverit_skills_metadata" not in existing_tables:
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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "turnoverit_skills_metadata" in existing_tables:
        op.drop_table("turnoverit_skills_metadata")

    if "turnoverit_skills" in existing_tables:
        op.drop_index("ix_turnoverit_skills_slug", table_name="turnoverit_skills")
        op.drop_index("ix_turnoverit_skills_name", table_name="turnoverit_skills")
        op.drop_table("turnoverit_skills")
