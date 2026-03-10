"""Add consultant_email and consultant_phone fields to cm_contract_requests.

Revision ID: 029_add_consultant_email_phone
Revises: 028_cr_consultant_address
Create Date: 2026-03-10
"""

import sqlalchemy as sa

from alembic import op

revision = "029_add_consultant_email_phone"
down_revision = "028_cr_consultant_address"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cm_contract_requests", sa.Column("consultant_email", sa.String(255), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("consultant_phone", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "consultant_phone")
    op.drop_column("cm_contract_requests", "consultant_email")
