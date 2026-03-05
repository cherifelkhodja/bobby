"""Add individual address fields to tp_third_parties for draft save.

Revision ID: 036
Revises: 035
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa

revision = "036"
down_revision = "035_add_entity_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tp_third_parties", sa.Column("head_office_street", sa.Text(), nullable=True))
    op.add_column(
        "tp_third_parties",
        sa.Column("head_office_postal_code", sa.String(10), nullable=True),
    )
    op.add_column(
        "tp_third_parties",
        sa.Column("head_office_city", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "head_office_city")
    op.drop_column("tp_third_parties", "head_office_postal_code")
    op.drop_column("tp_third_parties", "head_office_street")
