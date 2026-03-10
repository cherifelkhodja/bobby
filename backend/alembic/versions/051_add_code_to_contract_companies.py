"""Add code field to cm_contract_companies.

Revision ID: 051
Revises: 050
Create Date: 2026-03-10

Adds a 3-letter code (e.g. "GEM") used to build contract references
in the format XXX-YYYY-NNN, with numbering independent per company.
"""

from alembic import op
import sqlalchemy as sa

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add code column with a temporary default so existing rows get a value
    op.add_column(
        "cm_contract_companies",
        sa.Column("code", sa.String(3), nullable=False, server_default="GEN"),
    )
    # Remove the server default so new rows must explicitly provide a code
    op.alter_column("cm_contract_companies", "code", server_default=None)


def downgrade() -> None:
    op.drop_column("cm_contract_companies", "code")
