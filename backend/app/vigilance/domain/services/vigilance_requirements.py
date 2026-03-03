"""Vigilance document requirements per third party type."""

from app.third_party.domain.value_objects.third_party_type import ThirdPartyType
from app.vigilance.domain.value_objects.document_type import DocumentType

# Document requirements per third party type.
# Each entry defines: document_type, validity_months (None = no expiry),
# and whether it is mandatory.
VIGILANCE_REQUIREMENTS: dict[ThirdPartyType, list[dict]] = {
    # Entreprise Individuelle / Micro-entreprise
    ThirdPartyType.FREELANCE: [
        {"type": DocumentType.EXTRAIT_INSEE, "validity_months": 3, "mandatory": True},
        {"type": DocumentType.ATTESTATION_VIGILANCE, "validity_months": 6, "mandatory": True},
        {"type": DocumentType.ATTESTATION_FISCALE, "validity_months": 6, "mandatory": True},
        {"type": DocumentType.ATTESTATION_ASSURANCE_RC_PRO, "validity_months": None, "mandatory": True},
        {"type": DocumentType.RIB, "validity_months": None, "mandatory": True},
    ],
    # Société (SAS, SASU, SARL, EURL, SA, etc.)
    ThirdPartyType.SOUS_TRAITANT: [
        {"type": DocumentType.KBIS, "validity_months": 3, "mandatory": True},
        {"type": DocumentType.ATTESTATION_VIGILANCE, "validity_months": 6, "mandatory": True},
        {"type": DocumentType.ATTESTATION_FISCALE, "validity_months": 6, "mandatory": True},
        {"type": DocumentType.ATTESTATION_ASSURANCE_RC_PRO, "validity_months": None, "mandatory": True},
        {"type": DocumentType.RIB, "validity_months": None, "mandatory": True},
    ],
    # Salarié porté — pas de collecte documentaire requise
    ThirdPartyType.SALARIE: [],
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
