"""Add cm_contract_companies table.

Revision ID: 042
Revises: 041
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cm_contract_companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_form", sa.String(50), nullable=False),
        sa.Column("capital", sa.String(100), nullable=False),
        sa.Column("head_office", sa.String(500), nullable=False),
        sa.Column("rcs_city", sa.String(100), nullable=False),
        sa.Column("rcs_number", sa.String(50), nullable=False),
        sa.Column("representative_is_entity", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("representative_name", sa.String(255), nullable=False),
        sa.Column("representative_quality", sa.String(255), nullable=False),
        sa.Column("representative_sub_name", sa.String(255), nullable=True),
        sa.Column("representative_sub_quality", sa.String(255), nullable=True),
        sa.Column("signatory_name", sa.String(255), nullable=False),
        sa.Column("color_code", sa.String(7), nullable=False, server_default="#4BBEA8"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Add company_id FK to contract requests
    op.add_column(
        "cm_contract_requests",
        sa.Column("company_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cm_contract_requests_company_id",
        "cm_contract_requests",
        "cm_contract_companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_cm_contract_requests_company_id", "cm_contract_requests", type_="foreignkey")
    op.drop_column("cm_contract_requests", "company_id")
    op.drop_table("cm_contract_companies")
