"""Remember the Boond project a purchase order's mission belongs to.

Le projet est la seule voie vers la prestation : un positionnement n'expose
aucune relation `delivery`, et c'est l'onglet des prestations du projet qui la
rend. L'achat fournisseur s'y rattache aussi — son corps porte le projet autant
que la prestation.

Boond le remplit au passage du positionnement à « Gagné ». Le retenir permet de
reprendre un report interrompu sans redemander au CRM par où passer.

Revision ID: 083
Revises: 082
"""

import sqlalchemy as sa

from alembic import op

revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_purchase_orders",
        sa.Column(
            "boond_project_id",
            sa.Integer(),
            nullable=True,
            comment="Projet Boond : par lui se retrouve la prestation, et l'achat s'y rattache",
        ),
    )


def downgrade() -> None:
    op.drop_column("cm_purchase_orders", "boond_project_id")
