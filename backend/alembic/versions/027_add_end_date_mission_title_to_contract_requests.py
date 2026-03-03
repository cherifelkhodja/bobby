"""Add end_date and mission_title to cm_contract_requests.

Revision ID: 027_cr_end_date_title
Revises: 026_partial_uniq_pos
Create Date: 2026-03-03
"""

import sqlalchemy as sa

from alembic import op

revision = "027_cr_end_date_title"
down_revision = "026_partial_uniq_pos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cm_contract_requests", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("mission_title", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "mission_title")
    op.drop_column("cm_contract_requests", "end_date")
