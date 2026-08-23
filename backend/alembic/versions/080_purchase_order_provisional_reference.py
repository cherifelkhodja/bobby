"""Give purchase orders a provisional reference until they are validated.

Un bon de commande reçoit `XXX-BC-NNN` au moment où son document est généré :
c'est là que le numéro devient définitif et s'imprime. Avant cela, il porte une
référence provisoire `PROV-BC-YYYY-NNN`, de sorte qu'un brouillon abandonné ne
consomme pas un numéro de la séquence — que le contrat cadre exige séquentielle.

Les bons de commande existants gardent leur numéro et reçoivent la même valeur
en référence provisoire : ils étaient déjà numérotés.

Revision ID: 080
Revises: 079
"""

import sqlalchemy as sa

from alembic import op

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_purchase_orders",
        sa.Column(
            "provisional_reference",
            sa.String(20),
            nullable=True,
            comment="Référence provisoire (PROV-BC-YYYY-NNN), assignée à la création",
        ),
    )
    # Les lignes existantes sont déjà numérotées : leur référence tient lieu de
    # provisoire, ce qui préserve l'unicité de la nouvelle colonne.
    op.execute(
        "UPDATE cm_purchase_orders SET provisional_reference = reference "
        "WHERE provisional_reference IS NULL"
    )
    op.alter_column("cm_purchase_orders", "provisional_reference", nullable=False)
    op.create_unique_constraint(
        "uq_cm_purchase_orders_provisional_reference",
        "cm_purchase_orders",
        ["provisional_reference"],
    )

    # La référence définitive n'existe qu'à partir de la génération du document.
    op.alter_column("cm_purchase_orders", "reference", nullable=True)


def downgrade() -> None:
    # Un bon de commande jamais généré n'a pas de référence définitive : on lui
    # rend sa provisoire pour pouvoir remettre la contrainte NOT NULL.
    op.execute(
        "UPDATE cm_purchase_orders SET reference = provisional_reference WHERE reference IS NULL"
    )
    op.alter_column("cm_purchase_orders", "reference", nullable=False)
    op.drop_constraint(
        "uq_cm_purchase_orders_provisional_reference",
        "cm_purchase_orders",
        type_="unique",
    )
    op.drop_column("cm_purchase_orders", "provisional_reference")
