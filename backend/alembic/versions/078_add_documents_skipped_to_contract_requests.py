"""Add documents_skipped to contract requests.

Marks a contract request whose vigilance document collection was deliberately
skipped by the ADV (fully manual / in-person entry, no fournisseur solicited).

Revision ID: 078
Revises: 077
"""

import sqlalchemy as sa

from alembic import op

revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "documents_skipped",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="Dépôt des documents de vigilance volontairement ignoré (saisie manuelle ADV)",
        ),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "documents_skipped")
