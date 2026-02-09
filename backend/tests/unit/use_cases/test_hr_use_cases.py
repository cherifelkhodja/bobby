"""Tests for HR feature use cases (job postings and applications)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.use_cases.job_applications import (
    GetApplicationCvUrlUseCase,
    SubmitApplicationCommand,
    SubmitApplicationUseCase,
    UpdateApplicationStatusCommand,
    UpdateApplicationStatusUseCase,
)
from app.application.use_cases.job_postings import (
    CreateJobPostingCommand,
    CreateJobPostingUseCase,
    ListOpenOpportunitiesForHRUseCase,
    PublishJobPostingUseCase,
)
from app.domain.entities import (
    ApplicationStatus,
    ContractType,
    JobPostingStatus,
)
from app.domain.exceptions import (
    InvalidStatusTransitionError,
    JobApplicationNotFoundError,
    JobPostingNotFoundError,
    OpportunityNotFoundError,
)


class TestListOpenOpportunitiesForHRUseCase:
    """Tests for listing opportunities from BoondManager for HR dashboard."""

    @pytest.fixture
    def mock_deps(self):
        return {
            "boond_client": AsyncMock(),
            "job_posting_repo": AsyncMock(),
            "job_application_repo": AsyncMock(),
        }

    @pytest.fixture
    def use_case(self, mock_deps):
        return ListOpenOpportunitiesForHRUseCase(
            boond_client=mock_deps["boond_client"],
            job_posting_repository=mock_deps["job_posting_repo"],
            job_application_repository=mock_deps["job_application_repo"],
        )

    @pytest.mark.asyncio
    async def test_list_opportunities_for_hr_manager(self, use_case, mock_deps):
        """Should return opportunities from BoondManager where user is HR manager."""
        posting_id = uuid4()

        # Mock BoondManager opportunity data
        boond_opp = {
            "id": "BOOND-123",
            "title": "Dev Python",
            "reference": "REF-001",
            "company_name": "Client A",
            "description": "Description",
            "start_date": "2024-03-01",
            "end_date": None,
            "manager_name": "Manager Principal",
            "hr_manager_name": "HR Manager",
            "state": 0,
            "state_name": "En cours",
            "state_color": "blue",
        }

        posting = MagicMock(id=posting_id, status=JobPostingStatus.PUBLISHED)

        mock_deps["boond_client"].get_hr_manager_opportunities.return_value = [boond_opp]
        mock_deps["job_posting_repo"].get_all_by_boond_opportunity_ids.return_value = {
            "BOOND-123": posting
        }
        mock_deps["job_application_repo"].count_by_posting.return_value = 5
        mock_deps["job_application_repo"].count_unread_by_posting.return_value = 2

        result = await use_case.execute(hr_manager_boond_id="12345")

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].id == "BOOND-123"
        assert result.items[0].title == "Dev Python"
        assert result.items[0].state_name == "En cours"
        assert result.items[0].has_job_posting is True
        assert result.items[0].job_posting_id == str(posting_id)
        assert result.items[0].applications_count == 5
        assert result.items[0].new_applications_count == 2

        mock_deps["boond_client"].get_hr_manager_opportunities.assert_called_once_with(
            hr_manager_boond_id="12345"
        )

    @pytest.mark.asyncio
    async def test_list_opportunities_admin_sees_all(self, use_case, mock_deps):
        """Should return all opportunities for admin users."""
        boond_opp = {
            "id": "BOOND-456",
            "title": "Dev Java",
            "reference": "REF-002",
            "company_name": "Client B",
            "description": "Description",
            "start_date": None,
            "end_date": None,
            "manager_name": None,
            "hr_manager_name": None,
            "state": 5,
            "state_name": "Piste identifiée",
            "state_color": "yellow",
        }

        mock_deps["boond_client"].get_manager_opportunities.return_value = [boond_opp]
        mock_deps["job_posting_repo"].get_all_by_boond_opportunity_ids.return_value = {}

        result = await use_case.execute(is_admin=True)

        assert result.total == 1
        assert result.items[0].has_job_posting is False
        assert result.items[0].job_posting_id is None
        assert result.items[0].applications_count == 0

        mock_deps["boond_client"].get_manager_opportunities.assert_called_once_with(fetch_all=True)

    @pytest.mark.asyncio
    async def test_list_opportunities_requires_boond_id_for_non_admin(self, use_case, mock_deps):
        """Should raise error if non-admin user has no boond_resource_id."""
        with pytest.raises(ValueError, match="BoondManager"):
            await use_case.execute(hr_manager_boond_id=None, is_admin=False)

    @pytest.mark.asyncio
    async def test_list_opportunities_with_search(self, use_case, mock_deps):
        """Should filter opportunities by search term."""
        boond_opps = [
            {
                "id": "BOOND-123",
                "title": "Dev Python",
                "reference": "REF-001",
                "company_name": "Client A",
                "description": None,
                "start_date": None,
                "end_date": None,
                "manager_name": None,
                "hr_manager_name": None,
                "state": 0,
                "state_name": "En cours",
                "state_color": "blue",
            },
            {
                "id": "BOOND-456",
                "title": "Dev Java",
                "reference": "REF-002",
                "company_name": "Client B",
                "description": None,
                "start_date": None,
                "end_date": None,
                "manager_name": None,
                "hr_manager_name": None,
                "state": 0,
                "state_name": "En cours",
                "state_color": "blue",
            },
        ]

        mock_deps["boond_client"].get_hr_manager_opportunities.return_value = boond_opps
        mock_deps["job_posting_repo"].get_all_by_boond_opportunity_ids.return_value = {}

        result = await use_case.execute(hr_manager_boond_id="12345", search="Python")

        assert result.total == 1
        assert result.items[0].title == "Dev Python"


class TestCreateJobPostingUseCase:
    """Tests for creating job postings."""

    @pytest.fixture
    def mock_repos(self):
        return {
            "job_posting_repo": AsyncMock(),
            "opportunity_repo": AsyncMock(),
            "user_repo": AsyncMock(),
        }

    @pytest.fixture
    def use_case(self, mock_repos):
        return CreateJobPostingUseCase(
            job_posting_repository=mock_repos["job_posting_repo"],
            opportunity_repository=mock_repos["opportunity_repo"],
            user_repository=mock_repos["user_repo"],
        )

    @pytest.mark.asyncio
    async def test_create_job_posting_success(self, use_case, mock_repos):
        """Should create a draft job posting."""
        opp_id = uuid4()
        user_id = uuid4()

        opportunity = MagicMock(
            id=opp_id,
            title="Dev Python Senior",
            reference="REF-001",
            client_name="Client A",
            external_id="BOOND-123",
        )
        user = MagicMock(full_name="Jean Admin")

        mock_repos["opportunity_repo"].get_by_id.return_value = opportunity
        mock_repos["job_posting_repo"].get_by_opportunity_id.return_value = None
        mock_repos["user_repo"].get_by_id.return_value = user

        # Mock save to return the posting with an ID
        async def mock_save(posting):
            posting.id = uuid4()
            return posting

        mock_repos["job_posting_repo"].save.side_effect = mock_save

        command = CreateJobPostingCommand(
            opportunity_id=opp_id,
            created_by=user_id,
            title="Développeur Python Senior",
            description="D" * 500,
            qualifications="Q" * 150,
            location_country="France",
            contract_types=["FREELANCE"],
            skills=["Python", "FastAPI"],
        )

        result = await use_case.execute(command)

        assert result.title == "Développeur Python Senior"
        assert result.status == "draft"
        mock_repos["job_posting_repo"].save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_posting_opportunity_not_found(self, use_case, mock_repos):
        """Should raise error if opportunity doesn't exist."""
        mock_repos["opportunity_repo"].get_by_id.return_value = None

        command = CreateJobPostingCommand(
            opportunity_id=uuid4(),
            created_by=uuid4(),
            title="Title",
            description="D" * 500,
            qualifications="Q" * 150,
            location_country="France",
            contract_types=["CDI"],
        )

        with pytest.raises(OpportunityNotFoundError):
            await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_create_job_posting_already_exists(self, use_case, mock_repos):
        """Should raise error if posting already exists for opportunity."""
        opp_id = uuid4()
        opportunity = MagicMock(id=opp_id)
        existing_posting = MagicMock(id=uuid4())

        mock_repos["opportunity_repo"].get_by_id.return_value = opportunity
        mock_repos["job_posting_repo"].get_by_opportunity_id.return_value = existing_posting

        command = CreateJobPostingCommand(
            opportunity_id=opp_id,
            created_by=uuid4(),
            title="Title",
            description="D" * 500,
            qualifications="Q" * 150,
            location_country="France",
            contract_types=["CDI"],
        )

        with pytest.raises(ValueError, match="already exists"):
            await use_case.execute(command)


class TestPublishJobPostingUseCase:
    """Tests for publishing job postings to Turnover-IT."""

    @pytest.fixture
    def mock_deps(self):
        return {
            "job_posting_repo": AsyncMock(),
            "opportunity_repo": AsyncMock(),
            "user_repo": AsyncMock(),
            "turnoverit_client": AsyncMock(),
        }

    @pytest.fixture
    def use_case(self, mock_deps):
        return PublishJobPostingUseCase(
            job_posting_repository=mock_deps["job_posting_repo"],
            opportunity_repository=mock_deps["opportunity_repo"],
            user_repository=mock_deps["user_repo"],
            turnoverit_client=mock_deps["turnoverit_client"],
        )

    @pytest.mark.asyncio
    async def test_publish_job_posting_success(self, use_case, mock_deps):
        """Should publish posting to Turnover-IT."""
        posting_id = uuid4()
        posting = MagicMock(
            id=posting_id,
            opportunity_id=uuid4(),
            status=JobPostingStatus.DRAFT,
            title="Dev Python",
            description="D" * 500,
            qualifications="Q" * 150,
            location_country="France",
            location_region=None,
            location_postal_code=None,
            location_city=None,
            location_key=None,
            contract_types=[ContractType.FREELANCE],
            skills=["Python"],
            experience_level=None,
            remote=None,
            start_date=None,
            duration_months=None,
            salary_min_annual=None,
            salary_max_annual=None,
            salary_min_daily=None,
            salary_max_daily=None,
            employer_overview=None,
            application_token="test-token",
            created_by=uuid4(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            published_at=None,
            closed_at=None,
            turnoverit_reference=None,
            turnoverit_public_url=None,
        )
        posting.to_turnoverit_payload = MagicMock(return_value={})
        posting.publish = MagicMock()

        opportunity = MagicMock(title="Opp Title", reference="REF", client_name="Client")
        user = MagicMock(full_name="Admin")

        mock_deps["job_posting_repo"].get_by_id.return_value = posting
        mock_deps["opportunity_repo"].get_by_id.return_value = opportunity
        mock_deps["user_repo"].get_by_id.return_value = user
        mock_deps["turnoverit_client"].create_job.return_value = "TIT-12345"

        async def mock_save(p):
            return p

        mock_deps["job_posting_repo"].save.side_effect = mock_save

        result = await use_case.execute(posting_id)

        mock_deps["turnoverit_client"].create_job.assert_called_once()
        posting.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_already_published_raises_error(self, use_case, mock_deps):
        """Should raise error if posting is not draft."""
        posting = MagicMock(id=uuid4(), status=JobPostingStatus.PUBLISHED)
        mock_deps["job_posting_repo"].get_by_id.return_value = posting

        with pytest.raises(ValueError, match="Cannot publish"):
            await use_case.execute(posting.id)

    @pytest.mark.asyncio
    async def test_publish_not_found_raises_error(self, use_case, mock_deps):
        """Should raise error if posting doesn't exist."""
        mock_deps["job_posting_repo"].get_by_id.return_value = None

        with pytest.raises(JobPostingNotFoundError):
            await use_case.execute(uuid4())


class TestSubmitApplicationUseCase:
    """Tests for submitting job applications."""

    @pytest.fixture
    def mock_deps(self):
        return {
            "job_posting_repo": AsyncMock(),
            "job_application_repo": AsyncMock(),
            "s3_client": AsyncMock(),
            "matching_service": AsyncMock(),
        }

    @pytest.fixture
    def use_case(self, mock_deps):
        return SubmitApplicationUseCase(
            job_posting_repository=mock_deps["job_posting_repo"],
            job_application_repository=mock_deps["job_application_repo"],
            s3_client=mock_deps["s3_client"],
            matching_service=mock_deps["matching_service"],
        )

    @pytest.mark.asyncio
    async def test_submit_application_success(self, use_case, mock_deps):
        """Should submit application successfully."""
        posting_id = uuid4()
        posting = MagicMock(
            id=posting_id,
            status=JobPostingStatus.PUBLISHED,
            title="Dev Python",
            description="Description",
            qualifications="Qualifications",
            skills=["Python"],
        )

        mock_deps["job_posting_repo"].get_by_token.return_value = posting
        mock_deps["job_application_repo"].exists_by_email_and_posting.return_value = False
        mock_deps["s3_client"].upload_file.return_value = "cvs/key.pdf"
        mock_deps["matching_service"].calculate_match.return_value = {
            "score": 75,
            "strengths": ["Python"],
            "gaps": [],
            "summary": "Good match",
        }

        async def mock_save(app):
            app.id = uuid4()
            return app

        mock_deps["job_application_repo"].save.side_effect = mock_save

        with patch(
            "app.infrastructure.cv_transformer.extractors.extract_text_from_bytes",
            return_value="CV text",
        ):
            command = SubmitApplicationCommand(
                application_token="test-token",
                first_name="Jean",
                last_name="Dupont",
                email="jean@example.com",
                phone="+33612345678",
                job_title="Dev Python",
                availability="1_month",
                employment_status="freelance",
                english_level="professional",
                tjm_current=450.0,
                tjm_desired=500.0,
                cv_content=b"PDF content",
                cv_filename="cv.pdf",
                cv_content_type="application/pdf",
            )

            result = await use_case.execute(command)

        assert result.success is True
        mock_deps["s3_client"].upload_file.assert_called_once()
        mock_deps["job_application_repo"].save.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_duplicate_application(self, use_case, mock_deps):
        """Should reject duplicate applications."""
        posting = MagicMock(id=uuid4(), status=JobPostingStatus.PUBLISHED)

        mock_deps["job_posting_repo"].get_by_token.return_value = posting
        mock_deps["job_application_repo"].exists_by_email_and_posting.return_value = True

        command = SubmitApplicationCommand(
            application_token="test-token",
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            phone="+33612345678",
            job_title="Dev",
            availability="asap",
            employment_status="freelance",
            english_level="intermediate",
            cv_content=b"PDF",
            cv_filename="cv.pdf",
            cv_content_type="application/pdf",
        )

        result = await use_case.execute(command)

        assert result.success is False
        assert "déjà postulé" in result.message

    @pytest.mark.asyncio
    async def test_submit_to_closed_posting(self, use_case, mock_deps):
        """Should reject application to closed posting."""
        posting = MagicMock(status=JobPostingStatus.CLOSED)
        mock_deps["job_posting_repo"].get_by_token.return_value = posting

        command = SubmitApplicationCommand(
            application_token="test-token",
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            phone="+33612345678",
            job_title="Dev",
            availability="asap",
            employment_status="freelance",
            english_level="intermediate",
            cv_content=b"PDF",
            cv_filename="cv.pdf",
            cv_content_type="application/pdf",
        )

        with pytest.raises(JobPostingNotFoundError):
            await use_case.execute(command)


class TestUpdateApplicationStatusUseCase:
    """Tests for updating application status."""

    @pytest.fixture
    def mock_deps(self):
        return {
            "job_application_repo": AsyncMock(),
            "job_posting_repo": AsyncMock(),
            "user_repo": AsyncMock(),
            "s3_client": AsyncMock(),
        }

    @pytest.fixture
    def use_case(self, mock_deps):
        return UpdateApplicationStatusUseCase(
            job_application_repository=mock_deps["job_application_repo"],
            job_posting_repository=mock_deps["job_posting_repo"],
            user_repository=mock_deps["user_repo"],
            s3_client=mock_deps["s3_client"],
        )

    @pytest.mark.asyncio
    async def test_update_status_success(self, use_case, mock_deps):
        """Should update application status."""
        app_id = uuid4()
        user_id = uuid4()

        application = MagicMock(
            id=app_id,
            job_posting_id=uuid4(),
            status=ApplicationStatus.EN_COURS,
            cv_s3_key="cvs/key.pdf",
            cv_filename="cv.pdf",
            first_name="Jean",
            last_name="DUPONT",
            email="jean@example.com",
            phone="+33612345678",
            job_title="Dev",
            civility=None,
            # New fields
            availability="1_month",
            availability_display="Sous 1 mois",
            employment_status="freelance",
            employment_status_display="Freelance",
            english_level="professional",
            english_level_display="Professionnel",
            tjm_current=400.0,
            tjm_desired=500.0,
            salary_current=None,
            salary_desired=None,
            salary_range="N/A",
            # Legacy fields
            tjm_min=None,
            tjm_max=None,
            availability_date=None,
            # Matching & quality
            matching_score=75,
            matching_details=None,
            cv_quality_score=None,
            cv_quality=None,
            # State
            is_read=False,
            notes=None,
            boond_candidate_id=None,
            boond_sync_error=None,
            boond_synced_at=None,
            boond_sync_status="not_applicable",
            status_history=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        application.full_name = "Jean DUPONT"
        application.tjm_range = "400€ - 500€"
        application.change_status = MagicMock(return_value=True)

        posting = MagicMock(title="Dev Python")
        user = MagicMock(full_name="Admin User")

        mock_deps["job_application_repo"].get_by_id.return_value = application
        mock_deps["job_posting_repo"].get_by_id.return_value = posting
        mock_deps["user_repo"].get_by_id.return_value = user
        mock_deps["s3_client"].get_presigned_url.return_value = "https://presigned-url"

        async def mock_save(app):
            return app

        mock_deps["job_application_repo"].save.side_effect = mock_save

        command = UpdateApplicationStatusCommand(
            application_id=app_id,
            new_status=ApplicationStatus.EN_COURS,
            changed_by=user_id,
            comment="Profil intéressant",
        )

        result = await use_case.execute(command)

        application.change_status.assert_called_once_with(
            new_status=ApplicationStatus.EN_COURS,
            changed_by=user_id,
            comment="Profil intéressant",
        )
        mock_deps["job_application_repo"].save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition(self, use_case, mock_deps):
        """Should raise error on invalid status transition."""
        application = MagicMock(status=ApplicationStatus.EN_COURS)
        application.change_status = MagicMock(return_value=False)

        mock_deps["job_application_repo"].get_by_id.return_value = application

        command = UpdateApplicationStatusCommand(
            application_id=uuid4(),
            new_status=ApplicationStatus.VALIDE,
            changed_by=uuid4(),
        )

        with pytest.raises(InvalidStatusTransitionError):
            await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, use_case, mock_deps):
        """Should raise error if application not found."""
        mock_deps["job_application_repo"].get_by_id.return_value = None

        command = UpdateApplicationStatusCommand(
            application_id=uuid4(),
            new_status=ApplicationStatus.EN_COURS,
            changed_by=uuid4(),
        )

        with pytest.raises(JobApplicationNotFoundError):
            await use_case.execute(command)


class TestGetApplicationCvUrlUseCase:
    """Tests for getting CV download URL."""

    @pytest.fixture
    def mock_deps(self):
        return {
            "job_application_repo": AsyncMock(),
            "s3_client": AsyncMock(),
        }

    @pytest.fixture
    def use_case(self, mock_deps):
        return GetApplicationCvUrlUseCase(
            job_application_repository=mock_deps["job_application_repo"],
            s3_client=mock_deps["s3_client"],
        )

    @pytest.mark.asyncio
    async def test_get_cv_url_success(self, use_case, mock_deps):
        """Should return presigned URL."""
        app_id = uuid4()
        application = MagicMock(cv_s3_key="cvs/key.pdf")

        mock_deps["job_application_repo"].get_by_id.return_value = application
        mock_deps["s3_client"].get_presigned_url.return_value = "https://presigned-url"

        result = await use_case.execute(app_id, expires_in=3600)

        assert result == "https://presigned-url"
        mock_deps["s3_client"].get_presigned_url.assert_called_once_with(
            key="cvs/key.pdf",
            expires_in=3600,
        )

    @pytest.mark.asyncio
    async def test_get_cv_url_not_found(self, use_case, mock_deps):
        """Should raise error if application not found."""
        mock_deps["job_application_repo"].get_by_id.return_value = None

        with pytest.raises(JobApplicationNotFoundError):
            await use_case.execute(uuid4())
