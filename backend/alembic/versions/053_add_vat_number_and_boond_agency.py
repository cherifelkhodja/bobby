"""Add vat_number to tp_third_parties and boond_agency_id to cm_contract_companies.

Revision ID: 053
Revises: 052
Create Date: 2026-03-10

- tp_third_parties.vat_number: numéro de TVA intracommunautaire du fournisseur
- cm_contract_companies.boond_agency_id: ID de l'agence Boond associée à la société émettrice
"""

from alembic import op
import sqlalchemy as sa

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column("vat_number", sa.String(50), nullable=True),
    )
    op.add_column(
        "cm_contract_companies",
        sa.Column("boond_agency_id", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_companies", "boond_agency_id")
    op.drop_column("tp_third_parties", "vat_number")
