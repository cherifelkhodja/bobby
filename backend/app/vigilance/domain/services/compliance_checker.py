"""Compliance checker service.

Computes the ComplianceStatus of a third party based on its documents
vs the requirements defined in vigilance_requirements.
"""

import structlog

from app.third_party.domain.value_objects.compliance_status import ComplianceStatus
from app.third_party.domain.value_objects.third_party_type import ThirdPartyType
from app.vigilance.domain.entities.vigilance_document import VigilanceDocument
from app.vigilance.domain.services.vigilance_requirements import VIGILANCE_REQUIREMENTS
from app.vigilance.domain.value_objects.document_status import DocumentStatus

logger = structlog.get_logger()


def compute_compliance_status(
    third_party_type: ThirdPartyType,
    documents: list[VigilanceDocument],
) -> ComplianceStatus:
    """Compute the compliance status based on documents vs requirements.

    Args:
        third_party_type: The type of third party.
        documents: The current documents for this third party.

    Returns:
        The computed compliance status.
    """
    requirements = VIGILANCE_REQUIREMENTS.get(third_party_type, [])

    if not requirements:
        # Salarié or type without requirements → compliant by default
        return ComplianceStatus.COMPLIANT

    mandatory_requirements = [r for r in requirements if r["mandatory"]]

    if not mandatory_requirements:
        return ComplianceStatus.COMPLIANT

    # Index documents by type for quick lookup
    doc_by_type: dict[str, VigilanceDocument] = {}
    for doc in documents:
        # Keep the most recent document per type
        existing = doc_by_type.get(doc.document_type.value)
        if existing is None or doc.created_at > existing.created_at:
            doc_by_type[doc.document_type.value] = doc

    has_expiring = False
    has_missing_or_invalid = False

    for req in mandatory_requirements:
        doc_type = req["type"]
        doc = doc_by_type.get(doc_type.value)

        if doc is None:
            has_missing_or_invalid = True
            continue

        if doc.status == DocumentStatus.VALIDATED:
            continue
        elif doc.status == DocumentStatus.EXPIRING_SOON:
            has_expiring = True
        elif doc.status in (
            DocumentStatus.REQUESTED,
            DocumentStatus.REJECTED,
            DocumentStatus.EXPIRED,
        ):
            has_missing_or_invalid = True
        elif doc.status == DocumentStatus.RECEIVED:
            # Waiting for ADV validation — treat as pending
            has_missing_or_invalid = True

    if has_missing_or_invalid:
        return ComplianceStatus.NON_COMPLIANT
    elif has_expiring:
        return ComplianceStatus.EXPIRING_SOON
    else:
        return ComplianceStatus.COMPLIANT
