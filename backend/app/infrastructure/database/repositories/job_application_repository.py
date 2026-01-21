"""Job Application repository implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import ApplicationStatus, JobApplication
from app.infrastructure.database.models import JobApplicationModel


class JobApplicationRepository:
    """Job Application repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, application_id: UUID) -> Optional[JobApplication]:
        """Get job application by ID."""
        result = await self.session.execute(
            select(JobApplicationModel).where(JobApplicationModel.id == application_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email_and_posting(
        self,
        email: str,
        posting_id: UUID,
    ) -> Optional[JobApplication]:
        """Get application by email and posting (to check for duplicates)."""
        result = await self.session.execute(
            select(JobApplicationModel).where(
                JobApplicationModel.email == email,
                JobApplicationModel.job_posting_id == posting_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, application: JobApplication) -> JobApplication:
        """Save job application (create or update)."""
        result = await self.session.execute(
            select(JobApplicationModel).where(JobApplicationModel.id == application.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.job_posting_id = application.job_posting_id
            model.first_name = application.first_name
            model.last_name = application.last_name
            model.email = application.email
            model.phone = application.phone
            model.job_title = application.job_title
            # New fields
            model.availability = application.availability
            model.employment_status = application.employment_status
            model.english_level = application.english_level
            model.tjm_current = application.tjm_current
            model.tjm_desired = application.tjm_desired
            model.salary_current = application.salary_current
            model.salary_desired = application.salary_desired
            # Legacy fields
            model.tjm_min = application.tjm_min
            model.tjm_max = application.tjm_max
            model.availability_date = application.availability_date
            model.cv_s3_key = application.cv_s3_key
            model.cv_filename = application.cv_filename
            model.cv_text = application.cv_text
            model.matching_score = application.matching_score
            model.matching_details = application.matching_details
            model.status = str(application.status)
            model.status_history = application.status_history
            model.notes = application.notes
            model.boond_candidate_id = application.boond_candidate_id
            model.updated_at = datetime.utcnow()
        else:
            model = JobApplicationModel(
                id=application.id,
                job_posting_id=application.job_posting_id,
                first_name=application.first_name,
                last_name=application.last_name,
                email=application.email,
                phone=application.phone,
                job_title=application.job_title,
                # New fields
                availability=application.availability,
                employment_status=application.employment_status,
                english_level=application.english_level,
                tjm_current=application.tjm_current,
                tjm_desired=application.tjm_desired,
                salary_current=application.salary_current,
                salary_desired=application.salary_desired,
                # Legacy fields
                tjm_min=application.tjm_min,
                tjm_max=application.tjm_max,
                availability_date=application.availability_date,
                cv_s3_key=application.cv_s3_key,
                cv_filename=application.cv_filename,
                cv_text=application.cv_text,
                matching_score=application.matching_score,
                matching_details=application.matching_details,
                status=str(application.status),
                status_history=application.status_history,
                notes=application.notes,
                boond_candidate_id=application.boond_candidate_id,
                created_at=application.created_at,
                updated_at=application.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, application_id: UUID) -> bool:
        """Delete job application by ID."""
        result = await self.session.execute(
            select(JobApplicationModel).where(JobApplicationModel.id == application_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_by_posting(
        self,
        posting_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ApplicationStatus] = None,
        sort_by_score: bool = True,
    ) -> list[JobApplication]:
        """List applications for a job posting with optional status filter."""
        query = select(JobApplicationModel).where(
            JobApplicationModel.job_posting_id == posting_id
        )
        if status:
            query = query.where(JobApplicationModel.status == str(status))

        if sort_by_score:
            query = query.order_by(
                JobApplicationModel.matching_score.desc().nullslast(),
                JobApplicationModel.created_at.desc(),
            )
        else:
            query = query.order_by(JobApplicationModel.created_at.desc())

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ApplicationStatus] = None,
    ) -> list[JobApplication]:
        """List all applications with optional status filter."""
        query = select(JobApplicationModel)
        if status:
            query = query.where(JobApplicationModel.status == str(status))
        query = query.offset(skip).limit(limit).order_by(JobApplicationModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_posting(
        self,
        posting_id: UUID,
        status: Optional[ApplicationStatus] = None,
    ) -> int:
        """Count applications for a job posting with optional status filter."""
        query = select(func.count(JobApplicationModel.id)).where(
            JobApplicationModel.job_posting_id == posting_id
        )
        if status:
            query = query.where(JobApplicationModel.status == str(status))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_new_by_posting(self, posting_id: UUID) -> int:
        """Count new (unread) applications for a job posting."""
        result = await self.session.execute(
            select(func.count(JobApplicationModel.id)).where(
                JobApplicationModel.job_posting_id == posting_id,
                JobApplicationModel.status == str(ApplicationStatus.NOUVEAU),
            )
        )
        return result.scalar() or 0

    async def get_stats_by_posting(self, posting_id: UUID) -> dict[str, int]:
        """Get application statistics for a job posting (by status)."""
        result = await self.session.execute(
            select(
                JobApplicationModel.status,
                func.count(JobApplicationModel.id),
            )
            .where(JobApplicationModel.job_posting_id == posting_id)
            .group_by(JobApplicationModel.status)
        )
        stats = {str(s): 0 for s in ApplicationStatus}
        for status, count in result.all():
            stats[status] = count
        return stats

    def _to_entity(self, model: JobApplicationModel) -> JobApplication:
        """Convert model to entity."""
        return JobApplication(
            id=model.id,
            job_posting_id=model.job_posting_id,
            first_name=model.first_name,
            last_name=model.last_name,
            email=model.email,
            phone=model.phone,
            job_title=model.job_title,
            # New fields
            availability=model.availability or "asap",
            employment_status=model.employment_status or "freelance",
            english_level=model.english_level or "notions",
            tjm_current=model.tjm_current,
            tjm_desired=model.tjm_desired,
            salary_current=model.salary_current,
            salary_desired=model.salary_desired,
            # Legacy fields
            tjm_min=model.tjm_min,
            tjm_max=model.tjm_max,
            availability_date=model.availability_date,
            cv_s3_key=model.cv_s3_key,
            cv_filename=model.cv_filename,
            cv_text=model.cv_text,
            matching_score=model.matching_score,
            matching_details=model.matching_details,
            status=ApplicationStatus(model.status),
            status_history=model.status_history or [],
            notes=model.notes,
            boond_candidate_id=model.boond_candidate_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
