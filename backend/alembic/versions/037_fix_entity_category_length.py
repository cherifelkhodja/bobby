"""Increase entity_category column length to 20 (portage_salarial = 16 chars).

Revision ID: 037
Revises: 036
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "tp_third_parties",
        "entity_category",
        type_=sa.String(20),
        existing_type=sa.String(10),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "tp_third_parties",
        "entity_category",
        type_=sa.String(10),
        existing_type=sa.String(20),
        nullable=True,
    )
