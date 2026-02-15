"""Vigilance document requirements per third party type."""

from app.third_party.domain.value_objects.third_party_type import ThirdPartyType
from app.vigilance.domain.value_objects.document_type import DocumentType

# Document requirements per third party type.
# Each entry defines: document_type, validity_months (None = no expiry),
# and whether it is mandatory.
VIGILANCE_REQUIREMENTS: dict[ThirdPartyType, list[dict]] = {
    ThirdPartyType.FREELANCE: [
        {"type": DocumentType.KBIS, "validity_months": 3, "mandatory": True},
        {"type": DocumentType.ATTESTATION_URSSAF, "validity_months": 6, "mandatory": True},
        {"type": DocumentType.ATTESTATION_FISCALE, "validity_months": 12, "mandatory": True},
        {"type": DocumentType.ATTESTATION_ASSURANCE_RC_PRO, "validity_months": 12, "mandatory": True},
        {"type": DocumentType.ATTESTATION_VIGILANCE, "validity_months": 6, "mandatory": True},
        {"type": DocumentType.RIB, "validity_months": None, "mandatory": True},
        {"type": DocumentType.CNI_REPRESENTANT, "validity_months": None, "mandatory": True},
    ],
    ThirdPartyType.SOUS_TRAITANT: [
        {"type": DocumentType.KBIS, "validity_months": 3, "mandatory": True},
        {"type": DocumentType.ATTESTATION_URSSAF, "validity_months": 6, "mandatory": True},
        {"type": DocumentType.ATTESTATION_FISCALE, "validity_months": 12, "mandatory": True},
        {"type": DocumentType.ATTESTATION_ASSURANCE_RC_PRO, "validity_months": 12, "mandatory": True},
        {"type": DocumentType.ATTESTATION_VIGILANCE, "validity_months": 6, "mandatory": True},
        {"type": DocumentType.CERTIFICAT_REGULARITE_FISCALE, "validity_months": 12, "mandatory": False},
        {"type": DocumentType.RIB, "validity_months": None, "mandatory": True},
        {"type": DocumentType.CNI_REPRESENTANT, "validity_months": None, "mandatory": True},
        {"type": DocumentType.LISTE_SALARIES_ETRANGERS, "validity_months": 6, "mandatory": False},
    ],
    ThirdPartyType.SALARIE: [],
}

# Maximum retention period for documents (RGPD)
RETENTION_YEARS = 5

# Maximum file size in bytes (10 Mo)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Allowed MIME types for document uploads
ALLOWED_MIME_TYPES = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
})

# Allowed file extensions
ALLOWED_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png"})
