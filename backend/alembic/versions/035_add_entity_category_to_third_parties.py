"""Add entity_category column to tp_third_parties.

Revision ID: 035
Revises: 034
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column("entity_category", sa.String(10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "entity_category")
