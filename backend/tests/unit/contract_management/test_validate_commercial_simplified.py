"""Tests for simplified ValidateCommercialUseCase (ADR-009)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.validate_commercial import (
    ValidateCommercialCommand,
    ValidateCommercialUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


def _make_cr(**overrides) -> ContractRequest:
    """Create a test ContractRequest entity."""
    defaults = {
        "provisional_reference": "PROV-2026-0001",
        "trigger_type": "candidat_11",
        "status": ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION,
    }
    defaults.update(overrides)
    return ContractRequest(**defaults)


def _make_use_case(cr: ContractRequest, **overrides) -> ValidateCommercialUseCase:
    """Create use case with mock dependencies and a pre-loaded CR."""
    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(return_value=cr)
    cr_repo.save = AsyncMock(side_effect=lambda x: x)
    cr_repo.get_by_positioning_id = AsyncMock(return_value=None)

    tp_repo = AsyncMock()

    generate_magic_link_uc = AsyncMock()
    generate_magic_link_uc.execute = AsyncMock()

    request_documents_uc = AsyncMock()

    defaults = {
        "contract_request_repository": cr_repo,
        "third_party_repository": tp_repo,
        "find_or_create_third_party_use_case": None,
        "generate_magic_link_use_case": generate_magic_link_uc,
        "request_documents_use_case": request_documents_uc,
    }
    defaults.update(overrides)
    return ValidateCommercialUseCase(**defaults)


class TestSimplifiedValidation:
    """Test that commercial validation only requires type tiers + contact email."""

    @pytest.mark.asyncio
    async def test_validates_with_minimal_fields(self):
        """Should validate with only type tiers and contact email."""
        cr = _make_cr()
        uc = _make_use_case(cr)

        command = ValidateCommercialCommand(
            contract_request_id=cr.id,
            third_party_type="freelance",
            contact_email="contact@fournisseur.fr",
        )

        result = await uc.execute(command)

        assert result.third_party_type == "freelance"
        assert result.contractualization_contact_email == "contact@fournisseur.fr"
        assert result.status == ContractRequestStatus.COLLECTING_DOCUMENTS

    @pytest.mark.asyncio
    async def test_consultant_info_optional(self):
        """Should accept optional consultant info."""
        cr = _make_cr()
        uc = _make_use_case(cr)

        command = ValidateCommercialCommand(
            contract_request_id=cr.id,
            third_party_type="sous_traitant",
            contact_email="contact@fournisseur.fr",
            consultant_civility="M.",
            consultant_first_name="Jean",
            consultant_last_name="Dupont",
            consultant_email="jean@dupont.fr",
            consultant_phone="+33612345678",
        )

        result = await uc.execute(command)

        assert result.consultant_first_name == "Jean"
        assert result.consultant_last_name == "Dupont"
        assert result.consultant_email == "jean@dupont.fr"

    @pytest.mark.asyncio
    async def test_preserves_existing_consultant_data(self):
        """Should keep Boond-provided consultant data when not overridden."""
        cr = _make_cr(
            consultant_first_name="Pierre",
            consultant_last_name="Martin",
        )
        uc = _make_use_case(cr)

        command = ValidateCommercialCommand(
            contract_request_id=cr.id,
            third_party_type="freelance",
            contact_email="contact@fournisseur.fr",
        )

        result = await uc.execute(command)

        # Consultant data from Boond preserved (not overwritten with None)
        assert result.consultant_first_name == "Pierre"
        assert result.consultant_last_name == "Martin"


class TestSalarieRedirectPayfit:
    """Test salarié type redirects to PayFit."""

    @pytest.mark.asyncio
    async def test_redirects_to_payfit(self):
        """Should redirect to PayFit for salarié type."""
        cr = _make_cr()
        uc = _make_use_case(cr)

        command = ValidateCommercialCommand(
            contract_request_id=cr.id,
            third_party_type="salarie",
            contact_email="contact@fournisseur.fr",
        )

        result = await uc.execute(command)

        assert result.status == ContractRequestStatus.REDIRECTED_PAYFIT
        assert result.third_party_type == "salarie"


class TestRecontractualization:
    """Test re-contractualization logic for trigger_type=ressource_4."""

    @pytest.mark.asyncio
    async def test_reuses_third_party_from_previous_cr(self):
        """Should reuse ThirdParty from previous CR when trigger is ressource_4."""
        previous_tp_id = uuid4()
        previous_cr_id = uuid4()

        previous_cr = _make_cr(
            id=previous_cr_id,
            third_party_id=previous_tp_id,
            status=ContractRequestStatus.ARCHIVED,
        )

        cr = _make_cr(
            trigger_type="ressource_4",
            previous_contract_request_id=previous_cr_id,
        )

        cr_repo = AsyncMock()
        cr_repo.get_by_id = AsyncMock(side_effect=lambda id_: cr if id_ == cr.id else previous_cr)
        cr_repo.save = AsyncMock(side_effect=lambda x: x)

        # No expired docs → should skip to reviewing compliance
        doc_repo = AsyncMock()
        doc_repo.list_by_third_party = AsyncMock(return_value=[])

        uc = ValidateCommercialUseCase(
            contract_request_repository=cr_repo,
            third_party_repository=AsyncMock(),
            find_or_create_third_party_use_case=None,
            generate_magic_link_use_case=AsyncMock(),
            request_documents_use_case=AsyncMock(),
            document_repository=doc_repo,
        )

        command = ValidateCommercialCommand(
            contract_request_id=cr.id,
            third_party_type="freelance",
            contact_email="contact@fournisseur.fr",
        )

        result = await uc.execute(command)

        assert result.third_party_id == previous_tp_id
        # With no expired docs → should reach reviewing_compliance
        assert result.status == ContractRequestStatus.REVIEWING_COMPLIANCE

    @pytest.mark.asyncio
    async def test_requests_expired_docs(self):
        """Should send magic link when previous docs are expired."""
        from datetime import datetime, timedelta

        previous_tp_id = uuid4()
        previous_cr_id = uuid4()

        previous_cr = _make_cr(
            id=previous_cr_id,
            third_party_id=previous_tp_id,
            status=ContractRequestStatus.ARCHIVED,
        )

        cr = _make_cr(
            trigger_type="ressource_4",
            previous_contract_request_id=previous_cr_id,
        )

        cr_repo = AsyncMock()
        cr_repo.get_by_id = AsyncMock(side_effect=lambda id_: cr if id_ == cr.id else previous_cr)
        cr_repo.save = AsyncMock(side_effect=lambda x: x)

        # Simulate an expired doc
        expired_doc = MagicMock()
        expired_doc.status = "expired"
        expired_doc.expires_at = datetime.utcnow() - timedelta(days=10)

        doc_repo = AsyncMock()
        doc_repo.list_by_third_party = AsyncMock(return_value=[expired_doc])

        magic_link_uc = AsyncMock()
        magic_link_uc.execute = AsyncMock()

        uc = ValidateCommercialUseCase(
            contract_request_repository=cr_repo,
            third_party_repository=AsyncMock(),
            find_or_create_third_party_use_case=None,
            generate_magic_link_use_case=magic_link_uc,
            request_documents_use_case=AsyncMock(),
            document_repository=doc_repo,
        )

        command = ValidateCommercialCommand(
            contract_request_id=cr.id,
            third_party_type="freelance",
            contact_email="contact@fournisseur.fr",
        )

        result = await uc.execute(command)

        # Should stay at collecting_documents (expired docs need renewal)
        assert result.status == ContractRequestStatus.COLLECTING_DOCUMENTS
        magic_link_uc.execute.assert_called_once()


class TestCommandValidation:
    """Test that the command accepts only the simplified fields."""

    def test_command_has_no_daily_rate(self):
        """Command should not accept daily_rate."""
        import inspect
        params = inspect.signature(ValidateCommercialCommand.__init__).parameters
        assert "daily_rate" not in params

    def test_command_has_no_start_date(self):
        """Command should not accept start_date."""
        import inspect
        params = inspect.signature(ValidateCommercialCommand.__init__).parameters
        assert "start_date" not in params

    def test_command_has_no_mission_fields(self):
        """Command should not accept mission-specific fields."""
        import inspect
        params = inspect.signature(ValidateCommercialCommand.__init__).parameters
        mission_fields = [
            "mission_title", "mission_description", "mission_site_name",
            "mission_address", "mission_postal_code", "mission_city",
        ]
        for field in mission_fields:
            assert field not in params, f"{field} should not be in command"

    def test_command_accepts_required_fields(self):
        """Command should accept type tiers and contact email."""
        import inspect
        params = inspect.signature(ValidateCommercialCommand.__init__).parameters
        assert "third_party_type" in params
        assert "contact_email" in params
        assert "consultant_civility" in params
        assert "consultant_first_name" in params
