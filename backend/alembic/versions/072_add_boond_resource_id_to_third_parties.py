"""Add boond_resource_id to third parties.

Revision ID: 072
Revises: 071
"""

import sqlalchemy as sa

from alembic import op

revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column("boond_resource_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "boond_resource_id")
