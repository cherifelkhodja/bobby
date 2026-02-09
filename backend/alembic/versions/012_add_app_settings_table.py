"""Add app_settings table for runtime configuration.

Revision ID: 012_add_app_settings_table
Revises: 011_add_turnoverit_skills_table
Create Date: 2026-01-18

This table stores runtime application settings that can be modified
from the admin panel, like the Gemini model to use.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "012_add_app_settings_table"
down_revision = "011_add_turnoverit_skills_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create app_settings table."""
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
    )

    # Create index for fast key lookups
    op.create_index("ix_app_settings_key", "app_settings", ["key"])

    # Insert default settings
    op.execute("""
        INSERT INTO app_settings (key, value, description)
        VALUES
            ('gemini_model', 'gemini-2.0-flash', 'Modèle Gemini à utiliser pour l''anonymisation et le matching'),
            ('gemini_model_cv', 'gemini-2.0-flash', 'Modèle Gemini à utiliser pour la transformation CV')
    """)


def downgrade() -> None:
    """Drop app_settings table."""
    op.drop_index("ix_app_settings_key", table_name="app_settings")
    op.drop_table("app_settings")
