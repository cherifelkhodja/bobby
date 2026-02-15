"""Tests for compliance checker service."""

from uuid import uuid4

import pytest

from app.third_party.domain.value_objects.compliance_status import ComplianceStatus
from app.third_party.domain.value_objects.third_party_type import ThirdPartyType
from app.vigilance.domain.entities.vigilance_document import VigilanceDocument
from app.vigilance.domain.services.compliance_checker import compute_compliance_status
from app.vigilance.domain.value_objects.document_status import DocumentStatus
from app.vigilance.domain.value_objects.document_type import DocumentType


class TestComplianceChecker:
    """Tests for compliance status computation."""

    def _make_doc(self, doc_type: DocumentType, status: DocumentStatus) -> VigilanceDocument:
        """Helper to create a VigilanceDocument."""
        return VigilanceDocument(
            third_party_id=uuid4(),
            document_type=doc_type,
            status=status,
        )

    def test_salarie_is_always_compliant(self):
        """Given a salarié with no documents, compliance is COMPLIANT."""
        result = compute_compliance_status(ThirdPartyType.SALARIE, [])
        assert result == ComplianceStatus.COMPLIANT

    def test_freelance_no_docs_is_non_compliant(self):
        """Given a freelance with no documents, compliance is NON_COMPLIANT."""
        result = compute_compliance_status(ThirdPartyType.FREELANCE, [])
        assert result == ComplianceStatus.NON_COMPLIANT

    def test_freelance_all_validated_is_compliant(self):
        """Given a freelance with all required docs validated, compliance is COMPLIANT."""
        from app.vigilance.domain.services.vigilance_requirements import VIGILANCE_REQUIREMENTS

        requirements = VIGILANCE_REQUIREMENTS[ThirdPartyType.FREELANCE]
        docs = [
            self._make_doc(req["type"], DocumentStatus.VALIDATED)
            for req in requirements
            if req["mandatory"]
        ]
        result = compute_compliance_status(ThirdPartyType.FREELANCE, docs)
        assert result == ComplianceStatus.COMPLIANT

    def test_one_expiring_soon_gives_expiring_soon(self):
        """Given all docs valid but one expiring, compliance is EXPIRING_SOON."""
        from app.vigilance.domain.services.vigilance_requirements import VIGILANCE_REQUIREMENTS

        requirements = VIGILANCE_REQUIREMENTS[ThirdPartyType.FREELANCE]
        mandatory = [r for r in requirements if r["mandatory"]]

        docs = []
        for i, req in enumerate(mandatory):
            if i == 0:
                docs.append(self._make_doc(req["type"], DocumentStatus.EXPIRING_SOON))
            else:
                docs.append(self._make_doc(req["type"], DocumentStatus.VALIDATED))

        result = compute_compliance_status(ThirdPartyType.FREELANCE, docs)
        assert result == ComplianceStatus.EXPIRING_SOON

    def test_one_missing_gives_non_compliant(self):
        """Given a freelance with one mandatory doc missing, compliance is NON_COMPLIANT."""
        from app.vigilance.domain.services.vigilance_requirements import VIGILANCE_REQUIREMENTS

        requirements = VIGILANCE_REQUIREMENTS[ThirdPartyType.FREELANCE]
        mandatory = [r for r in requirements if r["mandatory"]]

        # Skip the first mandatory doc
        docs = [
            self._make_doc(req["type"], DocumentStatus.VALIDATED)
            for req in mandatory[1:]
        ]
        result = compute_compliance_status(ThirdPartyType.FREELANCE, docs)
        assert result == ComplianceStatus.NON_COMPLIANT
