"""Refonte complète des articles du contrat.

Supprime les 7 anciens articles génériques et les remplace par
13 articles juridiquement structurés (préambule, définitions, objet,
durée, personnel, conditions financières, confidentialité, PI,
responsabilité, RGPD, résiliation, non-sollicitation,
dispositions générales).

Revision ID: 045
Revises: 044
Create Date: 2026-03-09
"""

from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None

# ── Keys to delete ──────────────────────────────────────────────────────────
DELETED_KEYS = [
    "definition_service",
    "modalites_execution",
    "conditions_financieres",
    "statut_partenaire",
    "litiges",
    "indivisibilite",
    "election_domicile",
]

# ── New articles (INSERT) ────────────────────────────────────────────────────
NEW_ARTICLES = [
    {
        "article_key": "preambule",
        "title": "PRÉAMBULE",
        "is_editable": False,
        "content": (
            "{{ issuer_company_name }} souhaite confier au PARTENAIRE des prestations d'assistance "
            "technique informatique au bénéfice de ses clients. Le PARTENAIRE déclare disposer des "
            "compétences et moyens requis. Les termes avec majuscule ont le sens de l'article 1."
        ),
    },
    {
        "article_key": "definitions",
        "title": "DÉFINITIONS",
        "is_editable": False,
        "content": (
            "- **Client Final** : Client de {{ issuer_company_name }} bénéficiaire de la Prestation.\n"
            "- **Collaborateur** : Personne mise à disposition par le PARTENAIRE.\n"
            "- **Conditions Particulières** : Bon de Commande précisant chaque mission (collaborateur, "
            "client, durée, tarif).\n"
            "- **Contrat** : Le présent document, ses annexes et avenants.\n"
            "- **Informations Confidentielles** : Toute information technique, commerciale, financière "
            "ou stratégique communiquée entre les Parties.\n"
            "- **Prestations** : Services d'assistance technique décrits dans les Conditions Particulières.\n"
            "- **Réalisations** : Tous résultats des Prestations : code, docs, specs, livrables."
        ),
    },
    {
        "article_key": "personnel",
        "title": "PERSONNEL ET EXÉCUTION",
        "is_editable": False,
        "content": (
            "**Indépendance** — Le Collaborateur reste sous la seule autorité hiérarchique du PARTENAIRE. "
            "Il se conformera au règlement intérieur et à la charte informatique du Client Final.\n\n"
            "**Compétences et validation** — Le PARTENAIRE fournit un Collaborateur conforme au profil "
            "décrit dans les Conditions Particulières. Un entretien préalable pourra être réalisé. "
            "En cas d'inadéquation constatée dans les 10 premiers jours ouvrés, {{ issuer_company_name }} "
            "pourra exiger un remplacement sous 10 jours ouvrés, sans facturation de la période.\n\n"
            "**Remplacement** — En cas de départ du Collaborateur, le PARTENAIRE informe "
            "{{ issuer_company_name }} sans délai et propose un remplaçant de compétences équivalentes "
            "sous 15 jours ouvrés, soumis à validation. Le PARTENAIRE ne peut sous-traiter sans accord "
            "écrit préalable de {{ issuer_company_name }}.\n\n"
            "**Obligation de conseil** — Le PARTENAIRE informera, conseillera et alertera "
            "{{ issuer_company_name }} sur tout problème lié à la Prestation dans un délai de 48 heures. "
            "Il exécutera les Prestations conformément aux règles de l'art."
        ),
    },
    {
        "article_key": "confidentialite",
        "title": "CONFIDENTIALITÉ",
        "is_editable": False,
        "content": (
            "Chaque Partie s'engage à garder strictement confidentielles toutes les Informations "
            "Confidentielles de l'autre Partie, à ne les communiquer qu'aux fins du Contrat, et à ne "
            "pas les exploiter à d'autres fins. Le PARTENAIRE fera signer un engagement individuel de "
            "confidentialité (Annexe 4) à chaque Collaborateur avant le début de mission, copie remise "
            "à {{ issuer_company_name }}.\n\n"
            "Exceptions : informations déjà publiques, communication légale, obtention légitime d'un "
            "tiers non lié par confidentialité. Cette obligation survit 5 ans après la fin du Contrat. "
            "Le PARTENAIRE se porte fort du respect par son personnel et sous-traitants."
        ),
    },
    {
        "article_key": "propriete_intellectuelle",
        "title": "PROPRIÉTÉ INTELLECTUELLE",
        "is_editable": False,
        "content": (
            "Le PARTENAIRE cède à {{ issuer_company_name }}, au fur et à mesure, à titre exclusif, "
            "tous les droits de PI sur les Réalisations (reproduction, adaptation, représentation, "
            "portage, exploitation commerciale), pour le monde entier et toute la durée de protection "
            "légale. Cette cession est incluse dans le prix.\n\n"
            "Le PARTENAIRE reste propriétaire de ses outils préexistants, dont il concède une licence "
            "non exclusive, perpétuelle et irrévocable à {{ issuer_company_name }} en cas d'utilisation "
            "dans les Réalisations.\n\n"
            "Le PARTENAIRE garantit {{ issuer_company_name }} contre toute réclamation de tiers "
            "(contrefaçon, concurrence déloyale) et remettra les codes sources sur demande. En cas "
            "d'invention brevetable, {{ issuer_company_name }} décide du dépôt. Cet article survit au Contrat."
        ),
    },
    {
        "article_key": "responsabilite",
        "title": "RESPONSABILITÉ ET ASSURANCES",
        "is_editable": True,
        "content": (
            "**Responsabilité** — Chaque Partie est responsable des dommages directs causés à l'autre. "
            "Le PARTENAIRE est responsable de son Collaborateur et de ses sous-traitants. La responsabilité "
            "totale cumulée de chaque Partie est plafonnée au montant facturé sur les 12 derniers mois. "
            "Les dommages indirects sont exclus. Ces limites ne s'appliquent pas en cas de faute "
            "lourde/dolosive, atteinte à la PI, ou violation de confidentialité.\n\n"
            "**Assurances** — Le PARTENAIRE déclare détenir une RC Professionnelle et une RC Exploitation "
            "auprès d'un assureur solvable. Il en justifiera sur demande."
        ),
    },
    {
        "article_key": "rgpd",
        "title": "PROTECTION DES DONNÉES PERSONNELLES",
        "is_editable": False,
        "content": (
            "Les Parties respectent le RGPD et la loi Informatique et Libertés. Si la Prestation implique "
            "un traitement de données personnelles, les conditions sont définies en Annexe 3 (DPA). "
            "Le PARTENAIRE agit en sous-traitant RGPD : traitement sur instruction uniquement, "
            "confidentialité, notification de violation sous 24h, assistance aux droits des personnes, "
            "destruction/restitution en fin de mission, possibilité d'audit."
        ),
    },
    {
        "article_key": "non_sollicitation",
        "title": "NON-SOLLICITATION",
        "is_editable": True,
        "content": (
            "Pendant le Contrat + 6 mois, le PARTENAIRE s'interdit de proposer directement au Client "
            "Final les services du Collaborateur sans passer par {{ issuer_company_name }}. "
            "Réciproquement, {{ issuer_company_name }} s'interdit de recruter le Collaborateur sans "
            "accord du PARTENAIRE. Pénalité : 12 mois de TJM moyen."
        ),
    },
    {
        "article_key": "dispositions_generales",
        "title": "DISPOSITIONS GÉNÉRALES",
        "is_editable": False,
        "content": (
            "**Force majeure** — Art. 1218 du Code civil. Notification sous 5 jours. Au-delà de 30 jours, "
            "résiliation sans indemnité.\n\n"
            "**Sécurité** — Le PARTENAIRE évitera toute introduction de virus/malware et se conformera à "
            "la législation en matière de cryptologie. Il communiquera la liste nominative du personnel "
            "intervenant sur site.\n\n"
            "**PCA** — Le PARTENAIRE tiendra à jour la liste de son personnel affecté avec coordonnées "
            "et prêtera assistance en cas de sinistre.\n\n"
            "**Cession** — Interdite sans accord écrit de {{ issuer_company_name }}. Le PARTENAIRE reste "
            "garant solidaire. Les obligations subsistent en cas de restructuration de "
            "{{ issuer_company_name }}.\n\n"
            "**Audit** — {{ issuer_company_name }} se réserve le droit de procéder ou faire procéder, "
            "à ses frais, à tout audit visant à vérifier le respect par le PARTENAIRE de ses obligations "
            "contractuelles (qualité des Prestations, conformité sociale, sécurité, protection des "
            "données), sur préavis raisonnable de quinze (15) jours ouvrés. Le PARTENAIRE s'engage à "
            "collaborer de bonne foi et à fournir les documents nécessaires.\n\n"
            "**Droit applicable** — Droit français. Résolution amiable sous 30 jours, puis Tribunal de "
            "Commerce de Paris. Nullité partielle sans effet sur le reste. Le non-exercice d'un droit ne "
            "vaut pas renonciation. Notifications par LRAR. Élection de domicile aux sièges sociaux.\n\n"
            "**Conformité sociale** — Le PARTENAIRE fournit à la signature puis tous les 6 mois : "
            "attestation URSSAF, Kbis, liste salariés étrangers, attestation assurance RC Pro "
            "(cf. Annexe 2)."
        ),
    },
]

# Final ordered sequence of all 13 article_keys (determines article_number)
ORDERED_KEYS = [
    "preambule",          # 1
    "definitions",        # 2
    "objet",              # 3
    "duree",              # 4
    "personnel",          # 5
    "facturation",        # 6
    "confidentialite",    # 7
    "propriete_intellectuelle",  # 8
    "responsabilite",     # 9
    "rgpd",               # 10
    "resiliation",        # 11
    "non_sollicitation",  # 12
    "dispositions_generales",    # 13
]

OBJET_CONTENT = (
    "Le Contrat référencé {{ reference }} définit les conditions générales de mise à disposition de "
    "Collaborateurs par le PARTENAIRE pour des Prestations d'assistance technique auprès de la "
    "clientèle de {{ issuer_company_name }}. Chaque mission fait l'objet de Conditions Particulières.\n\n"
    "Le Contrat comprend : Annexe 1 (Correspondants), Annexe 2 (Conformité sociale), Annexe 3 (DPA), "
    "Annexe 4 (Engagement de confidentialité). Les conditions spécifiques de chaque mission font "
    "l'objet d'un Bon de Commande distinct, numéroté séquentiellement, signé par les Parties et "
    "faisant expressément référence au présent Contrat.\n\n"
    "En cas de contradiction, le présent document prévaut sur les annexes. Les CGV du PARTENAIRE ne "
    "s'appliquent pas. Le Contrat ne peut être modifié que par avenant écrit."
)

DUREE_CONTENT = (
    "Le Contrat est conclu pour une durée indéterminée à compter de sa signature. La durée de chaque "
    "mission est fixée dans les Conditions Particulières. Le renouvellement de mission nécessite un "
    "accord écrit au moins 15 jours avant l'échéance. Toute tacite reconduction est exclue."
)

FACTURATION_CONTENT = (
    "Le TJM est défini dans les Conditions Particulières, exprimé en euros HT, incluant tous les frais "
    "(déplacements IDF compris). Il est ferme et non révisable pendant chaque mission. Toute révision "
    "nécessite un avenant.\n\n"
    "Les factures sont établies mensuellement sur base des CRA validés par {{ issuer_company_name }}, "
    "envoyées à {{ invoice_email }} avant le 5 du mois suivant. Paiement : {{ payment_terms_display }}, "
    "{{ invoice_submission_method_display }}. En cas de retard : intérêts à 3× le taux légal. "
    "Conformément à l'article D.441-5 du Code de commerce, une indemnité forfaitaire de 40 euros pour "
    "frais de recouvrement sera due de plein droit. Contestation sous 15 jours ; la partie non "
    "contestée est réglée normalement."
)

RESILIATION_CONTENT = (
    "Résiliation pour convenance par LRAR : préavis d'1 mois (initiative {{ issuer_company_name }}) "
    "ou 3 mois (initiative PARTENAIRE).\n\n"
    "Résiliation pour manquement : mise en demeure par LRAR, délai de 15 jours, puis résiliation de "
    "plein droit. Constituent un manquement grave : violation de confidentialité, défaut de conformité "
    "sociale, abandon sans remplacement.\n\n"
    "Résiliation de plein droit sans préavis : procédure collective, faute lourde/dolosive, changement "
    "de contrôle non accepté (le contrôle désigne la détention directe/indirecte de >50 % des droits "
    "de vote).\n\n"
    "Effets : restitution des Réalisations en l'état, paiement du réalisé, restitution des badges et matériels."
)


def upgrade() -> None:
    # 1. Delete removed articles
    keys_list = ", ".join(f"'{k}'" for k in DELETED_KEYS)
    op.execute(
        f"DELETE FROM cm_contract_article_templates WHERE article_key IN ({keys_list})"
    )

    # 2. Update existing articles (objet, duree, facturation, resiliation)
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET title = 'OBJET ET DOCUMENTS CONTRACTUELS',
            is_editable = false,
            content = $objet${OBJET_CONTENT}$objet$
        WHERE article_key = 'objet'
        """
    )
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET title = 'DURÉE',
            is_editable = true,
            content = $duree${DUREE_CONTENT}$duree$
        WHERE article_key = 'duree'
        """
    )
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET title = 'CONDITIONS FINANCIÈRES',
            is_editable = true,
            content = $facturation${FACTURATION_CONTENT}$facturation$
        WHERE article_key = 'facturation'
        """
    )
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET title = 'RÉSILIATION',
            is_editable = true,
            content = $resiliation${RESILIATION_CONTENT}$resiliation$
        WHERE article_key = 'resiliation'
        """
    )

    # 3. Insert new articles (temporary article_number 999, reordered below)
    import sqlalchemy as sa

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
        [
            {
                "article_key": a["article_key"],
                "article_number": 999,
                "title": a["title"],
                "content": a["content"],
                "is_editable": a["is_editable"],
                "is_active": True,
            }
            for a in NEW_ARTICLES
        ],
    )

    # 4. Reorder all 13 articles
    for idx, key in enumerate(ORDERED_KEYS, start=1):
        op.execute(
            f"UPDATE cm_contract_article_templates SET article_number = {idx} "
            f"WHERE article_key = '{key}'"
        )


def downgrade() -> None:
    # Not implemented — restoring from migration 034/044 would require full re-seed
    pass
