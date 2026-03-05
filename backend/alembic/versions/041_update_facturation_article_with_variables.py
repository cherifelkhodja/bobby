"""Update facturation article content to use Jinja2 variables for payment terms.

Replaces hardcoded '30 jours fin de mois' with {{ payment_terms_display }}
so that the contract draft reflects the configured payment terms.

Revision ID: 041
Revises: 040
Create Date: 2026-03-05
"""
from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None

NEW_CONTENT = (
    "Les factures émises par le PARTENAIRE seront établies, chaque fin de mois, sur la base des rapports "
    "d'activités rédigés par le Collaborateur du PARTENAIRE qui seront rempli sur notre plateforme au plus "
    "tard le dernier jour du mois de la prestation.\n\n"
    "Les factures seront à envoyer exclusivement à l'adresse suivante factures@geminiconsulting.fr avant le "
    "5 du mois suivant la prestation pour mise en paiement dans les temps.\n\n"
    "Le règlement sera effectué {{ payment_terms_display }}, net d'agios par virement bancaire."
)

OLD_CONTENT = (
    "Les factures émises par le PARTENAIRE seront établies, chaque fin de mois, sur la base des rapports "
    "d'activités rédigés par le Collaborateur du PARTENAIRE qui seront rempli sur notre plateforme au plus "
    "tard le dernier jour du mois de la prestation.\n\n"
    "Les factures seront à envoyer exclusivement à l'adresse suivante factures@geminiconsulting.fr avant le "
    "5 du mois suivant la prestation pour mise en paiement dans les temps.\n\n"
    "Le règlement sera effectué 30 jours fin de mois, net d'agios par virement bancaire."
)


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET content = $content${NEW_CONTENT}$content$
        WHERE article_key = 'facturation'
          AND content = $old${OLD_CONTENT}$old$
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET content = $old${OLD_CONTENT}$old$
        WHERE article_key = 'facturation'
          AND content = $content${NEW_CONTENT}$content$
        """
    )
