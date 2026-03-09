"""Mise à jour des articles : remplacement de 'Conditions Particulières' par 'Bon de Commande (BDC)'.

Revision ID: 047
Revises: 046
Create Date: 2026-03-09
"""

from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None

DEFINITIONS_CONTENT = (
    "- **Client Final** : Client de {{ issuer_company_name }} bénéficiaire de la Prestation.\n"
    "- **Collaborateur** : Personne mise à disposition par le PARTENAIRE.\n"
    "- **Bon de Commande (BDC)** : Document signé par les Parties précisant chaque mission "
    "(collaborateur, client final, durée, tarif, lieu).\n"
    "- **Contrat** : Le présent document, ses annexes et avenants.\n"
    "- **Informations Confidentielles** : Toute information technique, commerciale, financière "
    "ou stratégique communiquée entre les Parties.\n"
    "- **Prestations** : Services d'assistance technique décrits dans le Bon de Commande.\n"
    "- **Réalisations** : Tous résultats des Prestations : code, docs, specs, livrables."
)

OBJET_CONTENT = (
    "Le Contrat référencé {{ reference }} définit les conditions générales de mise à disposition de "
    "Collaborateurs par le PARTENAIRE pour des Prestations d'assistance technique auprès de la "
    "clientèle de {{ issuer_company_name }}. Chaque mission fait l'objet d'un Bon de Commande distinct.\n\n"
    "Le Contrat comprend : Annexe 1 (Correspondants), Annexe 2 (Conformité sociale), Annexe 3 (DPA), "
    "Annexe 4 (Engagement de confidentialité). Les conditions spécifiques de chaque mission font "
    "l'objet d'un Bon de Commande numéroté séquentiellement, signé par les Parties et faisant "
    "expressément référence au présent Contrat.\n\n"
    "En cas de contradiction, le présent document prévaut sur les annexes. Les CGV du PARTENAIRE ne "
    "s'appliquent pas. Le Contrat ne peut être modifié que par avenant écrit."
)

DUREE_CONTENT = (
    "Le Contrat est conclu pour une durée indéterminée à compter de sa signature. La durée de chaque "
    "mission est fixée dans le Bon de Commande correspondant. Le renouvellement de mission nécessite un "
    "accord écrit au moins 15 jours avant l'échéance. Toute tacite reconduction est exclue."
)

PERSONNEL_CONTENT = (
    "**Indépendance** — Le Collaborateur reste sous la seule autorité hiérarchique du PARTENAIRE. "
    "Il se conformera au règlement intérieur et à la charte informatique du Client Final.\n\n"
    "**Compétences et validation** — Le PARTENAIRE fournit un Collaborateur conforme au profil "
    "décrit dans le Bon de Commande. Un entretien préalable pourra être réalisé. "
    "En cas d'inadéquation constatée dans les 10 premiers jours ouvrés, {{ issuer_company_name }} "
    "pourra exiger un remplacement sous 10 jours ouvrés, sans facturation de la période.\n\n"
    "**Remplacement** — En cas de départ du Collaborateur, le PARTENAIRE informe "
    "{{ issuer_company_name }} sans délai et propose un remplaçant de compétences équivalentes "
    "sous 15 jours ouvrés, soumis à validation. Le PARTENAIRE ne peut sous-traiter sans accord "
    "écrit préalable de {{ issuer_company_name }}.\n\n"
    "**Obligation de conseil** — Le PARTENAIRE informera, conseillera et alertera "
    "{{ issuer_company_name }} sur tout problème lié à la Prestation dans un délai de 48 heures. "
    "Il exécutera les Prestations conformément aux règles de l'art."
)

FACTURATION_CONTENT = (
    "Le TJM est défini dans le Bon de Commande, exprimé en euros HT, incluant tous les frais "
    "(déplacements IDF compris). Il est ferme et non révisable pendant chaque mission. Toute révision "
    "nécessite un avenant.\n\n"
    "Les factures sont établies mensuellement sur base des CRA validés par {{ issuer_company_name }}, "
    "envoyées à {{ invoice_email }} avant le 5 du mois suivant. Paiement : {{ payment_terms_display }}, "
    "{{ invoice_submission_method_display }}. En cas de retard : intérêts à 3× le taux légal. "
    "Conformément à l'article D.441-5 du Code de commerce, une indemnité forfaitaire de 40 euros pour "
    "frais de recouvrement sera due de plein droit. Contestation sous 15 jours ; la partie non "
    "contestée est réglée normalement."
)


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET content = $definitions${DEFINITIONS_CONTENT}$definitions$
        WHERE article_key = 'definitions'
        """
    )
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET content = $objet${OBJET_CONTENT}$objet$
        WHERE article_key = 'objet'
        """
    )
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET content = $duree${DUREE_CONTENT}$duree$
        WHERE article_key = 'duree'
        """
    )
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET content = $personnel${PERSONNEL_CONTENT}$personnel$
        WHERE article_key = 'personnel'
        """
    )
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET content = $facturation${FACTURATION_CONTENT}$facturation$
        WHERE article_key = 'facturation'
        """
    )


def downgrade() -> None:
    pass
