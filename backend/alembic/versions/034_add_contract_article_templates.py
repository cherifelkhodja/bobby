"""Add contract article templates table.

Revision ID: 034
Revises: 033
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None

DEFAULT_ARTICLES = [
    {
        "article_key": "objet",
        "article_number": 1,
        "title": "OBJET",
        "content": "Le présent contrat a pour objet de définir les conditions dans lesquelles le PARTENAIRE participe à des travaux informatiques pour le compte de GEMINI, auprès de la clientèle de GEMINI.",
        "is_editable": False,
        "is_active": True,
    },
    {
        "article_key": "definition_service",
        "article_number": 2,
        "title": "DEFINITION DU SERVICE",
        "content": "Le service consiste à mettre à la disposition du client de GEMINI un collaborateur du PARTENAIRE afin de réaliser la prestation d'assistance technique définie en annexe au présent contrat.",
        "is_editable": False,
        "is_active": True,
    },
    {
        "article_key": "modalites_execution",
        "article_number": 3,
        "title": "MODALITES D'EXECUTION DE LA SOUS TRAITANCE",
        "content": "Le collaborateur du PARTENAIRE ne sera en aucun cas soumis à l'autorité hiérarchique de GEMINI ou du client final. Il devra néanmoins se conformer au règlement intérieur du client de GEMINI et exécuter la prestation qui lui a été confiée en respectant les spécifications du client et de GEMINI.\n\nLe PARTENAIRE avertira directement GEMINI de toutes réclamations éventuelles concernant l'exécution de la prestation.",
        "is_editable": False,
        "is_active": True,
    },
    {
        "article_key": "duree",
        "article_number": 4,
        "title": "DUREE DU CONTRAT",
        "content": "La durée initiale du contrat et les modalités de reconduction figurent en annexe.",
        "is_editable": False,
        "is_active": True,
    },
    {
        "article_key": "conditions_financieres",
        "article_number": 5,
        "title": "CONDITIONS FINANCIERES",
        "content": "Les prestations fournies dans le cadre du présent contrat font l'objet d'une facturation mensuelle.\n\nLe prix unitaire par unité d'œuvre est défini dans l'annexe du présent contrat.",
        "is_editable": False,
        "is_active": True,
    },
    {
        "article_key": "facturation",
        "article_number": 6,
        "title": "FACTURATION ET CONDITIONS DE PAIEMENT",
        "content": "Les factures émises par le PARTENAIRE seront établies, chaque fin de mois, sur la base des rapports d'activités rédigés par le Collaborateur du PARTENAIRE qui seront rempli sur notre plateforme au plus tard le dernier jour du mois de la prestation.\n\nLes factures seront à envoyer exclusivement à l'adresse suivante factures@geminiconsulting.fr avant le 5 du mois suivant la prestation pour mise en paiement dans les temps.\n\nLe règlement sera effectué 30 jours fin de mois, net d'agios par virement bancaire.",
        "is_editable": True,
        "is_active": True,
    },
    {
        "article_key": "resiliation",
        "article_number": 7,
        "title": "RESILIATION",
        "content": "Le présent contrat est résiliable par chacune des parties, notification par lettre recommandée avec accusé de réception. En cas de rupture à l'initiative du GEMINI, le préavis est fixé à un mois. En cas de rupture à l'initiative du PARTENAIRE, le préavis est fixé à un mois.\n\nIl pourra toutefois prendre fin avant l'échéance fixée pour les motifs suivants :\n- Modification de planning par le client final, entraînant une baisse de charge et par conséquent une durée de mission inférieure à la durée initialement fixée,\n- Fin prématurée de la mission pour cause d'inaptitude du collaborateur du PARTENAIRE à remplir les fonctions auxquelles font appel les travaux,\n\nDans le cas où le PARTENAIRE souhaite procéder au remplacement de son intervenant, GEMINI est tenu d'en avertir son client trois mois à l'avance.",
        "is_editable": True,
        "is_active": True,
    },
    {
        "article_key": "statut_partenaire",
        "article_number": 8,
        "title": "STATUT DU PARTENAIRE",
        "content": "Le PARTENAIRE certifie être en règle vis-à-vis de l'administration fiscale et des instances sociales. Le PARTENAIRE déclare être titulaire d'une police d'assurance garantissant les conséquences pécuniaires de sa responsabilité civile au cas où elle serait engagée.\n\nToute fausse déclaration engage totalement le PARTENAIRE, socialement, fiscalement et civilement.",
        "is_editable": False,
        "is_active": True,
    },
    {
        "article_key": "litiges",
        "article_number": 9,
        "title": "LITIGES",
        "content": "Toutes difficultés relatives à l'application du présent contrat seront soumises, à défaut d'accord amiable, au Tribunal de Commerce de Paris, à qui est donnée compétence territoriale.",
        "is_editable": True,
        "is_active": True,
    },
    {
        "article_key": "indivisibilite",
        "article_number": 10,
        "title": "INDIVISIBILITE",
        "content": "Le présent contrat forme un tout indivisible avec les annexes qui y seront éventuellement intégrées. Par conséquent, toutes les clauses, charges et conditions de la présente convention demeureront inchangées en ce qu'elles ne sont pas contraires auxdites annexes.",
        "is_editable": False,
        "is_active": True,
    },
    {
        "article_key": "election_domicile",
        "article_number": 11,
        "title": "ELECTION DE DOMICILE",
        "content": "Pour l'exécution des présentes, les parties font élection de domicile en leur siège social respectif sus indiqué.",
        "is_editable": False,
        "is_active": True,
    },
]


def upgrade() -> None:
    op.create_table(
        "cm_contract_article_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("article_key", sa.String(50), nullable=False, unique=True),
        sa.Column("article_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_editable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    op.bulk_insert(
        sa.table(
            "cm_contract_article_templates",
            sa.column("article_key", sa.String),
            sa.column("article_number", sa.Integer),
            sa.column("title", sa.String),
            sa.column("content", sa.Text),
            sa.column("is_editable", sa.Boolean),
            sa.column("is_active", sa.Boolean),
        ),
        DEFAULT_ARTICLES,
    )


def downgrade() -> None:
    op.drop_table("cm_contract_article_templates")
