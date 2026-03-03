"""Add consultant and mission address fields to cm_contract_requests.

Revision ID: 028_cr_consultant_addr
Revises: 027_cr_end_date_title
Create Date: 2026-03-03
"""

import sqlalchemy as sa

from alembic import op

revision = "028_cr_consultant_addr"
down_revision = "027_cr_end_date_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cm_contract_requests", sa.Column("consultant_civility", sa.String(10), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("consultant_first_name", sa.String(255), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("consultant_last_name", sa.String(255), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("mission_site_name", sa.String(255), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("mission_address", sa.String(500), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("mission_postal_code", sa.String(10), nullable=True))
    op.add_column("cm_contract_requests", sa.Column("mission_city", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "mission_city")
    op.drop_column("cm_contract_requests", "mission_postal_code")
    op.drop_column("cm_contract_requests", "mission_address")
    op.drop_column("cm_contract_requests", "mission_site_name")
    op.drop_column("cm_contract_requests", "consultant_last_name")
    op.drop_column("cm_contract_requests", "consultant_first_name")
    op.drop_column("cm_contract_requests", "consultant_civility")
