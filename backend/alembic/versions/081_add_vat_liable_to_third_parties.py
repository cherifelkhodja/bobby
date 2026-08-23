"""Record whether a supplier is liable for VAT.

Tous les fournisseurs ne facturent pas la TVA : franchise en base, structure
étrangère en autoliquidation. Le numéro de TVA ne dit rien de cet
assujettissement — le portail le calcule d'office depuis le SIREN quand le
tiers ne le renseigne pas —, d'où ce drapeau explicite. Il décide de ce que le
bon de commande imprime : TVA et total TTC, ou « TVA non applicable ».

Les tiers existants sont réputés assujettis, cas de loin le plus courant.

Revision ID: 081
Revises: 080
"""

import sqlalchemy as sa

from alembic import op

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tp_third_parties",
        sa.Column(
            "vat_liable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="Le tiers facture-t-il la TVA ? Faux en franchise en base ou autoliquidation.",
        ),
    )


def downgrade() -> None:
    op.drop_column("tp_third_parties", "vat_liable")
