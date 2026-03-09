"""Replace hard-coded GEMINI company name with {{ issuer_company_name }} tag in article templates.

Revision ID: 044
Revises: 043
Create Date: 2026-03-09
"""

from alembic import op
from sqlalchemy import text

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None

# (article_key, new_content) — "GEMINI" replaced by {{ issuer_company_name }}
UPDATES = [
    (
        "objet",
        "Le présent contrat a pour objet de définir les conditions dans lesquelles le PARTENAIRE participe à des travaux informatiques pour le compte de {{ issuer_company_name }}, auprès de la clientèle de {{ issuer_company_name }}.",
    ),
    (
        "definition_service",
        "Le service consiste à mettre à la disposition du client de {{ issuer_company_name }} un collaborateur du PARTENAIRE afin de réaliser la prestation d'assistance technique définie en annexe au présent contrat.",
    ),
    (
        "modalites_execution",
        "Le collaborateur du PARTENAIRE ne sera en aucun cas soumis à l'autorité hiérarchique de {{ issuer_company_name }} ou du client final. Il devra néanmoins se conformer au règlement intérieur du client de {{ issuer_company_name }} et exécuter la prestation qui lui a été confiée en respectant les spécifications du client et de {{ issuer_company_name }}.\n\nLe PARTENAIRE avertira directement {{ issuer_company_name }} de toutes réclamations éventuelles concernant l'exécution de la prestation.",
    ),
    (
        "resiliation",
        "Le présent contrat est résiliable par chacune des parties, notification par lettre recommandée avec accusé de réception. En cas de rupture à l'initiative de {{ issuer_company_name }}, le préavis est fixé à un mois. En cas de rupture à l'initiative du PARTENAIRE, le préavis est fixé à un mois.\n\nIl pourra toutefois prendre fin avant l'échéance fixée pour les motifs suivants :\n- Modification de planning par le client final, entraînant une baisse de charge et par conséquent une durée de mission inférieure à la durée initialement fixée,\n- Fin prématurée de la mission pour cause d'inaptitude du collaborateur du PARTENAIRE à remplir les fonctions auxquelles font appel les travaux,\n\nDans le cas où le PARTENAIRE souhaite procéder au remplacement de son intervenant, {{ issuer_company_name }} est tenu d'en avertir son client trois mois à l'avance.",
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    for article_key, new_content in UPDATES:
        conn.execute(
            text(
                "UPDATE cm_contract_article_templates"
                " SET content = :content, updated_at = NOW()"
                " WHERE article_key = :key"
            ),
            {"content": new_content, "key": article_key},
        )


def downgrade() -> None:
    pass  # No rollback — previous content had a hard-coded company name
