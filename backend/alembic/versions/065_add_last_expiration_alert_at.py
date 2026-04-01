"""Add last_expiration_alert_at to tp_third_parties for email cooldown.

Revision ID: 065
Revises: 064
"""

import sqlalchemy as sa
from alembic import op

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column("last_expiration_alert_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "last_expiration_alert_at")
