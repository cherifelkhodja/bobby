"""Add consultant_scope to charter templates.

Revision ID: 070
Revises: 069
"""

import sqlalchemy as sa

from alembic import op

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_charter_templates",
        sa.Column(
            "consultant_scope",
            sa.String(20),
            nullable=False,
            server_default="all",
            comment="all, external, internal — only relevant when target=consultant",
        ),
    )


def downgrade() -> None:
    op.drop_column("cm_charter_templates", "consultant_scope")
