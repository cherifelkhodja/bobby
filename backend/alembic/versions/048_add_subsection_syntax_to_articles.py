"""Mise à jour des articles : adoption de la syntaxe ## pour les sous-sections numérotées.

Les articles personnel, responsabilite et dispositions_generales utilisaient
'**Titre** — contenu' (bold inline). Ils passent au format '## Titre\n\ncontenu'
qui génère des sous-sections numérotées (ex: 4.1, 4.2...) dans le PDF.

Revision ID: 048
Revises: 047
Create Date: 2026-03-09
"""

from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None

PERSONNEL_CONTENT = (
    "## Indépendance\n\n"
    "Le Collaborateur reste sous la seule autorité hiérarchique du PARTENAIRE. "
    "Il se conformera au règlement intérieur et à la charte informatique du Client Final.\n\n"
    "## Compétences et validation\n\n"
    "Le PARTENAIRE fournit un Collaborateur conforme au profil décrit dans le Bon de Commande. "
    "Un entretien préalable pourra être réalisé. "
    "En cas d'inadéquation constatée dans les 10 premiers jours ouvrés, {{ issuer_company_name }} "
    "pourra exiger un remplacement sous 10 jours ouvrés, sans facturation de la période.\n\n"
    "## Remplacement\n\n"
    "En cas de départ du Collaborateur, le PARTENAIRE informe "
    "{{ issuer_company_name }} sans délai et propose un remplaçant de compétences équivalentes "
    "sous 15 jours ouvrés, soumis à validation. Le PARTENAIRE ne peut sous-traiter sans accord "
    "écrit préalable de {{ issuer_company_name }}.\n\n"
    "## Obligation de conseil\n\n"
    "Le PARTENAIRE informera, conseillera et alertera "
    "{{ issuer_company_name }} sur tout problème lié à la Prestation dans un délai de 48 heures. "
    "Il exécutera les Prestations conformément aux règles de l'art."
)

RESPONSABILITE_CONTENT = (
    "## Responsabilité\n\n"
    "Chaque Partie est responsable des dommages directs causés à l'autre. "
    "Le PARTENAIRE est responsable de son Collaborateur et de ses sous-traitants. La responsabilité "
    "totale cumulée de chaque Partie est plafonnée au montant facturé sur les 12 derniers mois. "
    "Les dommages indirects sont exclus. Ces limites ne s'appliquent pas en cas de faute "
    "lourde/dolosive, atteinte à la PI, ou violation de confidentialité.\n\n"
    "## Assurances\n\n"
    "Le PARTENAIRE déclare détenir une RC Professionnelle et une RC Exploitation "
    "auprès d'un assureur solvable. Il en justifiera sur demande."
)

DISPOSITIONS_GENERALES_CONTENT = (
    "## Force majeure\n\n"
    "Art. 1218 du Code civil. Notification sous 5 jours. Au-delà de 30 jours, "
    "résiliation sans indemnité.\n\n"
    "## Sécurité\n\n"
    "Le PARTENAIRE évitera toute introduction de virus/malware et se conformera à "
    "la législation en matière de cryptologie. Il communiquera la liste nominative du personnel "
    "intervenant sur site.\n\n"
    "## PCA\n\n"
    "Le PARTENAIRE tiendra à jour la liste de son personnel affecté avec coordonnées "
    "et prêtera assistance en cas de sinistre.\n\n"
    "## Cession\n\n"
    "Interdite sans accord écrit de {{ issuer_company_name }}. Le PARTENAIRE reste "
    "garant solidaire. Les obligations subsistent en cas de restructuration de "
    "{{ issuer_company_name }}.\n\n"
    "## Audit\n\n"
    "{{ issuer_company_name }} se réserve le droit de procéder ou faire procéder, "
    "à ses frais, à tout audit visant à vérifier le respect par le PARTENAIRE de ses obligations "
    "contractuelles (qualité des Prestations, conformité sociale, sécurité, protection des "
    "données), sur préavis raisonnable de quinze (15) jours ouvrés. Le PARTENAIRE s'engage à "
    "collaborer de bonne foi et à fournir les documents nécessaires.\n\n"
    "## Droit applicable\n\n"
    "Droit français. Résolution amiable sous 30 jours, puis Tribunal de "
    "Commerce de Paris. Nullité partielle sans effet sur le reste. Le non-exercice d'un droit ne "
    "vaut pas renonciation. Notifications par LRAR. Élection de domicile aux sièges sociaux.\n\n"
    "## Conformité sociale\n\n"
    "Le PARTENAIRE fournit à la signature puis tous les 6 mois : "
    "attestation URSSAF, Kbis, liste salariés étrangers, attestation assurance RC Pro "
    "(cf. Annexe 2)."
)


def upgrade() -> None:
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
        SET content = $responsabilite${RESPONSABILITE_CONTENT}$responsabilite$
        WHERE article_key = 'responsabilite'
        """
    )
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET content = $dispositions${DISPOSITIONS_GENERALES_CONTENT}$dispositions$
        WHERE article_key = 'dispositions_generales'
        """
    )


def downgrade() -> None:
    pass
