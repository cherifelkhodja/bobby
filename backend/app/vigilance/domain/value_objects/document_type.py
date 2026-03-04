"""Document type value object for vigilance documents."""

from enum import Enum


class DocumentType(str, Enum):
    """Types of vigilance documents required from third parties."""

    KBIS = "kbis"
    EXTRAIT_INSEE = "extrait_insee"
    ATTESTATION_URSSAF = "attestation_urssaf"
    ATTESTATION_FISCALE = "attestation_fiscale"
    ATTESTATION_ASSURANCE_RC_PRO = "attestation_assurance_rc_pro"
    ATTESTATION_VIGILANCE = "attestation_vigilance"
    CERTIFICAT_REGULARITE_FISCALE = "certificat_regularite_fiscale"
    RIB = "rib"
    CNI_REPRESENTANT = "cni_representant"
    LISTE_SALARIES_ETRANGERS = "liste_salaries_etrangers"

    @property
    def display_name(self) -> str:
        """Return a human-readable label for this document type."""
        labels = {
            "kbis": "Extrait Kbis",
            "extrait_insee": "Avis de situation SIRENE",
            "attestation_urssaf": "Attestation URSSAF",
            "attestation_fiscale": "Attestation de régularité fiscale",
            "attestation_assurance_rc_pro": "Attestation RC Pro",
            "attestation_vigilance": "Attestation de vigilance URSSAF",
            "certificat_regularite_fiscale": "Certificat de régularité fiscale",
            "rib": "RIB",
            "cni_representant": "CNI du représentant",
            "liste_salaries_etrangers": "Liste des salariés étrangers",
        }
        return labels.get(self.value, self.value)

    @property
    def validity_label(self) -> str | None:
        """Return the maximum document age requirement, or None if not applicable."""
        labels: dict[str, str | None] = {
            "kbis": "≤ 3 mois",
            "extrait_insee": "≤ 3 mois",
            "attestation_urssaf": "≤ 6 mois",
            "attestation_fiscale": "≤ 6 mois",
            "attestation_assurance_rc_pro": "En cours de validité",
            "attestation_vigilance": "≤ 6 mois",
            "certificat_regularite_fiscale": "≤ 6 mois",
            "rib": None,
            "cni_representant": None,
            "liste_salaries_etrangers": None,
        }
        return labels.get(self.value)


# Documents interdits par le RGPD
FORBIDDEN_DOCUMENT_TYPES = frozenset(
    {
        "casier_judiciaire",
        "releve_bancaire",
        "avis_imposition_personnel",
        "certificat_medical",
    }
)
