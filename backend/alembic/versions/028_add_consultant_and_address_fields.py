"""Add consultant info and mission address fields, drop mission_location.

Revision ID: 028_cr_consultant_address
Revises: 027_cr_end_date_title
Create Date: 2026-03-03
"""

import sqlalchemy as sa

from alembic import op

revision = "028_cr_consultant_address"
down_revision = "027_cr_end_date_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Consultant info (from Boond positioning candidate)
    op.add_column("cm_contract_requests", sa.Column("consultant_civility", sa.String(10), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("consultant_first_name", sa.String(255), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("consultant_last_name", sa.String(255), nullable=True))

    # Mission address (replaces mission_location)
    op.add_column("cm_contract_requests", sa.Column("mission_site_name", sa.String(255), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("mission_address", sa.String(500), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("mission_postal_code", sa.String(10), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("mission_city", sa.String(255), nullable=True))

    # Drop old location field
    op.drop_column("cm_contract_requests", "mission_location")


def downgrade() -> None:
    op.add_column("cm_contract_requests", sa.Column("mission_location", sa.Text(), nullable=True))

    op.drop_column("cm_contract_requests", "mission_city")
    op.drop_column("cm_contract_requests", "mission_postal_code")
    op.drop_column("cm_contract_requests", "mission_address")
    op.drop_column("cm_contract_requests", "mission_site_name")
    op.drop_column("cm_contract_requests", "consultant_last_name")
    op.drop_column("cm_contract_requests", "consultant_first_name")
    op.drop_column("cm_contract_requests", "consultant_civility")
