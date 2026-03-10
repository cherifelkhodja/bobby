"""Add quantity_sold to cm_contract_requests.

Revision ID: 056
Revises: 055
Create Date: 2026-03-10

Nombre d'UO (Unités d'Oeuvre) vendues, récupéré depuis le webhook BoondManager
via l'attribut `quantity` du positioning.
"""

import sqlalchemy as sa

from alembic import op

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "quantity_sold",
            sa.Integer,
            nullable=True,
            comment="Nombre d'UO vendues (attribut 'quantity' du positioning Boond)",
        ),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "quantity_sold")
