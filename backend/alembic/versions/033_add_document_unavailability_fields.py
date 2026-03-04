"""Add is_unavailable and unavailability_reason to vig_documents.

Revision ID: 033_add_doc_unavailability_fields
Revises: 032_add_doc_extraction_fields
Create Date: 2026-03-04
"""

import sqlalchemy as sa

from alembic import op

revision = "033_add_doc_unavailability_fields"
down_revision = "032_add_doc_extraction_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vig_documents",
        sa.Column("is_unavailable", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("vig_documents", sa.Column("unavailability_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("vig_documents", "unavailability_reason")
    op.drop_column("vig_documents", "is_unavailable")
