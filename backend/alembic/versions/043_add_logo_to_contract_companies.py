"""Add logo_s3_key to cm_contract_companies.

Revision ID: 043
Revises: 042
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_companies",
        sa.Column("logo_s3_key", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_companies", "logo_s3_key")
