"""Add invoices_company_mail to cm_contract_companies.

Revision ID: 049
Revises: 048
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_companies",
        sa.Column("invoices_company_mail", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_companies", "invoices_company_mail")
