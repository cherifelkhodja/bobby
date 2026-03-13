"""Add boond_contact_ids to tp_third_parties.

Revision ID: 060
Revises: 059
Create Date: 2026-03-13
"""

import sqlalchemy as sa

from alembic import op

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column("boond_signatory_contact_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tp_third_parties",
        sa.Column("boond_adv_contact_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tp_third_parties",
        sa.Column("boond_commercial_contact_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "boond_commercial_contact_id")
    op.drop_column("tp_third_parties", "boond_adv_contact_id")
    op.drop_column("tp_third_parties", "boond_signatory_contact_id")
