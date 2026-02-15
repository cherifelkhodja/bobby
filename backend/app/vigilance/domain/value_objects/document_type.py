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
            "extrait_insee": "Extrait INSEE",
            "attestation_urssaf": "Attestation URSSAF",
            "attestation_fiscale": "Attestation fiscale",
            "attestation_assurance_rc_pro": "Attestation RC Pro",
            "attestation_vigilance": "Attestation de vigilance",
            "certificat_regularite_fiscale": "Certificat de régularité fiscale",
            "rib": "RIB",
            "cni_representant": "CNI du représentant",
            "liste_salaries_etrangers": "Liste des salariés étrangers",
        }
        return labels.get(self.value, self.value)


# Documents interdits par le RGPD
FORBIDDEN_DOCUMENT_TYPES = frozenset({
    "casier_judiciaire",
    "releve_bancaire",
    "avis_imposition_personnel",
    "certificat_medical",
})
