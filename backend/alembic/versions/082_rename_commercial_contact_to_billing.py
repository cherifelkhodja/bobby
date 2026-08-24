"""Rename the supplier's commercial contact column to billing contact.

Bobby collecte auprès du fournisseur un **contact facturation**, poussé jusqu'ici
dans BoondManager avec le type « Commercial » (8) et rangé dans une colonne du
même nom. Le type correct est « Contact facturation » (2) ; la colonne suit, pour
que le code cesse d'appeler « commercial » une personne qui ne l'est pas.

Simple renommage : aucune donnée n'est perdue, les identifiants Boond déjà
enregistrés restent valides.

Revision ID: 082
Revises: 081
"""

from alembic import op

revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "tp_third_parties",
        "boond_commercial_contact_id",
        new_column_name="boond_billing_contact_id",
    )


def downgrade() -> None:
    op.alter_column(
        "tp_third_parties",
        "boond_billing_contact_id",
        new_column_name="boond_commercial_contact_id",
    )
