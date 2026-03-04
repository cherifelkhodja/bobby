"""Add document_date and is_valid_at_upload to vig_documents.

Revision ID: 032_add_doc_extraction_fields
Revises: 031_remove_siren_unique
Create Date: 2026-03-04
"""

import sqlalchemy as sa

from alembic import op

revision = "032_add_doc_extraction_fields"
down_revision = "031_remove_siren_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vig_documents", sa.Column("document_date", sa.Date(), nullable=True))
    op.add_column("vig_documents", sa.Column("is_valid_at_upload", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("vig_documents", "is_valid_at_upload")
    op.drop_column("vig_documents", "document_date")
