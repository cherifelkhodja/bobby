"""Tests for cooptation use cases."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.use_cases.cooptations import (
    CreateCooptationCommand,
    CreateCooptationUseCase,
    GetCooptationStatsUseCase,
    GetCooptationUseCase,
    ListCooptationsUseCase,
    UpdateCooptationStatusUseCase,
)
from app.domain.entities import Candidate, Cooptation, Opportunity, User
from app.domain.exceptions import (
    CandidateAlreadyExistsError,
    CooptationNotFoundError,
    OpportunityNotFoundError,
)
from app.domain.value_objects import CooptationStatus, Email, UserRole


def create_mock_opportunity(**kwargs) -> Opportunity:
    """Factory for creating mock opportunities."""
    defaults = {
        "id": uuid4(),
        "title": "Test Opportunity",
        "reference": "REF-001",
        "external_id": "ext-123",
        "is_active": True,
        "is_shared": True,
        "owner_id": uuid4(),
    }
    defaults.update(kwargs)
    return Opportunity(**defaults)


def create_mock_candidate(**kwargs) -> Candidate:
    """Factory for creating mock candidates."""
    defaults = {
        "id": uuid4(),
        "email": Email("candidate@example.com"),
        "first_name": "John",
        "last_name": "Doe",
        "civility": "M",
    }
    defaults.update(kwargs)
    return Candidate(**defaults)


def create_mock_cooptation(**kwargs) -> Cooptation:
    """Factory for creating mock cooptations."""
    defaults = {
        "id": uuid4(),
        "candidate": create_mock_candidate(),
        "opportunity": create_mock_opportunity(),
        "submitter_id": uuid4(),
        "status": CooptationStatus.PENDING,
    }
    defaults.update(kwargs)
    return Cooptation(**defaults)


def create_mock_user(**kwargs) -> User:
    """Factory for creating mock users."""
    defaults = {
        "id": uuid4(),
        "email": Email("user@example.com"),
        "first_name": "Test",
        "last_name": "User",
        "password_hash": "hashed",
        "role": UserRole.USER,
        "is_verified": True,
        "is_active": True,
    }
    defaults.update(kwargs)
    return User(**defaults)


class TestCreateCooptationUseCase:
    """Tests for CreateCooptationUseCase."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories."""
        return {
            "cooptation_repository": AsyncMock(),
            "candidate_repository": AsyncMock(),
            "opportunity_repository": AsyncMock(),
            "published_opportunity_repository": AsyncMock(),
            "user_repository": AsyncMock(),
        }

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        return {
            "boond_client": AsyncMock(),
            "email_service": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_create_cooptation_success(self, mock_repositories, mock_services):
        """Test successful cooptation creation."""
        opportunity = create_mock_opportunity()
        candidate = create_mock_candidate()
        user = create_mock_user()

        mock_repositories["opportunity_repository"].get_by_id = AsyncMock(return_value=opportunity)
        mock_repositories[
            "cooptation_repository"
        ].get_by_candidate_email_and_opportunity = AsyncMock(return_value=None)
        mock_repositories["candidate_repository"].get_by_email = AsyncMock(return_value=None)
        mock_repositories["candidate_repository"].save = AsyncMock(return_value=candidate)
        mock_repositories["user_repository"].get_by_id = AsyncMock(return_value=user)

        cooptation = create_mock_cooptation(candidate=candidate, opportunity=opportunity)
        mock_repositories["cooptation_repository"].save = AsyncMock(return_value=cooptation)

        use_case = CreateCooptationUseCase(
            **mock_repositories,
            **mock_services,
        )

        command = CreateCooptationCommand(
            opportunity_id=opportunity.id,
            submitter_id=user.id,
            candidate_first_name="John",
            candidate_last_name="Doe",
            candidate_email="candidate@example.com",
        )

        result = await use_case.execute(command)

        assert result.candidate_email == "candidate@example.com"
        mock_repositories["cooptation_repository"].save.assert_called_once()
        mock_services["email_service"].send_cooptation_confirmation.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_cooptation_opportunity_not_found(self, mock_repositories, mock_services):
        """Test cooptation creation fails when opportunity not found."""
        mock_repositories["opportunity_repository"].get_by_id = AsyncMock(return_value=None)
        mock_repositories["published_opportunity_repository"].get_by_id = AsyncMock(
            return_value=None
        )

        use_case = CreateCooptationUseCase(
            **mock_repositories,
            **mock_services,
        )

        command = CreateCooptationCommand(
            opportunity_id=uuid4(),
            submitter_id=uuid4(),
            candidate_first_name="John",
            candidate_last_name="Doe",
            candidate_email="candidate@example.com",
        )

        with pytest.raises(OpportunityNotFoundError):
            await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_create_cooptation_duplicate_candidate(self, mock_repositories, mock_services):
        """Test cooptation creation fails with duplicate candidate for same opportunity."""
        opportunity = create_mock_opportunity()
        existing_cooptation = create_mock_cooptation()

        mock_repositories["opportunity_repository"].get_by_id = AsyncMock(return_value=opportunity)
        mock_repositories[
            "cooptation_repository"
        ].get_by_candidate_email_and_opportunity = AsyncMock(return_value=existing_cooptation)

        use_case = CreateCooptationUseCase(
            **mock_repositories,
            **mock_services,
        )

        command = CreateCooptationCommand(
            opportunity_id=opportunity.id,
            submitter_id=uuid4(),
            candidate_first_name="John",
            candidate_last_name="Doe",
            candidate_email="candidate@example.com",
        )

        with pytest.raises(CandidateAlreadyExistsError):
            await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_create_cooptation_uses_existing_candidate(
        self, mock_repositories, mock_services
    ):
        """Test cooptation uses existing candidate if found."""
        opportunity = create_mock_opportunity()
        existing_candidate = create_mock_candidate(external_id="ext-123")
        user = create_mock_user()

        mock_repositories["opportunity_repository"].get_by_id = AsyncMock(return_value=opportunity)
        mock_repositories[
            "cooptation_repository"
        ].get_by_candidate_email_and_opportunity = AsyncMock(return_value=None)
        mock_repositories["candidate_repository"].get_by_email = AsyncMock(
            return_value=existing_candidate
        )
        mock_repositories["user_repository"].get_by_id = AsyncMock(return_value=user)

        cooptation = create_mock_cooptation(candidate=existing_candidate, opportunity=opportunity)
        mock_repositories["cooptation_repository"].save = AsyncMock(return_value=cooptation)

        use_case = CreateCooptationUseCase(
            **mock_repositories,
            **mock_services,
        )

        command = CreateCooptationCommand(
            opportunity_id=opportunity.id,
            submitter_id=user.id,
            candidate_first_name="John",
            candidate_last_name="Doe",
            candidate_email="candidate@example.com",
        )

        await use_case.execute(command)

        # Should not create new candidate (existing candidate already has external_id)
        mock_repositories["candidate_repository"].save.assert_not_called()


class TestGetCooptationUseCase:
    """Tests for GetCooptationUseCase."""

    @pytest.fixture
    def mock_cooptation_repository(self):
        """Create mock cooptation repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_cooptation_success(self, mock_cooptation_repository):
        """Test successful cooptation retrieval."""
        cooptation = create_mock_cooptation()
        mock_cooptation_repository.get_by_id = AsyncMock(return_value=cooptation)

        use_case = GetCooptationUseCase(mock_cooptation_repository)

        result = await use_case.execute(cooptation.id)

        assert result.id == str(cooptation.id)
        assert result.status == str(CooptationStatus.PENDING)

    @pytest.mark.asyncio
    async def test_get_cooptation_not_found(self, mock_cooptation_repository):
        """Test cooptation retrieval fails when not found."""
        mock_cooptation_repository.get_by_id = AsyncMock(return_value=None)

        use_case = GetCooptationUseCase(mock_cooptation_repository)

        with pytest.raises(CooptationNotFoundError):
            await use_case.execute(uuid4())


class TestUpdateCooptationStatusUseCase:
    """Tests for UpdateCooptationStatusUseCase."""

    @pytest.fixture
    def mock_repositories_and_services(self):
        """Create mock repositories and services."""
        return {
            "cooptation_repository": AsyncMock(),
            "user_repository": AsyncMock(),
            "email_service": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_update_status_success(self, mock_repositories_and_services):
        """Test successful status update."""
        cooptation = create_mock_cooptation(status=CooptationStatus.PENDING)
        user = create_mock_user()

        mock_repositories_and_services["cooptation_repository"].get_by_id = AsyncMock(
            return_value=cooptation
        )
        mock_repositories_and_services["cooptation_repository"].save = AsyncMock(
            return_value=cooptation
        )
        mock_repositories_and_services["user_repository"].get_by_id = AsyncMock(return_value=user)

        use_case = UpdateCooptationStatusUseCase(**mock_repositories_and_services)

        result = await use_case.execute(
            cooptation_id=cooptation.id,
            new_status=CooptationStatus.IN_REVIEW,
            changed_by=user.id,
            comment="Starting review",
        )

        assert result.status == str(CooptationStatus.IN_REVIEW)
        mock_repositories_and_services[
            "email_service"
        ].send_cooptation_status_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_cooptation_not_found(self, mock_repositories_and_services):
        """Test status update fails when cooptation not found."""
        mock_repositories_and_services["cooptation_repository"].get_by_id = AsyncMock(
            return_value=None
        )

        use_case = UpdateCooptationStatusUseCase(**mock_repositories_and_services)

        with pytest.raises(CooptationNotFoundError):
            await use_case.execute(
                cooptation_id=uuid4(),
                new_status=CooptationStatus.IN_REVIEW,
                changed_by=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition(self, mock_repositories_and_services):
        """Test status update fails with invalid transition."""
        cooptation = create_mock_cooptation(status=CooptationStatus.PENDING)

        mock_repositories_and_services["cooptation_repository"].get_by_id = AsyncMock(
            return_value=cooptation
        )

        use_case = UpdateCooptationStatusUseCase(**mock_repositories_and_services)

        # PENDING -> ACCEPTED is not a valid direct transition
        with pytest.raises(ValueError, match="Invalid status transition"):
            await use_case.execute(
                cooptation_id=cooptation.id,
                new_status=CooptationStatus.ACCEPTED,
                changed_by=uuid4(),
            )


class TestListCooptationsUseCase:
    """Tests for ListCooptationsUseCase."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories."""
        return {
            "cooptation_repository": AsyncMock(),
            "user_repository": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_list_all_cooptations(self, mock_repositories):
        """Test listing all cooptations."""
        cooptations = [create_mock_cooptation() for _ in range(3)]
        user = create_mock_user()

        mock_repositories["cooptation_repository"].list_all = AsyncMock(return_value=cooptations)
        mock_repositories["cooptation_repository"].get_stats_by_submitter = AsyncMock(
            return_value={"total": 3}
        )
        mock_repositories["user_repository"].get_by_id = AsyncMock(return_value=user)

        use_case = ListCooptationsUseCase(**mock_repositories)

        result = await use_case.execute(page=1, page_size=10)

        assert len(result.items) == 3
        assert result.total == 3
        assert result.page == 1

    @pytest.mark.asyncio
    async def test_list_cooptations_by_submitter(self, mock_repositories):
        """Test listing cooptations filtered by submitter."""
        submitter_id = uuid4()
        cooptations = [create_mock_cooptation(submitter_id=submitter_id) for _ in range(2)]
        user = create_mock_user(id=submitter_id)

        mock_repositories["cooptation_repository"].list_by_submitter = AsyncMock(
            return_value=cooptations
        )
        mock_repositories["cooptation_repository"].count_by_submitter = AsyncMock(return_value=2)
        mock_repositories["user_repository"].get_by_id = AsyncMock(return_value=user)

        use_case = ListCooptationsUseCase(**mock_repositories)

        result = await use_case.execute(page=1, page_size=10, submitter_id=submitter_id)

        assert len(result.items) == 2
        assert result.total == 2


class TestGetCooptationStatsUseCase:
    """Tests for GetCooptationStatsUseCase."""

    @pytest.fixture
    def mock_cooptation_repository(self):
        """Create mock cooptation repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_stats_by_submitter(self, mock_cooptation_repository):
        """Test getting stats for a specific submitter."""
        submitter_id = uuid4()
        mock_cooptation_repository.get_stats_by_submitter = AsyncMock(
            return_value={
                "total": 10,
                "pending": 3,
                "in_review": 2,
                "interview": 2,
                "accepted": 2,
                "rejected": 1,
            }
        )

        use_case = GetCooptationStatsUseCase(mock_cooptation_repository)

        result = await use_case.execute(submitter_id=submitter_id)

        assert result.total == 10
        assert result.pending == 3
        assert result.accepted == 2
        assert result.conversion_rate == 20.0  # 2/10 * 100

    @pytest.mark.asyncio
    async def test_get_global_stats(self, mock_cooptation_repository):
        """Test getting global statistics."""
        mock_cooptation_repository.count_by_status = AsyncMock(side_effect=[5, 3, 2, 4, 1])

        use_case = GetCooptationStatsUseCase(mock_cooptation_repository)

        result = await use_case.execute()

        assert result.total == 15  # 5+3+2+4+1
        assert result.pending == 5
        assert result.in_review == 3
        assert result.interview == 2
        assert result.accepted == 4
        assert result.rejected == 1

    @pytest.mark.asyncio
    async def test_get_stats_zero_total(self, mock_cooptation_repository):
        """Test getting stats when total is zero (no division by zero)."""
        mock_cooptation_repository.get_stats_by_submitter = AsyncMock(
            return_value={
                "total": 0,
                "pending": 0,
                "in_review": 0,
                "interview": 0,
                "accepted": 0,
                "rejected": 0,
            }
        )

        use_case = GetCooptationStatsUseCase(mock_cooptation_repository)

        result = await use_case.execute(submitter_id=uuid4())

        assert result.total == 0
        assert result.conversion_rate == 0.0
