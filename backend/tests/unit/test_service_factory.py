"""Unit tests for ServiceFactory wiring of new bounded contexts."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.service_factory import ServiceFactory


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_settings():
    """Create a mock Settings."""
    settings = MagicMock()
    settings.INSEE_CONSUMER_KEY = "test-key"
    settings.INSEE_CONSUMER_SECRET = "test-secret"
    settings.YOUSIGN_API_KEY = "test-yousign-key"
    settings.YOUSIGN_API_BASE_URL = "https://api-sandbox.yousign.app/v3"
    settings.BOBBY_PORTAL_BASE_URL = "https://bobby.test/portal"
    return settings


@pytest.fixture
def factory(mock_db, mock_settings):
    """Create a ServiceFactory instance."""
    return ServiceFactory(mock_db, mock_settings)


# ============================================================================
# Third Party / Vigilance / Contract Management Repositories
# ============================================================================


class TestThirdPartyRepositories:
    """Tests for third_party bounded context repositories."""

    def test_third_party_repository_created(self, factory):
        """Given a factory, third_party_repository returns a ThirdPartyRepository."""
        repo = factory.third_party_repository
        assert repo is not None
        from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
            ThirdPartyRepository,
        )
        assert isinstance(repo, ThirdPartyRepository)

    def test_third_party_repository_cached(self, factory):
        """Given a factory, accessing third_party_repository twice returns same instance."""
        repo1 = factory.third_party_repository
        repo2 = factory.third_party_repository
        assert repo1 is repo2

    def test_magic_link_repository_created(self, factory):
        """Given a factory, magic_link_repository returns a MagicLinkRepository."""
        repo = factory.magic_link_repository
        assert repo is not None
        from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
            MagicLinkRepository,
        )
        assert isinstance(repo, MagicLinkRepository)

    def test_magic_link_repository_cached(self, factory):
        """Given a factory, accessing magic_link_repository twice returns same instance."""
        repo1 = factory.magic_link_repository
        repo2 = factory.magic_link_repository
        assert repo1 is repo2


class TestVigilanceRepositories:
    """Tests for vigilance bounded context repositories."""

    def test_document_repository_created(self, factory):
        """Given a factory, document_repository returns a DocumentRepository."""
        repo = factory.document_repository
        assert repo is not None
        from app.vigilance.infrastructure.adapters.postgres_document_repo import (
            DocumentRepository,
        )
        assert isinstance(repo, DocumentRepository)

    def test_document_repository_cached(self, factory):
        """Given a factory, accessing document_repository twice returns same instance."""
        repo1 = factory.document_repository
        repo2 = factory.document_repository
        assert repo1 is repo2


class TestContractManagementRepositories:
    """Tests for contract_management bounded context repositories."""

    def test_contract_request_repository_created(self, factory):
        """Given a factory, contract_request_repository returns a ContractRequestRepository."""
        repo = factory.contract_request_repository
        assert repo is not None
        from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
            ContractRequestRepository,
        )
        assert isinstance(repo, ContractRequestRepository)

    def test_contract_request_repository_cached(self, factory):
        """Given a factory, accessing contract_request_repository twice returns same instance."""
        repo1 = factory.contract_request_repository
        repo2 = factory.contract_request_repository
        assert repo1 is repo2

    def test_contract_repository_created(self, factory):
        """Given a factory, contract_repository returns a ContractRepository."""
        repo = factory.contract_repository
        assert repo is not None
        from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
            ContractRepository,
        )
        assert isinstance(repo, ContractRepository)

    def test_contract_repository_cached(self, factory):
        """Given a factory, accessing contract_repository twice returns same instance."""
        repo1 = factory.contract_repository
        repo2 = factory.contract_repository
        assert repo1 is repo2

    def test_webhook_event_repository_created(self, factory):
        """Given a factory, webhook_event_repository returns a WebhookEventRepository."""
        repo = factory.webhook_event_repository
        assert repo is not None
        from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
            WebhookEventRepository,
        )
        assert isinstance(repo, WebhookEventRepository)

    def test_webhook_event_repository_cached(self, factory):
        """Given a factory, accessing webhook_event_repository twice returns same instance."""
        repo1 = factory.webhook_event_repository
        repo2 = factory.webhook_event_repository
        assert repo1 is repo2


# ============================================================================
# External Services
# ============================================================================


class TestExternalServices:
    """Tests for new external service creation."""

    def test_insee_client_created(self, factory):
        """Given a factory, insee_client returns an InseeClient."""
        client = factory.insee_client
        assert client is not None
        from app.third_party.infrastructure.adapters.insee_client import InseeClient
        assert isinstance(client, InseeClient)

    def test_insee_client_cached(self, factory):
        """Given a factory, accessing insee_client twice returns same instance."""
        client1 = factory.insee_client
        client2 = factory.insee_client
        assert client1 is client2

    def test_yousign_client_created(self, factory):
        """Given a factory, yousign_client returns a YouSignClient."""
        client = factory.yousign_client
        assert client is not None
        from app.contract_management.infrastructure.adapters.yousign_client import (
            YouSignClient,
        )
        assert isinstance(client, YouSignClient)

    def test_yousign_client_cached(self, factory):
        """Given a factory, accessing yousign_client twice returns same instance."""
        client1 = factory.yousign_client
        client2 = factory.yousign_client
        assert client1 is client2

    def test_boond_crm_adapter_created(self, factory):
        """Given a factory, boond_crm_adapter returns a BoondCrmAdapter."""
        adapter = factory.boond_crm_adapter
        assert adapter is not None
        from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
            BoondCrmAdapter,
        )
        assert isinstance(adapter, BoondCrmAdapter)


# ============================================================================
# Use Cases - Third Party
# ============================================================================


class TestThirdPartyUseCases:
    """Tests for third_party use case creation."""

    def test_find_or_create_third_party_use_case(self, factory):
        """Given a factory, creates FindOrCreateThirdPartyUseCase with correct deps."""
        use_case = factory.create_find_or_create_third_party_use_case()
        assert use_case is not None
        from app.third_party.application.use_cases.find_or_create_third_party import (
            FindOrCreateThirdPartyUseCase,
        )
        assert isinstance(use_case, FindOrCreateThirdPartyUseCase)

    def test_generate_magic_link_use_case(self, factory):
        """Given a factory, creates GenerateMagicLinkUseCase with correct deps."""
        use_case = factory.create_generate_magic_link_use_case()
        assert use_case is not None
        from app.third_party.application.use_cases.generate_magic_link import (
            GenerateMagicLinkUseCase,
        )
        assert isinstance(use_case, GenerateMagicLinkUseCase)


# ============================================================================
# Use Cases - Contract Management
# ============================================================================


class TestContractManagementUseCases:
    """Tests for contract_management use case creation."""

    def test_generate_draft_use_case(self, factory):
        """Given a factory, creates GenerateDraftUseCase with correct deps."""
        use_case = factory.create_generate_draft_use_case()
        assert use_case is not None
        from app.contract_management.application.use_cases.generate_draft import (
            GenerateDraftUseCase,
        )
        assert isinstance(use_case, GenerateDraftUseCase)

    def test_send_draft_to_partner_use_case(self, factory):
        """Given a factory, creates SendDraftToPartnerUseCase with correct deps."""
        use_case = factory.create_send_draft_to_partner_use_case()
        assert use_case is not None
        from app.contract_management.application.use_cases.send_draft_to_partner import (
            SendDraftToPartnerUseCase,
        )
        assert isinstance(use_case, SendDraftToPartnerUseCase)

    def test_send_for_signature_use_case(self, factory):
        """Given a factory, creates SendForSignatureUseCase with correct deps."""
        use_case = factory.create_send_for_signature_use_case()
        assert use_case is not None
        from app.contract_management.application.use_cases.send_for_signature import (
            SendForSignatureUseCase,
        )
        assert isinstance(use_case, SendForSignatureUseCase)

    def test_handle_signature_completed_use_case(self, factory):
        """Given a factory, creates HandleSignatureCompletedUseCase with correct deps."""
        use_case = factory.create_handle_signature_completed_use_case()
        assert use_case is not None
        from app.contract_management.application.use_cases.handle_signature_completed import (
            HandleSignatureCompletedUseCase,
        )
        assert isinstance(use_case, HandleSignatureCompletedUseCase)

    def test_push_to_crm_use_case(self, factory):
        """Given a factory, creates PushToCrmUseCase with correct deps."""
        use_case = factory.create_push_to_crm_use_case()
        assert use_case is not None
        from app.contract_management.application.use_cases.push_to_crm import (
            PushToCrmUseCase,
        )
        assert isinstance(use_case, PushToCrmUseCase)


# ============================================================================
# Repository Independence
# ============================================================================


class TestRepositoryIndependence:
    """Tests that repositories from different contexts are independent."""

    def test_all_new_repos_are_distinct(self, factory):
        """Given a factory, all new bounded context repositories are distinct instances."""
        repos = [
            factory.third_party_repository,
            factory.magic_link_repository,
            factory.document_repository,
            factory.contract_request_repository,
            factory.contract_repository,
            factory.webhook_event_repository,
        ]
        assert len(set(id(r) for r in repos)) == len(repos)

    def test_new_repos_independent_from_existing(self, factory):
        """Given a factory, new repos don't interfere with existing ones."""
        # Access a few existing repos
        user_repo = factory.user_repository
        candidate_repo = factory.candidate_repository

        # Then access new repos
        tp_repo = factory.third_party_repository
        cr_repo = factory.contract_request_repository

        # All should be distinct
        assert user_repo is not tp_repo
        assert candidate_repo is not cr_repo
        # Existing repos still cached correctly
        assert factory.user_repository is user_repo
        assert factory.candidate_repository is candidate_repo
