"""Add consultant_email and consultant_phone to cm_contract_requests.

Revision ID: 052
Revises: 051
Create Date: 2026-03-10

Adds email and phone fields for the consultant (prestataire) to the
contract request, allowing the commercial to record and sync contact
details from BoondManager.
"""

from alembic import op
import sqlalchemy as sa

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_requests",
        sa.Column("consultant_email", sa.String(255), nullable=True),
    )
    op.add_column(
        "cm_contract_requests",
        sa.Column("consultant_phone", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "consultant_phone")
    op.drop_column("cm_contract_requests", "consultant_email")
