"""Add company_id to charter templates.

Revision ID: 068
Revises: 067
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_charter_templates",
        sa.Column("company_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cm_charter_templates_company_id",
        "cm_charter_templates",
        "cm_contract_companies",
        ["company_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_cm_charter_templates_company_id",
        "cm_charter_templates",
        ["company_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cm_charter_templates_company_id", table_name="cm_charter_templates")
    op.drop_constraint("fk_cm_charter_templates_company_id", "cm_charter_templates", type_="foreignkey")
    op.drop_column("cm_charter_templates", "company_id")
