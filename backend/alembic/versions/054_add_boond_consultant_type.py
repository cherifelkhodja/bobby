"""Add boond_consultant_type to cm_contract_requests.

Revision ID: 054
Revises: 053
Create Date: 2026-03-10

Distingue si le consultant du positioning est un candidat Boond (type "candidate",
endpoint /candidates/{id}) ou une ressource déjà existante (type "resource",
endpoint /resources/{id}). Cette distinction conditionne :
  - l'appel pour récupérer les infos du consultant (candidates vs resources)
  - la conversion candidate → resource lors du sync post-signature (seulement si "candidate")
"""

import sqlalchemy as sa

from alembic import op

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "boond_consultant_type",
            sa.String(20),
            nullable=True,
            comment="'candidate' ou 'resource' selon le type Boond du consultant",
        ),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "boond_consultant_type")
