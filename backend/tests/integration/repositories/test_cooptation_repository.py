"""Integration tests for CooptationRepository."""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Candidate, Cooptation, Opportunity, User
from app.domain.value_objects import CooptationStatus, Email, UserRole
from app.infrastructure.database.repositories import (
    CandidateRepository,
    CooptationRepository,
    OpportunityRepository,
    UserRepository,
)


class TestCooptationRepository:
    """Integration tests for CooptationRepository."""

    @pytest_asyncio.fixture
    async def repository(self, db_session: AsyncSession):
        """Create CooptationRepository with test session."""
        return CooptationRepository(db_session)

    @pytest_asyncio.fixture
    async def user_repo(self, db_session: AsyncSession):
        """Create UserRepository with test session."""
        return UserRepository(db_session)

    @pytest_asyncio.fixture
    async def candidate_repo(self, db_session: AsyncSession):
        """Create CandidateRepository with test session."""
        return CandidateRepository(db_session)

    @pytest_asyncio.fixture
    async def opportunity_repo(self, db_session: AsyncSession):
        """Create OpportunityRepository with test session."""
        return OpportunityRepository(db_session)

    @pytest_asyncio.fixture
    async def submitter(self, user_repo: UserRepository) -> User:
        """Create a submitter user."""
        user = User(
            email=Email(f"submitter-{uuid4().hex[:8]}@example.com"),
            first_name="Submitter",
            last_name="User",
            password_hash="hashed",
            role=UserRole.USER,
            is_verified=True,
            is_active=True,
        )
        return await user_repo.save(user)

    @pytest_asyncio.fixture
    async def candidate(self, candidate_repo: CandidateRepository) -> Candidate:
        """Create a candidate."""
        candidate = Candidate(
            email=Email(f"candidate-{uuid4().hex[:8]}@example.com"),
            first_name="John",
            last_name="Candidate",
            civility="M",
            daily_rate=500.0,
        )
        return await candidate_repo.save(candidate)

    @pytest_asyncio.fixture
    async def opportunity(
        self, opportunity_repo: OpportunityRepository, submitter: User
    ) -> Opportunity:
        """Create an opportunity."""
        opp = Opportunity(
            title="Test Opportunity",
            reference=f"REF-{uuid4().hex[:8]}",
            external_id=str(uuid4()),
            is_active=True,
            is_shared=True,
            owner_id=submitter.id,
        )
        return await opportunity_repo.save(opp)

    @pytest.mark.asyncio
    async def test_save_new_cooptation(
        self,
        repository: CooptationRepository,
        submitter: User,
        candidate: Candidate,
        opportunity: Opportunity,
    ):
        """Test saving a new cooptation."""
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=submitter.id,
            status=CooptationStatus.PENDING,
        )

        saved = await repository.save(cooptation)

        assert saved.id == cooptation.id
        assert saved.status == CooptationStatus.PENDING
        assert saved.candidate.id == candidate.id
        assert saved.opportunity.id == opportunity.id

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        repository: CooptationRepository,
        submitter: User,
        candidate: Candidate,
        opportunity: Opportunity,
    ):
        """Test retrieving cooptation by ID."""
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=submitter.id,
        )
        await repository.save(cooptation)

        retrieved = await repository.get_by_id(cooptation.id)

        assert retrieved is not None
        assert retrieved.id == cooptation.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository: CooptationRepository):
        """Test retrieving non-existent cooptation returns None."""
        retrieved = await repository.get_by_id(uuid4())

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_candidate_email_and_opportunity(
        self,
        repository: CooptationRepository,
        submitter: User,
        candidate: Candidate,
        opportunity: Opportunity,
    ):
        """Test checking for duplicate cooptation."""
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=submitter.id,
        )
        await repository.save(cooptation)

        # Try to find duplicate
        found = await repository.get_by_candidate_email_and_opportunity(
            email=str(candidate.email),
            opportunity_id=opportunity.id,
        )

        assert found is not None
        assert found.id == cooptation.id

    @pytest.mark.asyncio
    async def test_get_by_candidate_email_and_opportunity_not_found(
        self,
        repository: CooptationRepository,
        opportunity: Opportunity,
    ):
        """Test no duplicate when candidate email doesn't exist."""
        found = await repository.get_by_candidate_email_and_opportunity(
            email="nonexistent@example.com",
            opportunity_id=opportunity.id,
        )

        assert found is None

    @pytest.mark.asyncio
    async def test_list_by_submitter(
        self,
        repository: CooptationRepository,
        user_repo: UserRepository,
        candidate_repo: CandidateRepository,
        opportunity_repo: OpportunityRepository,
        submitter: User,
        opportunity: Opportunity,
    ):
        """Test listing cooptations by submitter."""
        # Create another submitter
        other_submitter = await user_repo.save(
            User(
                email=Email(f"other-{uuid4().hex[:8]}@example.com"),
                first_name="Other",
                last_name="User",
                password_hash="hashed",
                role=UserRole.USER,
                is_verified=True,
                is_active=True,
            )
        )

        # Create cooptations for first submitter
        for i in range(3):
            cand = await candidate_repo.save(
                Candidate(
                    email=Email(f"cand{i}-{uuid4().hex[:8]}@example.com"),
                    first_name=f"Cand{i}",
                    last_name="Test",
                    civility="M",
                )
            )
            coopt = Cooptation(
                candidate=cand,
                opportunity=opportunity,
                submitter_id=submitter.id,
            )
            await repository.save(coopt)

        # Create cooptation for other submitter
        other_cand = await candidate_repo.save(
            Candidate(
                email=Email(f"other-cand-{uuid4().hex[:8]}@example.com"),
                first_name="Other",
                last_name="Candidate",
                civility="M",
            )
        )
        other_coopt = Cooptation(
            candidate=other_cand,
            opportunity=opportunity,
            submitter_id=other_submitter.id,
        )
        await repository.save(other_coopt)

        # List by first submitter
        listed = await repository.list_by_submitter(submitter.id)

        assert len(listed) == 3
        for coopt in listed:
            assert coopt.submitter_id == submitter.id

    @pytest.mark.asyncio
    async def test_list_all_with_status_filter(
        self,
        repository: CooptationRepository,
        candidate_repo: CandidateRepository,
        submitter: User,
        opportunity: Opportunity,
    ):
        """Test listing cooptations filtered by status."""
        # Create cooptations with different statuses
        statuses = [
            CooptationStatus.PENDING,
            CooptationStatus.PENDING,
            CooptationStatus.IN_REVIEW,
            CooptationStatus.ACCEPTED,
        ]

        for i, status in enumerate(statuses):
            cand = await candidate_repo.save(
                Candidate(
                    email=Email(f"status{i}-{uuid4().hex[:8]}@example.com"),
                    first_name=f"Status{i}",
                    last_name="Test",
                    civility="M",
                )
            )
            coopt = Cooptation(
                candidate=cand,
                opportunity=opportunity,
                submitter_id=submitter.id,
                status=status,
            )
            await repository.save(coopt)

        # List only PENDING
        pending = await repository.list_all(status=CooptationStatus.PENDING)
        assert len(pending) == 2

        # List only IN_REVIEW
        in_review = await repository.list_all(status=CooptationStatus.IN_REVIEW)
        assert len(in_review) == 1

    @pytest.mark.asyncio
    async def test_count_by_status(
        self,
        repository: CooptationRepository,
        candidate_repo: CandidateRepository,
        submitter: User,
        opportunity: Opportunity,
    ):
        """Test counting cooptations by status."""
        # Create cooptations
        for i in range(5):
            status = CooptationStatus.PENDING if i < 3 else CooptationStatus.ACCEPTED
            cand = await candidate_repo.save(
                Candidate(
                    email=Email(f"count{i}-{uuid4().hex[:8]}@example.com"),
                    first_name=f"Count{i}",
                    last_name="Test",
                    civility="M",
                )
            )
            coopt = Cooptation(
                candidate=cand,
                opportunity=opportunity,
                submitter_id=submitter.id,
                status=status,
            )
            await repository.save(coopt)

        # Count by status
        pending_count = await repository.count_by_status(CooptationStatus.PENDING)
        accepted_count = await repository.count_by_status(CooptationStatus.ACCEPTED)

        assert pending_count == 3
        assert accepted_count == 2

    @pytest.mark.asyncio
    async def test_update_cooptation_status(
        self,
        repository: CooptationRepository,
        submitter: User,
        candidate: Candidate,
        opportunity: Opportunity,
    ):
        """Test updating cooptation status."""
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=submitter.id,
            status=CooptationStatus.PENDING,
        )
        await repository.save(cooptation)

        # Change status
        cooptation.change_status(CooptationStatus.IN_REVIEW, submitter.id)
        await repository.save(cooptation)

        # Verify
        retrieved = await repository.get_by_id(cooptation.id)
        assert retrieved is not None
        assert retrieved.status == CooptationStatus.IN_REVIEW

    @pytest.mark.asyncio
    async def test_status_history_persisted(
        self,
        repository: CooptationRepository,
        submitter: User,
        candidate: Candidate,
        opportunity: Opportunity,
    ):
        """Test that status history is correctly persisted."""
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=submitter.id,
            status=CooptationStatus.PENDING,
        )
        await repository.save(cooptation)

        # Make status transitions
        cooptation.change_status(CooptationStatus.IN_REVIEW, submitter.id, "Starting review")
        await repository.save(cooptation)

        cooptation.change_status(CooptationStatus.INTERVIEW, submitter.id, "Scheduling interview")
        await repository.save(cooptation)

        # Verify history
        retrieved = await repository.get_by_id(cooptation.id)
        assert retrieved is not None
        assert len(retrieved.status_history) == 2
        assert retrieved.status_history[0].to_status == CooptationStatus.IN_REVIEW
        assert retrieved.status_history[1].to_status == CooptationStatus.INTERVIEW

    @pytest.mark.asyncio
    async def test_delete_cooptation(
        self,
        repository: CooptationRepository,
        submitter: User,
        candidate: Candidate,
        opportunity: Opportunity,
    ):
        """Test deleting a cooptation."""
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=submitter.id,
        )
        await repository.save(cooptation)

        # Delete
        deleted = await repository.delete(cooptation.id)
        assert deleted is True

        # Verify
        retrieved = await repository.get_by_id(cooptation.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_stats_by_submitter(
        self,
        repository: CooptationRepository,
        candidate_repo: CandidateRepository,
        submitter: User,
        opportunity: Opportunity,
    ):
        """Test getting statistics by submitter."""
        # Create cooptations with various statuses
        status_distribution = {
            CooptationStatus.PENDING: 2,
            CooptationStatus.IN_REVIEW: 1,
            CooptationStatus.INTERVIEW: 1,
            CooptationStatus.ACCEPTED: 3,
            CooptationStatus.REJECTED: 1,
        }

        idx = 0
        for status, count in status_distribution.items():
            for _ in range(count):
                cand = await candidate_repo.save(
                    Candidate(
                        email=Email(f"stats{idx}-{uuid4().hex[:8]}@example.com"),
                        first_name=f"Stats{idx}",
                        last_name="Test",
                        civility="M",
                    )
                )
                coopt = Cooptation(
                    candidate=cand,
                    opportunity=opportunity,
                    submitter_id=submitter.id,
                    status=status,
                )
                await repository.save(coopt)
                idx += 1

        # Get stats
        stats = await repository.get_stats_by_submitter(submitter.id)

        assert stats["total"] == 8
        assert stats.get("pending", 0) == 2
        assert stats.get("in_review", 0) == 1
        assert stats.get("interview", 0) == 1
        assert stats.get("accepted", 0) == 3
        assert stats.get("rejected", 0) == 1
