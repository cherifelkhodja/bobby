"""Compliance checker service.

Computes the ComplianceStatus of a third party based on its documents
vs the requirements defined in vigilance_requirements.
"""

import structlog

from app.third_party.domain.value_objects.compliance_status import ComplianceStatus
from app.vigilance.domain.entities.vigilance_document import VigilanceDocument
from app.vigilance.domain.services.vigilance_requirements import REQUIREMENTS_BY_ENTITY_CATEGORY
from app.vigilance.domain.value_objects.document_status import DocumentStatus
from app.vigilance.domain.value_objects.document_type import DocumentType

logger = structlog.get_logger()


def compute_compliance_status(
    documents: list[VigilanceDocument],
) -> ComplianceStatus:
    """Compute the compliance status based on documents vs requirements.

    The entity category (ei / societe) is inferred from the document types
    present in the list:
    - KBIS present → societe requirements
    - EXTRAIT_INSEE present → ei requirements
    - Neither → company info not yet submitted → NON_COMPLIANT

    Args:
        documents: The current documents for this third party.

    Returns:
        The computed compliance status.
    """
    doc_types = {doc.document_type for doc in documents}

    if DocumentType.KBIS in doc_types:
        entity_category = "societe"
    elif DocumentType.EXTRAIT_INSEE in doc_types:
        entity_category = "ei"
    else:
        # Company info not yet submitted — no documents requested yet
        return ComplianceStatus.NON_COMPLIANT

    requirements = REQUIREMENTS_BY_ENTITY_CATEGORY.get(entity_category, [])

    if not requirements:
        return ComplianceStatus.COMPLIANT

    mandatory_requirements = [r for r in requirements if r["mandatory"]]

    if not mandatory_requirements:
        return ComplianceStatus.COMPLIANT

    # Index documents by type, keeping the most recent per type
    doc_by_type: dict[str, VigilanceDocument] = {}
    for doc in documents:
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
