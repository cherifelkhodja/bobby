"""Job posting use cases for HR feature."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from app.application.read_models.hr import (
    JobPostingListReadModel,
    JobPostingPublicReadModel,
    JobPostingReadModel,
    OpportunityForHRReadModel,
    OpportunityListForHRReadModel,
)
from app.config import settings
from app.domain.entities import JobPosting, JobPostingStatus
from app.domain.entities.job_posting import ContractType, ExperienceLevel, RemotePolicy
from app.domain.exceptions import (
    JobPostingNotFoundError,
    OpportunityNotFoundError,
    TurnoverITError,
)
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.database.repositories import (
    JobApplicationRepository,
    JobPostingRepository,
    OpportunityRepository,
    UserRepository,
)
from app.infrastructure.turnoverit.client import TurnoverITClient


class ListOpenOpportunitiesForHRUseCase:
    """List opportunities from BoondManager where user is HR manager.

    Fetches opportunities directly from BoondManager API filtered by hrManager,
    then enriches with local job posting status.
    """

    def __init__(
        self,
        boond_client: BoondClient,
        job_posting_repository: JobPostingRepository,
        job_application_repository: JobApplicationRepository,
    ) -> None:
        self.boond_client = boond_client
        self.job_posting_repository = job_posting_repository
        self.job_application_repository = job_application_repository

    async def execute(
        self,
        hr_manager_boond_id: Optional[str] = None,
        is_admin: bool = False,
        search: Optional[str] = None,
    ) -> OpportunityListForHRReadModel:
        """List opportunities from BoondManager where user is HR manager.

        Args:
            hr_manager_boond_id: The user's BoondManager resource ID.
                Required unless is_admin is True.
            is_admin: If True, fetch ALL opportunities (admin view).
            search: Optional search term to filter opportunities.

        Returns:
            Paginated list of opportunities with job posting status.

        Raises:
            ValueError: If hr_manager_boond_id is not set and user is not admin.
        """
        if not is_admin and not hr_manager_boond_id:
            raise ValueError("L'utilisateur n'a pas d'identifiant BoondManager configuré")

        # Fetch opportunities from BoondManager
        if is_admin:
            # Admin can see all opportunities (use main manager filter with fetch_all)
            boond_opportunities = await self.boond_client.get_manager_opportunities(
                fetch_all=True,
            )
        else:
            # HR users see only opportunities where they are HR manager
            boond_opportunities = await self.boond_client.get_hr_manager_opportunities(
                hr_manager_boond_id=hr_manager_boond_id,
            )

        # Filter by search term if provided
        if search:
            search_lower = search.lower()
            boond_opportunities = [
                opp for opp in boond_opportunities
                if search_lower in opp.get("title", "").lower()
                or search_lower in opp.get("reference", "").lower()
                or search_lower in opp.get("company_name", "").lower()
            ]

        # Batch lookup job postings by boond opportunity IDs
        boond_ids = [opp["id"] for opp in boond_opportunities]
        job_postings_map = await self.job_posting_repository.get_all_by_boond_opportunity_ids(
            boond_ids
        )

        # Build items with job posting info
        items = []
        for opp in boond_opportunities:
            boond_id = opp["id"]
            job_posting = job_postings_map.get(boond_id)

            applications_count = 0
            new_applications_count = 0
            if job_posting:
                applications_count = await self.job_application_repository.count_by_posting(
                    job_posting.id
                )
                new_applications_count = await self.job_application_repository.count_new_by_posting(
                    job_posting.id
                )

            # Parse dates if they exist
            start_date = None
            end_date = None
            if opp.get("start_date"):
                try:
                    start_date = date.fromisoformat(opp["start_date"])
                except (ValueError, TypeError):
                    pass
            if opp.get("end_date"):
                try:
                    end_date = date.fromisoformat(opp["end_date"])
                except (ValueError, TypeError):
                    pass

            items.append(
                OpportunityForHRReadModel(
                    id=boond_id,
                    title=opp.get("title", ""),
                    reference=opp.get("reference", ""),
                    client_name=opp.get("company_name"),
                    description=opp.get("description"),
                    start_date=start_date,
                    end_date=end_date,
                    manager_name=opp.get("manager_name"),
                    hr_manager_name=opp.get("hr_manager_name"),
                    state=opp.get("state"),
                    state_name=opp.get("state_name"),
                    state_color=opp.get("state_color"),
                    has_job_posting=job_posting is not None,
                    job_posting_id=str(job_posting.id) if job_posting else None,
                    job_posting_status=str(job_posting.status) if job_posting else None,
                    job_posting_status_display=job_posting.status.display_name if job_posting else None,
                    applications_count=applications_count,
                    new_applications_count=new_applications_count,
                )
            )

        return OpportunityListForHRReadModel(
            items=items,
            total=len(items),
            page=1,  # No pagination for BoondManager API
            page_size=len(items),
        )


@dataclass
class CreateJobPostingCommand:
    """Command for creating a job posting."""

    opportunity_id: UUID
    created_by: UUID
    title: str
    description: str
    qualifications: str
    location_country: str
    location_region: Optional[str] = None
    location_postal_code: Optional[str] = None
    location_city: Optional[str] = None
    location_key: Optional[str] = None  # Turnover-IT location key for normalization
    contract_types: list[str] = None  # type: ignore
    skills: list[str] = None  # type: ignore
    experience_level: Optional[str] = None
    remote: Optional[str] = None
    start_date: Optional[date] = None
    duration_months: Optional[int] = None
    salary_min_annual: Optional[float] = None
    salary_max_annual: Optional[float] = None
    salary_min_daily: Optional[float] = None
    salary_max_daily: Optional[float] = None
    employer_overview: Optional[str] = None

    def __post_init__(self) -> None:
        if self.contract_types is None:
            self.contract_types = []
        if self.skills is None:
            self.skills = []


class CreateJobPostingUseCase:
    """Create a draft job posting from an opportunity."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        opportunity_repository: OpportunityRepository,
        user_repository: UserRepository,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.opportunity_repository = opportunity_repository
        self.user_repository = user_repository

    async def execute(self, command: CreateJobPostingCommand) -> JobPostingReadModel:
        """Create a new job posting draft."""
        # Check if opportunity exists
        opportunity = await self.opportunity_repository.get_by_id(command.opportunity_id)
        if not opportunity:
            raise OpportunityNotFoundError(str(command.opportunity_id))

        # Check if a posting already exists for this opportunity
        existing = await self.job_posting_repository.get_by_opportunity_id(
            command.opportunity_id
        )
        if existing:
            raise ValueError(
                f"A job posting already exists for opportunity {command.opportunity_id}"
            )

        # Parse enums
        contract_types = [ContractType(ct) for ct in command.contract_types]
        experience_level = (
            ExperienceLevel(command.experience_level)
            if command.experience_level
            else None
        )
        remote = RemotePolicy(command.remote) if command.remote else None

        # Create job posting entity
        job_posting = JobPosting(
            opportunity_id=command.opportunity_id,
            title=command.title,
            description=command.description,
            qualifications=command.qualifications,
            location_country=command.location_country,
            location_region=command.location_region,
            location_postal_code=command.location_postal_code,
            location_city=command.location_city,
            location_key=command.location_key,
            contract_types=contract_types,
            skills=command.skills,
            experience_level=experience_level,
            remote=remote,
            start_date=command.start_date,
            duration_months=command.duration_months,
            salary_min_annual=command.salary_min_annual,
            salary_max_annual=command.salary_max_annual,
            salary_min_daily=command.salary_min_daily,
            salary_max_daily=command.salary_max_daily,
            employer_overview=command.employer_overview,
            created_by=command.created_by,
        )

        saved = await self.job_posting_repository.save(job_posting)
        return await self._to_read_model(saved, opportunity.title, opportunity.reference, opportunity.client_name)

    async def _to_read_model(
        self,
        posting: JobPosting,
        opportunity_title: Optional[str] = None,
        opportunity_reference: Optional[str] = None,
        client_name: Optional[str] = None,
    ) -> JobPostingReadModel:
        created_by_name = None
        if posting.created_by:
            user = await self.user_repository.get_by_id(posting.created_by)
            if user:
                created_by_name = user.full_name

        application_url = f"{settings.FRONTEND_URL}/postuler/{posting.application_token}"

        return JobPostingReadModel(
            id=str(posting.id),
            opportunity_id=str(posting.opportunity_id),
            opportunity_title=opportunity_title,
            opportunity_reference=opportunity_reference,
            client_name=client_name,
            title=posting.title,
            description=posting.description,
            qualifications=posting.qualifications,
            location_country=posting.location_country,
            location_region=posting.location_region,
            location_postal_code=posting.location_postal_code,
            location_city=posting.location_city,
            location_key=posting.location_key,
            contract_types=[str(ct) for ct in posting.contract_types],
            skills=posting.skills,
            experience_level=str(posting.experience_level) if posting.experience_level else None,
            remote=str(posting.remote) if posting.remote else None,
            start_date=posting.start_date,
            duration_months=posting.duration_months,
            salary_min_annual=posting.salary_min_annual,
            salary_max_annual=posting.salary_max_annual,
            salary_min_daily=posting.salary_min_daily,
            salary_max_daily=posting.salary_max_daily,
            employer_overview=posting.employer_overview,
            status=str(posting.status),
            status_display=posting.status.display_name,
            turnoverit_reference=posting.turnoverit_reference,
            turnoverit_public_url=posting.turnoverit_public_url,
            application_token=posting.application_token,
            application_url=application_url,
            created_by=str(posting.created_by) if posting.created_by else None,
            created_by_name=created_by_name,
            created_at=posting.created_at,
            updated_at=posting.updated_at,
            published_at=posting.published_at,
            closed_at=posting.closed_at,
        )


class GetJobPostingUseCase:
    """Get a single job posting with details."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        opportunity_repository: OpportunityRepository,
        job_application_repository: JobApplicationRepository,
        user_repository: UserRepository,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.opportunity_repository = opportunity_repository
        self.job_application_repository = job_application_repository
        self.user_repository = user_repository

    async def execute(self, posting_id: UUID) -> JobPostingReadModel:
        """Get job posting by ID."""
        posting = await self.job_posting_repository.get_by_id(posting_id)
        if not posting:
            raise JobPostingNotFoundError(str(posting_id))

        opportunity = await self.opportunity_repository.get_by_id(posting.opportunity_id)

        stats = await self.job_application_repository.get_stats_by_posting(posting_id)

        return await self._to_read_model(
            posting,
            opportunity.title if opportunity else None,
            opportunity.reference if opportunity else None,
            opportunity.client_name if opportunity else None,
            stats,
        )

    async def _to_read_model(
        self,
        posting: JobPosting,
        opportunity_title: Optional[str] = None,
        opportunity_reference: Optional[str] = None,
        client_name: Optional[str] = None,
        stats: Optional[dict] = None,
    ) -> JobPostingReadModel:
        created_by_name = None
        if posting.created_by:
            user = await self.user_repository.get_by_id(posting.created_by)
            if user:
                created_by_name = user.full_name

        application_url = f"{settings.FRONTEND_URL}/postuler/{posting.application_token}"

        return JobPostingReadModel(
            id=str(posting.id),
            opportunity_id=str(posting.opportunity_id),
            opportunity_title=opportunity_title,
            opportunity_reference=opportunity_reference,
            client_name=client_name,
            title=posting.title,
            description=posting.description,
            qualifications=posting.qualifications,
            location_country=posting.location_country,
            location_region=posting.location_region,
            location_postal_code=posting.location_postal_code,
            location_city=posting.location_city,
            location_key=posting.location_key,
            contract_types=[str(ct) for ct in posting.contract_types],
            skills=posting.skills,
            experience_level=str(posting.experience_level) if posting.experience_level else None,
            remote=str(posting.remote) if posting.remote else None,
            start_date=posting.start_date,
            duration_months=posting.duration_months,
            salary_min_annual=posting.salary_min_annual,
            salary_max_annual=posting.salary_max_annual,
            salary_min_daily=posting.salary_min_daily,
            salary_max_daily=posting.salary_max_daily,
            employer_overview=posting.employer_overview,
            status=str(posting.status),
            status_display=posting.status.display_name,
            turnoverit_reference=posting.turnoverit_reference,
            turnoverit_public_url=posting.turnoverit_public_url,
            application_token=posting.application_token,
            application_url=application_url,
            created_by=str(posting.created_by) if posting.created_by else None,
            created_by_name=created_by_name,
            created_at=posting.created_at,
            updated_at=posting.updated_at,
            published_at=posting.published_at,
            closed_at=posting.closed_at,
            applications_total=stats.get("total", 0) if stats else 0,
            applications_new=stats.get("nouveau", 0) if stats else 0,
        )


class GetJobPostingByTokenUseCase:
    """Get job posting by application token (for public form)."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
    ) -> None:
        self.job_posting_repository = job_posting_repository

    async def execute(self, token: str) -> JobPostingPublicReadModel:
        """Get public job posting info by token."""
        posting = await self.job_posting_repository.get_by_token(token)
        if not posting:
            raise JobPostingNotFoundError(f"token:{token}")

        # Only return published postings
        if posting.status != JobPostingStatus.PUBLISHED:
            raise JobPostingNotFoundError(f"token:{token}")

        return JobPostingPublicReadModel(
            title=posting.title,
            description=posting.description,
            qualifications=posting.qualifications,
            location_country=posting.location_country,
            location_region=posting.location_region,
            location_city=posting.location_city,
            location_key=posting.location_key,
            contract_types=[str(ct) for ct in posting.contract_types],
            skills=posting.skills,
            experience_level=str(posting.experience_level) if posting.experience_level else None,
            remote=str(posting.remote) if posting.remote else None,
            start_date=posting.start_date,
            duration_months=posting.duration_months,
            salary_min_daily=posting.salary_min_daily,
            salary_max_daily=posting.salary_max_daily,
            employer_overview=posting.employer_overview,
        )


class ListJobPostingsUseCase:
    """List all job postings."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        opportunity_repository: OpportunityRepository,
        job_application_repository: JobApplicationRepository,
        user_repository: UserRepository,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.opportunity_repository = opportunity_repository
        self.job_application_repository = job_application_repository
        self.user_repository = user_repository

    async def execute(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[JobPostingStatus] = None,
    ) -> JobPostingListReadModel:
        """List job postings with pagination."""
        skip = (page - 1) * page_size

        postings = await self.job_posting_repository.list_all(
            skip=skip,
            limit=page_size,
            status=status,
        )
        total = await self.job_posting_repository.count_all(status=status)

        items = []
        for posting in postings:
            opportunity = await self.opportunity_repository.get_by_id(posting.opportunity_id)
            stats = await self.job_application_repository.get_stats_by_posting(posting.id)

            created_by_name = None
            if posting.created_by:
                user = await self.user_repository.get_by_id(posting.created_by)
                if user:
                    created_by_name = user.full_name

            application_url = f"{settings.FRONTEND_URL}/postuler/{posting.application_token}"

            items.append(
                JobPostingReadModel(
                    id=str(posting.id),
                    opportunity_id=str(posting.opportunity_id),
                    opportunity_title=opportunity.title if opportunity else None,
                    opportunity_reference=opportunity.reference if opportunity else None,
                    client_name=opportunity.client_name if opportunity else None,
                    title=posting.title,
                    description=posting.description,
                    qualifications=posting.qualifications,
                    location_country=posting.location_country,
                    location_region=posting.location_region,
                    location_postal_code=posting.location_postal_code,
                    location_city=posting.location_city,
                    contract_types=[str(ct) for ct in posting.contract_types],
                    skills=posting.skills,
                    experience_level=str(posting.experience_level) if posting.experience_level else None,
                    remote=str(posting.remote) if posting.remote else None,
                    start_date=posting.start_date,
                    duration_months=posting.duration_months,
                    salary_min_annual=posting.salary_min_annual,
                    salary_max_annual=posting.salary_max_annual,
                    salary_min_daily=posting.salary_min_daily,
                    salary_max_daily=posting.salary_max_daily,
                    employer_overview=posting.employer_overview,
                    status=str(posting.status),
                    status_display=posting.status.display_name,
                    turnoverit_reference=posting.turnoverit_reference,
                    turnoverit_public_url=posting.turnoverit_public_url,
                    application_token=posting.application_token,
                    application_url=application_url,
                    created_by=str(posting.created_by) if posting.created_by else None,
                    created_by_name=created_by_name,
                    created_at=posting.created_at,
                    updated_at=posting.updated_at,
                    published_at=posting.published_at,
                    closed_at=posting.closed_at,
                    applications_total=stats.get("total", 0),
                    applications_new=stats.get("nouveau", 0),
                )
            )

        return JobPostingListReadModel(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )


class PublishJobPostingUseCase:
    """Publish a job posting to Turnover-IT."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        opportunity_repository: OpportunityRepository,
        user_repository: UserRepository,
        turnoverit_client: TurnoverITClient,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.opportunity_repository = opportunity_repository
        self.user_repository = user_repository
        self.turnoverit_client = turnoverit_client

    async def execute(self, posting_id: UUID) -> JobPostingReadModel:
        """Publish job posting to Turnover-IT."""
        posting = await self.job_posting_repository.get_by_id(posting_id)
        if not posting:
            raise JobPostingNotFoundError(str(posting_id))

        if posting.status != JobPostingStatus.DRAFT:
            raise ValueError(f"Cannot publish posting with status {posting.status}")

        # Get opportunity for context
        opportunity = await self.opportunity_repository.get_by_id(posting.opportunity_id)

        # Build Turnover-IT payload
        application_base_url = f"{settings.FRONTEND_URL}/postuler"
        payload = posting.to_turnoverit_payload(application_base_url)

        try:
            # Create job on Turnover-IT
            turnoverit_reference = await self.turnoverit_client.create_job(payload)

            # Build public URL (assuming Turnover-IT provides this format)
            turnoverit_public_url = f"https://www.turnover-it.com/job/{turnoverit_reference}"

            # Update posting
            posting.publish(turnoverit_public_url)
            posting.turnoverit_reference = turnoverit_reference

            saved = await self.job_posting_repository.save(posting)

            return await self._to_read_model(
                saved,
                opportunity.title if opportunity else None,
                opportunity.reference if opportunity else None,
                opportunity.client_name if opportunity else None,
            )

        except Exception as e:
            raise TurnoverITError(f"Failed to publish job: {str(e)}")

    async def _to_read_model(
        self,
        posting: JobPosting,
        opportunity_title: Optional[str] = None,
        opportunity_reference: Optional[str] = None,
        client_name: Optional[str] = None,
    ) -> JobPostingReadModel:
        created_by_name = None
        if posting.created_by:
            user = await self.user_repository.get_by_id(posting.created_by)
            if user:
                created_by_name = user.full_name

        application_url = f"{settings.FRONTEND_URL}/postuler/{posting.application_token}"

        return JobPostingReadModel(
            id=str(posting.id),
            opportunity_id=str(posting.opportunity_id),
            opportunity_title=opportunity_title,
            opportunity_reference=opportunity_reference,
            client_name=client_name,
            title=posting.title,
            description=posting.description,
            qualifications=posting.qualifications,
            location_country=posting.location_country,
            location_region=posting.location_region,
            location_postal_code=posting.location_postal_code,
            location_city=posting.location_city,
            location_key=posting.location_key,
            contract_types=[str(ct) for ct in posting.contract_types],
            skills=posting.skills,
            experience_level=str(posting.experience_level) if posting.experience_level else None,
            remote=str(posting.remote) if posting.remote else None,
            start_date=posting.start_date,
            duration_months=posting.duration_months,
            salary_min_annual=posting.salary_min_annual,
            salary_max_annual=posting.salary_max_annual,
            salary_min_daily=posting.salary_min_daily,
            salary_max_daily=posting.salary_max_daily,
            employer_overview=posting.employer_overview,
            status=str(posting.status),
            status_display=posting.status.display_name,
            turnoverit_reference=posting.turnoverit_reference,
            turnoverit_public_url=posting.turnoverit_public_url,
            application_token=posting.application_token,
            application_url=application_url,
            created_by=str(posting.created_by) if posting.created_by else None,
            created_by_name=created_by_name,
            created_at=posting.created_at,
            updated_at=posting.updated_at,
            published_at=posting.published_at,
            closed_at=posting.closed_at,
        )


class CloseJobPostingUseCase:
    """Close a published job posting."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        opportunity_repository: OpportunityRepository,
        user_repository: UserRepository,
        turnoverit_client: TurnoverITClient,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.opportunity_repository = opportunity_repository
        self.user_repository = user_repository
        self.turnoverit_client = turnoverit_client

    async def execute(self, posting_id: UUID) -> JobPostingReadModel:
        """Close job posting on Turnover-IT."""
        posting = await self.job_posting_repository.get_by_id(posting_id)
        if not posting:
            raise JobPostingNotFoundError(str(posting_id))

        if posting.status != JobPostingStatus.PUBLISHED:
            raise ValueError(f"Cannot close posting with status {posting.status}")

        # Get opportunity for context
        opportunity = await self.opportunity_repository.get_by_id(posting.opportunity_id)

        # Close on Turnover-IT if reference exists
        if posting.turnoverit_reference:
            try:
                await self.turnoverit_client.close_job(posting.turnoverit_reference)
            except Exception as e:
                # Log but don't fail - job might already be closed on their side
                pass

        # Update posting status
        posting.close()
        saved = await self.job_posting_repository.save(posting)

        return await self._to_read_model(
            saved,
            opportunity.title if opportunity else None,
            opportunity.reference if opportunity else None,
            opportunity.client_name if opportunity else None,
        )

    async def _to_read_model(
        self,
        posting: JobPosting,
        opportunity_title: Optional[str] = None,
        opportunity_reference: Optional[str] = None,
        client_name: Optional[str] = None,
    ) -> JobPostingReadModel:
        created_by_name = None
        if posting.created_by:
            user = await self.user_repository.get_by_id(posting.created_by)
            if user:
                created_by_name = user.full_name

        application_url = f"{settings.FRONTEND_URL}/postuler/{posting.application_token}"

        return JobPostingReadModel(
            id=str(posting.id),
            opportunity_id=str(posting.opportunity_id),
            opportunity_title=opportunity_title,
            opportunity_reference=opportunity_reference,
            client_name=client_name,
            title=posting.title,
            description=posting.description,
            qualifications=posting.qualifications,
            location_country=posting.location_country,
            location_region=posting.location_region,
            location_postal_code=posting.location_postal_code,
            location_city=posting.location_city,
            location_key=posting.location_key,
            contract_types=[str(ct) for ct in posting.contract_types],
            skills=posting.skills,
            experience_level=str(posting.experience_level) if posting.experience_level else None,
            remote=str(posting.remote) if posting.remote else None,
            start_date=posting.start_date,
            duration_months=posting.duration_months,
            salary_min_annual=posting.salary_min_annual,
            salary_max_annual=posting.salary_max_annual,
            salary_min_daily=posting.salary_min_daily,
            salary_max_daily=posting.salary_max_daily,
            employer_overview=posting.employer_overview,
            status=str(posting.status),
            status_display=posting.status.display_name,
            turnoverit_reference=posting.turnoverit_reference,
            turnoverit_public_url=posting.turnoverit_public_url,
            application_token=posting.application_token,
            application_url=application_url,
            created_by=str(posting.created_by) if posting.created_by else None,
            created_by_name=created_by_name,
            created_at=posting.created_at,
            updated_at=posting.updated_at,
            published_at=posting.published_at,
            closed_at=posting.closed_at,
        )


@dataclass
class UpdateJobPostingCommand:
    """Command for updating a job posting."""

    posting_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    qualifications: Optional[str] = None
    location_country: Optional[str] = None
    location_region: Optional[str] = None
    location_postal_code: Optional[str] = None
    location_city: Optional[str] = None
    location_key: Optional[str] = None  # Turnover-IT location key for normalization
    contract_types: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    experience_level: Optional[str] = None
    remote: Optional[str] = None
    start_date: Optional[date] = None
    duration_months: Optional[int] = None
    salary_min_annual: Optional[float] = None
    salary_max_annual: Optional[float] = None
    salary_min_daily: Optional[float] = None
    salary_max_daily: Optional[float] = None
    employer_overview: Optional[str] = None


class UpdateJobPostingUseCase:
    """Update a draft job posting."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        opportunity_repository: OpportunityRepository,
        user_repository: UserRepository,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.opportunity_repository = opportunity_repository
        self.user_repository = user_repository

    async def execute(self, command: UpdateJobPostingCommand) -> JobPostingReadModel:
        """Update job posting (only drafts can be updated)."""
        posting = await self.job_posting_repository.get_by_id(command.posting_id)
        if not posting:
            raise JobPostingNotFoundError(str(command.posting_id))

        if posting.status != JobPostingStatus.DRAFT:
            raise ValueError(f"Cannot update posting with status {posting.status}")

        # Update fields if provided
        if command.title is not None:
            posting.title = command.title
        if command.description is not None:
            posting.description = command.description
        if command.qualifications is not None:
            posting.qualifications = command.qualifications
        if command.location_country is not None:
            posting.location_country = command.location_country
        if command.location_region is not None:
            posting.location_region = command.location_region
        if command.location_postal_code is not None:
            posting.location_postal_code = command.location_postal_code
        if command.location_city is not None:
            posting.location_city = command.location_city
        if command.location_key is not None:
            posting.location_key = command.location_key
        if command.contract_types is not None:
            posting.contract_types = [ContractType(ct) for ct in command.contract_types]
        if command.skills is not None:
            posting.skills = command.skills
        if command.experience_level is not None:
            posting.experience_level = ExperienceLevel(command.experience_level) if command.experience_level else None
        if command.remote is not None:
            posting.remote = RemotePolicy(command.remote) if command.remote else None
        if command.start_date is not None:
            posting.start_date = command.start_date
        if command.duration_months is not None:
            posting.duration_months = command.duration_months
        if command.salary_min_annual is not None:
            posting.salary_min_annual = command.salary_min_annual
        if command.salary_max_annual is not None:
            posting.salary_max_annual = command.salary_max_annual
        if command.salary_min_daily is not None:
            posting.salary_min_daily = command.salary_min_daily
        if command.salary_max_daily is not None:
            posting.salary_max_daily = command.salary_max_daily
        if command.employer_overview is not None:
            posting.employer_overview = command.employer_overview

        posting.updated_at = datetime.utcnow()

        saved = await self.job_posting_repository.save(posting)

        opportunity = await self.opportunity_repository.get_by_id(posting.opportunity_id)

        return await self._to_read_model(
            saved,
            opportunity.title if opportunity else None,
            opportunity.reference if opportunity else None,
            opportunity.client_name if opportunity else None,
        )

    async def _to_read_model(
        self,
        posting: JobPosting,
        opportunity_title: Optional[str] = None,
        opportunity_reference: Optional[str] = None,
        client_name: Optional[str] = None,
    ) -> JobPostingReadModel:
        created_by_name = None
        if posting.created_by:
            user = await self.user_repository.get_by_id(posting.created_by)
            if user:
                created_by_name = user.full_name

        application_url = f"{settings.FRONTEND_URL}/postuler/{posting.application_token}"

        return JobPostingReadModel(
            id=str(posting.id),
            opportunity_id=str(posting.opportunity_id),
            opportunity_title=opportunity_title,
            opportunity_reference=opportunity_reference,
            client_name=client_name,
            title=posting.title,
            description=posting.description,
            qualifications=posting.qualifications,
            location_country=posting.location_country,
            location_region=posting.location_region,
            location_postal_code=posting.location_postal_code,
            location_city=posting.location_city,
            location_key=posting.location_key,
            contract_types=[str(ct) for ct in posting.contract_types],
            skills=posting.skills,
            experience_level=str(posting.experience_level) if posting.experience_level else None,
            remote=str(posting.remote) if posting.remote else None,
            start_date=posting.start_date,
            duration_months=posting.duration_months,
            salary_min_annual=posting.salary_min_annual,
            salary_max_annual=posting.salary_max_annual,
            salary_min_daily=posting.salary_min_daily,
            salary_max_daily=posting.salary_max_daily,
            employer_overview=posting.employer_overview,
            status=str(posting.status),
            status_display=posting.status.display_name,
            turnoverit_reference=posting.turnoverit_reference,
            turnoverit_public_url=posting.turnoverit_public_url,
            application_token=posting.application_token,
            application_url=application_url,
            created_by=str(posting.created_by) if posting.created_by else None,
            created_by_name=created_by_name,
            created_at=posting.created_at,
            updated_at=posting.updated_at,
            published_at=posting.published_at,
            closed_at=posting.closed_at,
        )
