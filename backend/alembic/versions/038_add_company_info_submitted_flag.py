"""Add company_info_submitted flag to tp_third_parties.

Distinguish between draft save (PATCH) and full submission (POST).

Revision ID: 038
Revises: 037
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column("company_info_submitted", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "company_info_submitted")
