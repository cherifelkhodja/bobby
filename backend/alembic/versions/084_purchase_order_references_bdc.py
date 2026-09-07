"""Les références des bons de commande passent de « BC » à « BDC ».

`PROV-BC-AAAA-NNN` devient `PROV-BDC-AAAA-NNN` et `XXX-BC-NNN` devient
`XXX-BDC-NNN`, le sigle que porte l'objet partout ailleurs dans Bobby.

Les numéros existants, provisoires et définitifs, sont renommés : le rang ne
bouge pas, et la séquence de chaque société émettrice reste continue puisque
le préfixe interrogé pour attribuer le numéro suivant change avec eux. Les
clés S3 déjà posées et les titres déjà écrits dans Boond gardent l'ancien
sigle — ils ne sont pas réécrits.

Revision ID: 084
Revises: 083
"""

import sqlalchemy as sa

from alembic import op

revision = "084"
down_revision = "083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE cm_purchase_orders "
            "SET provisional_reference = replace(provisional_reference, '-BC-', '-BDC-') "
            "WHERE strpos(provisional_reference, '-BC-') > 0"
        )
    )
    op.execute(
        sa.text(
            "UPDATE cm_purchase_orders "
            "SET reference = replace(reference, '-BC-', '-BDC-') "
            "WHERE reference IS NOT NULL AND strpos(reference, '-BC-') > 0"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE cm_purchase_orders "
            "SET provisional_reference = replace(provisional_reference, '-BDC-', '-BC-') "
            "WHERE strpos(provisional_reference, '-BDC-') > 0"
        )
    )
    op.execute(
        sa.text(
            "UPDATE cm_purchase_orders "
            "SET reference = replace(reference, '-BDC-', '-BC-') "
            "WHERE reference IS NOT NULL AND strpos(reference, '-BDC-') > 0"
        )
    )
