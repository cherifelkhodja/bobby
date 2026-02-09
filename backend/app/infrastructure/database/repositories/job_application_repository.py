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

    async def exists_by_email_and_posting(
        self,
        email: str,
        posting_id: UUID,
    ) -> bool:
        """Check if an application exists for a given email and posting."""
        result = await self.session.execute(
            select(func.count(JobApplicationModel.id)).where(
                JobApplicationModel.email == email,
                JobApplicationModel.job_posting_id == posting_id,
            )
        )
        count = result.scalar() or 0
        return count > 0

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
            model.civility = application.civility
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
            model.cv_quality_score = application.cv_quality_score
            model.cv_quality = application.cv_quality
            model.is_read = application.is_read
            model.status = str(application.status)
            model.status_history = application.status_history
            model.notes = application.notes
            model.boond_candidate_id = application.boond_candidate_id
            model.boond_sync_error = application.boond_sync_error
            model.boond_synced_at = application.boond_synced_at
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
                civility=application.civility,
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
                cv_quality_score=application.cv_quality_score,
                cv_quality=application.cv_quality,
                is_read=application.is_read,
                status=str(application.status),
                status_history=application.status_history,
                notes=application.notes,
                boond_candidate_id=application.boond_candidate_id,
                boond_sync_error=application.boond_sync_error,
                boond_synced_at=application.boond_synced_at,
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
        employment_status: Optional[str] = None,
        availability: Optional[str] = None,
        sort_by: str = "score",  # score, tjm, salary, date
        sort_order: str = "desc",  # asc, desc
    ) -> list[JobApplication]:
        """List applications for a job posting with optional filters and sorting.

        Args:
            posting_id: Job posting UUID
            skip: Number of records to skip
            limit: Maximum number of records
            status: Filter by application status
            employment_status: Filter by employment status (freelance, employee, both)
            availability: Filter by availability (asap, 1_month, 2_months, 3_months, more_3_months)
            sort_by: Sort field (score, tjm, salary, date)
            sort_order: Sort direction (asc, desc)
        """
        query = select(JobApplicationModel).where(
            JobApplicationModel.job_posting_id == posting_id
        )
        if status:
            query = query.where(JobApplicationModel.status == str(status))
        if employment_status:
            # Filter by employment_status, handling comma-separated values
            # When filtering by "freelance", match "freelance" and "freelance,employee"
            query = query.where(
                JobApplicationModel.employment_status.contains(employment_status)
            )
        if availability:
            query = query.where(JobApplicationModel.availability == availability)

        # Build sort expression
        if sort_by == "tjm":
            # Sort by tjm_desired, fallback to tjm_current
            sort_col = func.coalesce(
                JobApplicationModel.tjm_desired,
                JobApplicationModel.tjm_current,
            )
        elif sort_by == "salary":
            # Sort by salary_desired, fallback to salary_current
            sort_col = func.coalesce(
                JobApplicationModel.salary_desired,
                JobApplicationModel.salary_current,
            )
        elif sort_by == "date":
            sort_col = JobApplicationModel.created_at
        else:
            # Default: sort by score
            sort_col = JobApplicationModel.matching_score

        # Apply sort order
        if sort_order == "asc":
            if sort_by == "score":
                query = query.order_by(
                    sort_col.asc().nullslast(),
                    JobApplicationModel.created_at.desc(),
                )
            else:
                query = query.order_by(
                    sort_col.asc().nullslast(),
                    JobApplicationModel.created_at.desc(),
                )
        else:
            if sort_by == "score":
                query = query.order_by(
                    sort_col.desc().nullslast(),
                    JobApplicationModel.created_at.desc(),
                )
            else:
                query = query.order_by(
                    sort_col.desc().nullslast(),
                    JobApplicationModel.created_at.desc(),
                )

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
        employment_status: Optional[str] = None,
        availability: Optional[str] = None,
    ) -> int:
        """Count applications for a job posting with optional filters."""
        query = select(func.count(JobApplicationModel.id)).where(
            JobApplicationModel.job_posting_id == posting_id
        )
        if status:
            query = query.where(JobApplicationModel.status == str(status))
        if employment_status:
            # Filter by employment_status, handling comma-separated values
            # When filtering by "freelance", match "freelance" and "freelance,employee"
            query = query.where(
                JobApplicationModel.employment_status.contains(employment_status)
            )
        if availability:
            query = query.where(JobApplicationModel.availability == availability)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_unread_by_posting(self, posting_id: UUID) -> int:
        """Count unread applications for a job posting."""
        result = await self.session.execute(
            select(func.count(JobApplicationModel.id)).where(
                JobApplicationModel.job_posting_id == posting_id,
                JobApplicationModel.is_read == False,  # noqa: E712
            )
        )
        return result.scalar() or 0

    async def get_stats_by_posting(self, posting_id: UUID) -> dict[str, int]:
        """Get application statistics for a job posting (by status and read state)."""
        # Get counts by status
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

        # Get unread count
        unread_result = await self.session.execute(
            select(func.count(JobApplicationModel.id)).where(
                JobApplicationModel.job_posting_id == posting_id,
                JobApplicationModel.is_read == False,  # noqa: E712
            )
        )
        stats["unread"] = unread_result.scalar() or 0

        # Add total count
        stats["total"] = sum(v for k, v in stats.items() if k != "unread")
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
            civility=model.civility,
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
            cv_quality_score=model.cv_quality_score,
            cv_quality=model.cv_quality,
            is_read=model.is_read if hasattr(model, 'is_read') else False,
            status=ApplicationStatus(model.status),
            status_history=model.status_history or [],
            notes=model.notes,
            boond_candidate_id=model.boond_candidate_id,
            boond_sync_error=model.boond_sync_error,
            boond_synced_at=model.boond_synced_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
