"""Add signatory_is_director to tp_third_parties.

Revision ID: 058
Revises: 057
Create Date: 2026-03-13
"""

import sqlalchemy as sa

from alembic import op

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column(
            "signatory_is_director",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "signatory_is_director")
