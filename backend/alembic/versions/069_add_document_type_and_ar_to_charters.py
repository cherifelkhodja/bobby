"""Add document_type, requires_acknowledgement, ar fields to charter templates.

Revision ID: 069
Revises: 068
"""

import sqlalchemy as sa

from alembic import op

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_charter_templates",
        sa.Column("document_type", sa.String(30), nullable=False, server_default="charte"),
    )
    op.add_column(
        "cm_charter_templates",
        sa.Column("requires_acknowledgement", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "cm_charter_templates",
        sa.Column("ar_file_s3_key", sa.String(500), nullable=True),
    )
    op.add_column(
        "cm_charter_templates",
        sa.Column("ar_file_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cm_charter_templates", "ar_file_name")
    op.drop_column("cm_charter_templates", "ar_file_s3_key")
    op.drop_column("cm_charter_templates", "requires_acknowledgement")
    op.drop_column("cm_charter_templates", "document_type")
