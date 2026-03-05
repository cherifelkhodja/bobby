"""Vigilance document requirements per entity category.

The entity_category discriminates based on the legal structure:
  - "ei"              : Entreprise Individuelle / Micro-entreprise
  - "societe"         : Société dotée de la personnalité morale (SAS, SASU, SARL, EURL, SA…)
  - "portage_salarial": Société de portage salarial (toujours une société + garantie financière)

A FREELANCE may be structured as either ei or societe; a SOUS_TRAITANT is always a société.
A PORTAGE_SALARIAL is always a société and requires an additional garantie financière.
Documents must be determined from entity_category, not from third_party_type alone.
"""

from app.vigilance.domain.value_objects.document_type import DocumentType

# Common documents required for all entity types that need vigilance.
_COMMON = [
    {"type": DocumentType.ATTESTATION_VIGILANCE, "validity_months": 6, "mandatory": True},
    {"type": DocumentType.ATTESTATION_FISCALE, "validity_months": 6, "mandatory": True},
    {"type": DocumentType.ATTESTATION_ASSURANCE_RC_PRO, "validity_months": None, "mandatory": True},
    {"type": DocumentType.RIB, "validity_months": None, "mandatory": True},
]

# Document requirements by entity_category.
# entity_category is submitted by the tiers on the portal company-info form.
REQUIREMENTS_BY_ENTITY_CATEGORY: dict[str, list[dict]] = {
    # Entreprise Individuelle / Micro-entreprise
    "ei": [
        {"type": DocumentType.EXTRAIT_INSEE, "validity_months": 3, "mandatory": True},
        *_COMMON,
    ],
    # Société avec personnalité morale (SAS, SASU, SARL, EURL, SA…)
    "societe": [
        {"type": DocumentType.KBIS, "validity_months": 3, "mandatory": True},
        *_COMMON,
    ],
    # Société de portage salarial : mêmes docs qu'une société + garantie financière obligatoire
    "portage_salarial": [
        {"type": DocumentType.KBIS, "validity_months": 3, "mandatory": True},
        *_COMMON,
        {"type": DocumentType.GARANTIE_FINANCIERE, "validity_months": None, "mandatory": True},
    ],
}

# Maximum retention period for documents (RGPD)
RETENTION_YEARS = 5

# Maximum file size in bytes (10 Mo)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Allowed MIME types for document uploads
ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }
)

# Allowed file extensions
ALLOWED_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png"})
