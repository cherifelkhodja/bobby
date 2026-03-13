"""Add tva_number to cm_contract_companies.

Revision ID: 059
Revises: 058
Create Date: 2026-03-13
"""

import sqlalchemy as sa

from alembic import op

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_companies",
        sa.Column("tva_number", sa.String(30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_companies", "tva_number")
