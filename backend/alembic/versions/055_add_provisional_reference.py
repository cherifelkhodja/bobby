"""Add provisional_reference to cm_contract_requests and make reference nullable.

Revision ID: 055
Revises: 054
Create Date: 2026-03-10

La numérotation finale du contrat (format XXX-YYYY-NNNN, ex: GEM-2026-0001) sera
désormais assignée uniquement au moment où le partenaire approuve le contrat
(état PARTNER_APPROVED).

En attendant, une référence provisoire (format PROV-YYYY-NNNN) est générée à la
création de la demande de contrat pour servir d'identifiant interne.

Migration :
- Ajoute la colonne `provisional_reference` (VARCHAR 20, unique, NOT NULL)
- Peuple `provisional_reference` = `reference` pour tous les enregistrements existants
- Rend la colonne `reference` nullable (NULL pour les nouvelles demandes jusqu'à approbation)
"""

import sqlalchemy as sa

from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Ajouter provisional_reference comme nullable d'abord
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "provisional_reference",
            sa.String(20),
            nullable=True,
            comment="Référence provisoire générée à la création (PROV-YYYY-NNNN)",
        ),
    )

    # 2. Peupler avec la valeur actuelle de reference pour les enregistrements existants
    op.execute(
        "UPDATE cm_contract_requests SET provisional_reference = reference"
    )

    # 3. Rendre provisional_reference NOT NULL et unique
    op.alter_column("cm_contract_requests", "provisional_reference", nullable=False)
    op.create_unique_constraint(
        "uq_cm_contract_requests_provisional_reference",
        "cm_contract_requests",
        ["provisional_reference"],
    )

    # 4. Rendre reference nullable (sera NULL pour les nouvelles demandes
    #    jusqu'à l'état PARTNER_APPROVED)
    op.alter_column("cm_contract_requests", "reference", nullable=True)


def downgrade() -> None:
    # Restore reference to NOT NULL (backfill with provisional_reference)
    op.execute(
        "UPDATE cm_contract_requests SET reference = provisional_reference WHERE reference IS NULL"
    )
    op.alter_column("cm_contract_requests", "reference", nullable=False)

    # Drop provisional_reference
    op.drop_constraint(
        "uq_cm_contract_requests_provisional_reference",
        "cm_contract_requests",
        type_="unique",
    )
    op.drop_column("cm_contract_requests", "provisional_reference")
