"""Add ape_code to tp_third_parties.

Revision ID: 057
Revises: 056
Create Date: 2026-03-13
"""

import sqlalchemy as sa

from alembic import op

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column("ape_code", sa.String(10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "ape_code")
