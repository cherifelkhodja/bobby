"""Add contract annex templates table.

Crée la table cm_contract_annex_templates (miroir de cm_contract_article_templates)
et insère les 6 annexes du contrat-cadre :
  1. Correspondants
  2. Conformité sociale
  3. DPA (accord de traitement des données)
  4. Engagement de confidentialité
  5. Tacite reconduction (conditionnelle)
  6. Conditions spéciales (conditionnelle)

Revision ID: 046
Revises: 045
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None

# ── Annexe content strings ────────────────────────────────────────────────────

CORRESPONDANTS_CONTENT = (
    "| | {{ issuer_company_name }} | {{ partner_company_name }} |\n"
    "|---|---|---|\n"
    "| Nom | À compléter | À compléter |\n"
    "| Téléphone | À compléter | À compléter |\n"
    "| Email | À compléter | À compléter |"
)

CONFORMITE_SOCIALE_CONTENT = (
    "Documents à fournir par {{ partner_company_name }} à la signature puis tous les 6 mois "
    "(art. D.8222-5 C. travail) :\n\n"
    "- Attestation URSSAF de vigilance en cours de validité\n"
    "- Extrait Kbis de moins de 3 mois\n"
    "- Liste des salariés étrangers (le cas échéant)\n"
    "- Attestation de régularité fiscale et sociale\n"
    "- Attestation d'assurance RC Professionnelle en cours de validité"
)

DPA_CONTENT = (
    "{{ partner_company_name }} (« Sous-traitant » RGPD) traite les Données Personnelles pour le compte "
    "de {{ issuer_company_name }} (« Responsable de traitement ») aux conditions suivantes :\n\n"
    "| Rubrique | Détails |\n"
    "|---|---|\n"
    "| Finalité(s) | À décrire par mission |\n"
    "| Nature des opérations | Collecte, modification, consultation, etc. |\n"
    "| Catégories de données | Identification, coordonnées, professionnel, etc. |\n"
    "| Personnes concernées | Clients, salariés, prospects |\n"
    "| Durée de conservation | Durée de la mission + 12 mois |\n"
    "| Localisation | France / UE |\n\n"
    "**Obligations du Sous-traitant** : traitement sur instruction documentée uniquement, "
    "confidentialité, mesures de sécurité appropriées, notification de violation sous 24h, "
    "assistance aux droits des personnes concernées, destruction ou restitution des données en "
    "fin de mission, tenue d'un registre des traitements, coopération en cas d'audit."
)

ENGAGEMENT_CONTENT = (
    "*(Modèle — à signer par chaque Collaborateur avant le début de mission)*\n\n"
    "Je soussigné(e) {{ consultant_first_name }} {{ consultant_last_name }}, collaborateur de "
    "{{ partner_company_name }}, intervenant pour {{ issuer_company_name }} dans le cadre de la "
    "mission « {{ mission_title }} », m'engage à :\n\n"
    "- Garder strictement confidentielles toutes les informations accessibles dans le cadre de ma mission ;\n"
    "- Ne les divulguer à aucun tiers, que ce soit pendant ou après la mission ;\n"
    "- Ne pas les utiliser à des fins personnelles ou au profit de tiers ;\n"
    "- Restituer tous documents, supports et copies à la fin de la mission ;\n"
    "- Respecter les règles de sécurité informatique du Client Final.\n\n"
    "Cet engagement survit 5 ans après la fin de la mission. "
    "Toute violation engage ma responsabilité civile et/ou pénale.\n\n"
    "Fait à __________, le __________\n\n"
    "Signature précédée de la mention « Lu et approuvé » :"
)

TACITE_CONTENT = (
    "Par dérogation à l'article 3, les missions régies par un Bon de Commande mentionnant une tacite "
    "reconduction seront automatiquement renouvelées pour des périodes successives de "
    "{{ tacit_renewal_months }} mois, sauf dénonciation par l'une ou l'autre des Parties adressée "
    "par LRAR au moins 30 jours avant l'échéance de la période en cours."
)

CONDITIONS_SPECIALES_CONTENT = "{{ special_conditions }}"

DEFAULT_ANNEXES = [
    {
        "annexe_key": "correspondants",
        "annexe_number": 1,
        "title": "CORRESPONDANTS",
        "content": CORRESPONDANTS_CONTENT,
        "is_conditional": False,
        "condition_field": None,
        "is_active": True,
    },
    {
        "annexe_key": "conformite_sociale",
        "annexe_number": 2,
        "title": "CONFORMITÉ SOCIALE",
        "content": CONFORMITE_SOCIALE_CONTENT,
        "is_conditional": False,
        "condition_field": None,
        "is_active": True,
    },
    {
        "annexe_key": "dpa",
        "annexe_number": 3,
        "title": "DPA — ACCORD DE TRAITEMENT DES DONNÉES",
        "content": DPA_CONTENT,
        "is_conditional": False,
        "condition_field": None,
        "is_active": True,
    },
    {
        "annexe_key": "engagement_confidentialite",
        "annexe_number": 4,
        "title": "ENGAGEMENT DE CONFIDENTIALITÉ",
        "content": ENGAGEMENT_CONTENT,
        "is_conditional": False,
        "condition_field": None,
        "is_active": True,
    },
    {
        "annexe_key": "tacite_reconduction",
        "annexe_number": 5,
        "title": "TACITE RECONDUCTION",
        "content": TACITE_CONTENT,
        "is_conditional": True,
        "condition_field": "tacit_renewal_months",
        "is_active": True,
    },
    {
        "annexe_key": "conditions_speciales",
        "annexe_number": 6,
        "title": "CONDITIONS SPÉCIALES",
        "content": CONDITIONS_SPECIALES_CONTENT,
        "is_conditional": True,
        "condition_field": "special_conditions",
        "is_active": True,
    },
]


def upgrade() -> None:
    op.create_table(
        "cm_contract_annex_templates",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("annexe_key", sa.String(50), nullable=False, unique=True),
        sa.Column("annexe_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        # is_conditional: True = include only when condition_field is non-empty in contract config
        sa.Column("is_conditional", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("condition_field", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )

    op.bulk_insert(
        sa.table(
            "cm_contract_annex_templates",
            sa.column("annexe_key", sa.String),
            sa.column("annexe_number", sa.Integer),
            sa.column("title", sa.String),
            sa.column("content", sa.Text),
            sa.column("is_conditional", sa.Boolean),
            sa.column("condition_field", sa.String),
            sa.column("is_active", sa.Boolean),
        ),
        DEFAULT_ANNEXES,
    )


def downgrade() -> None:
    op.drop_table("cm_contract_annex_templates")
