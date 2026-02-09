"""Job Posting repository implementation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import JobPosting, JobPostingStatus
from app.infrastructure.database.models import JobPostingModel, OpportunityModel


class JobPostingRepository:
    """Job Posting repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, posting_id: UUID) -> JobPosting | None:
        """Get job posting by ID."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.id == posting_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_token(self, token: str) -> JobPosting | None:
        """Get job posting by application token."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.application_token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_opportunity_id(self, opportunity_id: UUID) -> JobPosting | None:
        """Get job posting by linked opportunity ID."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.opportunity_id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_boond_opportunity_id(self, boond_opportunity_id: str) -> JobPosting | None:
        """Get job posting by BoondManager opportunity external ID.

        Joins with opportunities table to find by external_id.
        """
        result = await self.session.execute(
            select(JobPostingModel)
            .join(OpportunityModel, JobPostingModel.opportunity_id == OpportunityModel.id)
            .where(OpportunityModel.external_id == boond_opportunity_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all_by_boond_opportunity_ids(
        self, boond_opportunity_ids: list[str]
    ) -> dict[str, JobPosting]:
        """Get all job postings by BoondManager opportunity external IDs.

        Efficient batch lookup for multiple opportunities.

        Returns:
            Dict mapping boond_opportunity_id -> JobPosting
        """
        if not boond_opportunity_ids:
            return {}

        result = await self.session.execute(
            select(JobPostingModel, OpportunityModel.external_id)
            .join(OpportunityModel, JobPostingModel.opportunity_id == OpportunityModel.id)
            .where(OpportunityModel.external_id.in_(boond_opportunity_ids))
        )
        postings_map = {}
        for row in result.all():
            posting_model = row[0]
            external_id = row[1]
            postings_map[external_id] = self._to_entity(posting_model)
        return postings_map

    async def get_by_turnoverit_reference(self, reference: str) -> JobPosting | None:
        """Get job posting by Turnover-IT reference."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.turnoverit_reference == reference)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, posting: JobPosting) -> JobPosting:
        """Save job posting (create or update)."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.id == posting.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.opportunity_id = posting.opportunity_id
            model.title = posting.title
            model.description = posting.description
            model.qualifications = posting.qualifications
            model.location_country = posting.location_country
            model.location_region = posting.location_region
            model.location_postal_code = posting.location_postal_code
            model.location_city = posting.location_city
            model.location_key = posting.location_key
            model.contract_types = posting.contract_types
            model.skills = posting.skills
            model.experience_level = posting.experience_level
            model.remote = posting.remote
            model.start_date = posting.start_date
            model.duration_months = posting.duration_months
            model.salary_min_annual = posting.salary_min_annual
            model.salary_max_annual = posting.salary_max_annual
            model.salary_min_daily = posting.salary_min_daily
            model.salary_max_daily = posting.salary_max_daily
            model.employer_overview = posting.employer_overview
            model.status = str(posting.status)
            model.turnoverit_reference = posting.turnoverit_reference
            model.turnoverit_public_url = posting.turnoverit_public_url
            model.application_token = posting.application_token
            model.created_by = posting.created_by
            model.published_at = posting.published_at
            model.closed_at = posting.closed_at
            model.updated_at = datetime.utcnow()
        else:
            model = JobPostingModel(
                id=posting.id,
                opportunity_id=posting.opportunity_id,
                title=posting.title,
                description=posting.description,
                qualifications=posting.qualifications,
                location_country=posting.location_country,
                location_region=posting.location_region,
                location_postal_code=posting.location_postal_code,
                location_city=posting.location_city,
                location_key=posting.location_key,
                contract_types=posting.contract_types,
                skills=posting.skills,
                experience_level=posting.experience_level,
                remote=posting.remote,
                start_date=posting.start_date,
                duration_months=posting.duration_months,
                salary_min_annual=posting.salary_min_annual,
                salary_max_annual=posting.salary_max_annual,
                salary_min_daily=posting.salary_min_daily,
                salary_max_daily=posting.salary_max_daily,
                employer_overview=posting.employer_overview,
                status=str(posting.status),
                turnoverit_reference=posting.turnoverit_reference,
                turnoverit_public_url=posting.turnoverit_public_url,
                application_token=posting.application_token,
                created_by=posting.created_by,
                created_at=posting.created_at,
                updated_at=posting.updated_at,
                published_at=posting.published_at,
                closed_at=posting.closed_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, posting_id: UUID) -> bool:
        """Delete job posting by ID."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.id == posting_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: JobPostingStatus | None = None,
    ) -> list[JobPosting]:
        """List all job postings with optional status filter."""
        query = select(JobPostingModel)
        if status:
            query = query.where(JobPostingModel.status == str(status))
        query = query.offset(skip).limit(limit).order_by(JobPostingModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_published(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobPosting]:
        """List published job postings."""
        query = (
            select(JobPostingModel)
            .where(JobPostingModel.status == str(JobPostingStatus.PUBLISHED))
            .offset(skip)
            .limit(limit)
            .order_by(JobPostingModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_creator(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobPosting]:
        """List job postings created by a specific user."""
        query = (
            select(JobPostingModel)
            .where(JobPostingModel.created_by == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(JobPostingModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_all(self, status: JobPostingStatus | None = None) -> int:
        """Count all job postings with optional status filter."""
        query = select(func.count(JobPostingModel.id))
        if status:
            query = query.where(JobPostingModel.status == str(status))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_by_creator(self, user_id: UUID) -> int:
        """Count job postings created by a specific user."""
        result = await self.session.execute(
            select(func.count(JobPostingModel.id)).where(JobPostingModel.created_by == user_id)
        )
        return result.scalar() or 0

    def _to_entity(self, model: JobPostingModel) -> JobPosting:
        """Convert model to entity."""
        return JobPosting(
            id=model.id,
            opportunity_id=model.opportunity_id,
            title=model.title,
            description=model.description,
            qualifications=model.qualifications,
            location_country=model.location_country,
            location_region=model.location_region,
            location_postal_code=model.location_postal_code,
            location_city=model.location_city,
            location_key=model.location_key,
            contract_types=model.contract_types or [],
            skills=model.skills or [],
            experience_level=model.experience_level,
            remote=model.remote,
            start_date=model.start_date,
            duration_months=model.duration_months,
            salary_min_annual=model.salary_min_annual,
            salary_max_annual=model.salary_max_annual,
            salary_min_daily=model.salary_min_daily,
            salary_max_daily=model.salary_max_daily,
            employer_overview=model.employer_overview,
            status=JobPostingStatus(model.status),
            turnoverit_reference=model.turnoverit_reference,
            turnoverit_public_url=model.turnoverit_public_url,
            application_token=model.application_token,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            published_at=model.published_at,
            closed_at=model.closed_at,
        )
