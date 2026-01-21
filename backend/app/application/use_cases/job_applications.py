"""Job application use cases for HR feature."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from app.application.read_models.hr import (
    ApplicationSubmissionResultReadModel,
    JobApplicationListReadModel,
    JobApplicationReadModel,
    MatchingDetailsReadModel,
    StatusChangeReadModel,
)
from app.domain.entities import ApplicationStatus, JobApplication, JobPostingStatus
from app.domain.entities.job_application import MatchingResult
from app.domain.exceptions import (
    InvalidStatusTransitionError,
    JobApplicationNotFoundError,
    JobPostingNotFoundError,
)
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.database.repositories import (
    JobApplicationRepository,
    JobPostingRepository,
    UserRepository,
)
from app.infrastructure.matching.gemini_matcher import GeminiMatchingService
from app.infrastructure.storage.s3_client import S3StorageClient


@dataclass
class SubmitApplicationCommand:
    """Command for submitting a job application (public form)."""

    application_token: str
    first_name: str
    last_name: str
    email: str
    phone: str  # Format international +33...
    job_title: str
    availability: str  # asap, 1_month, 2_months, 3_months, more_3_months
    employment_status: str  # freelance, employee, both
    english_level: str  # notions, intermediate, professional, fluent, bilingual
    tjm_current: Optional[float]  # For freelance/both
    tjm_desired: Optional[float]  # For freelance/both
    salary_current: Optional[float]  # For employee/both
    salary_desired: Optional[float]  # For employee/both
    cv_content: bytes
    cv_filename: str
    cv_content_type: str


class SubmitApplicationUseCase:
    """Submit a job application through the public form."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        job_application_repository: JobApplicationRepository,
        s3_client: S3StorageClient,
        matching_service: GeminiMatchingService,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.job_application_repository = job_application_repository
        self.s3_client = s3_client
        self.matching_service = matching_service

    async def execute(self, command: SubmitApplicationCommand) -> ApplicationSubmissionResultReadModel:
        """Submit application with CV upload and matching."""
        # Get job posting by token
        posting = await self.job_posting_repository.get_by_token(command.application_token)
        if not posting:
            raise JobPostingNotFoundError(f"token:{command.application_token}")

        # Check posting is published
        if posting.status != JobPostingStatus.PUBLISHED:
            raise JobPostingNotFoundError(f"token:{command.application_token}")

        # Check for duplicate application
        exists = await self.job_application_repository.exists_by_email_and_posting(
            email=command.email,
            posting_id=posting.id,
        )
        if exists:
            return ApplicationSubmissionResultReadModel(
                success=False,
                application_id="",
                message="Vous avez déjà postulé à cette offre.",
            )

        # Upload CV to S3
        cv_s3_key = f"cvs/{posting.id}/{command.email.replace('@', '_at_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{command.cv_filename}"

        try:
            await self.s3_client.upload_file(
                key=cv_s3_key,
                content=command.cv_content,
                content_type=command.cv_content_type,
            )
        except Exception as e:
            return ApplicationSubmissionResultReadModel(
                success=False,
                application_id="",
                message=f"Erreur lors du téléchargement du CV: {str(e)}",
            )

        # Extract text from CV for matching
        cv_text = None
        try:
            from app.infrastructure.cv_transformer.extractors import extract_text_from_bytes
            cv_text = extract_text_from_bytes(command.cv_content, command.cv_filename)
        except Exception:
            # Continue without text extraction
            pass

        # Calculate matching score
        matching_score = None
        matching_details = None
        if cv_text:
            try:
                # Build job description for matching
                job_description = f"""
Titre: {posting.title}

Description:
{posting.description}

Qualifications requises:
{posting.qualifications}

Compétences recherchées:
{', '.join(posting.skills) if posting.skills else 'Non spécifiées'}
"""
                result = await self.matching_service.calculate_match(
                    cv_text=cv_text,
                    job_description=job_description,
                )
                matching_score = result.get("score", 0)
                matching_details = MatchingResult(
                    score=matching_score,
                    strengths=result.get("strengths", []),
                    gaps=result.get("gaps", []),
                    summary=result.get("summary", ""),
                )
            except Exception:
                # Continue without matching
                pass

        # Create application
        application = JobApplication(
            job_posting_id=posting.id,
            first_name=command.first_name,
            last_name=command.last_name,
            email=command.email.lower(),
            phone=command.phone,
            job_title=command.job_title,
            availability=command.availability,
            employment_status=command.employment_status,
            english_level=command.english_level,
            tjm_current=command.tjm_current,
            tjm_desired=command.tjm_desired,
            salary_current=command.salary_current,
            salary_desired=command.salary_desired,
            cv_s3_key=cv_s3_key,
            cv_filename=command.cv_filename,
            cv_text=cv_text,
            matching_score=matching_score,
            matching_details=matching_details,
        )

        saved = await self.job_application_repository.save(application)

        return ApplicationSubmissionResultReadModel(
            success=True,
            application_id=str(saved.id),
            message="Votre candidature a été soumise avec succès. Nous reviendrons vers vous rapidement.",
        )


class ListApplicationsForPostingUseCase:
    """List applications for a specific job posting."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        job_application_repository: JobApplicationRepository,
        s3_client: S3StorageClient,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.job_application_repository = job_application_repository
        self.s3_client = s3_client

    async def execute(
        self,
        posting_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ApplicationStatus] = None,
        sort_by_score: bool = True,
    ) -> JobApplicationListReadModel:
        """List applications for a job posting."""
        # Verify posting exists
        posting = await self.job_posting_repository.get_by_id(posting_id)
        if not posting:
            raise JobPostingNotFoundError(str(posting_id))

        skip = (page - 1) * page_size

        applications = await self.job_application_repository.list_by_posting(
            posting_id=posting_id,
            skip=skip,
            limit=page_size,
            status=status,
            sort_by_score=sort_by_score,
        )
        total = await self.job_application_repository.count_by_posting(
            posting_id=posting_id,
            status=status,
        )
        stats = await self.job_application_repository.get_stats_by_posting(posting_id)

        items = []
        for app in applications:
            # Generate presigned URL for CV download
            cv_download_url = None
            try:
                cv_download_url = await self.s3_client.get_presigned_url(
                    key=app.cv_s3_key,
                    expires_in=3600,  # 1 hour
                )
            except Exception:
                pass

            items.append(self._to_read_model(app, posting.title, cv_download_url))

        return JobApplicationListReadModel(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            stats=stats,
        )

    def _to_read_model(
        self,
        application: JobApplication,
        posting_title: Optional[str] = None,
        cv_download_url: Optional[str] = None,
    ) -> JobApplicationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh.from_status),
                to_status=str(sh.to_status),
                changed_at=sh.changed_at,
                changed_by=str(sh.changed_by) if sh.changed_by else None,
                comment=sh.comment,
            )
            for sh in application.status_history
        ]

        matching_details_model = None
        if application.matching_details:
            matching_details_model = MatchingDetailsReadModel(
                score=application.matching_details.score,
                strengths=application.matching_details.strengths,
                gaps=application.matching_details.gaps,
                summary=application.matching_details.summary,
            )

        return JobApplicationReadModel(
            id=str(application.id),
            job_posting_id=str(application.job_posting_id),
            job_posting_title=posting_title,
            first_name=application.first_name,
            last_name=application.last_name,
            full_name=application.full_name,
            email=application.email,
            phone=application.phone,
            job_title=application.job_title,
            # New fields
            availability=application.availability,
            availability_display=application.availability_display,
            employment_status=application.employment_status,
            employment_status_display=application.employment_status_display,
            english_level=application.english_level,
            english_level_display=application.english_level_display,
            tjm_current=application.tjm_current,
            tjm_desired=application.tjm_desired,
            salary_current=application.salary_current,
            salary_desired=application.salary_desired,
            tjm_range=application.tjm_range,
            salary_range=application.salary_range,
            # Legacy fields
            tjm_min=application.tjm_min,
            tjm_max=application.tjm_max,
            availability_date=application.availability_date,
            cv_s3_key=application.cv_s3_key,
            cv_filename=application.cv_filename,
            cv_download_url=cv_download_url,
            matching_score=application.matching_score,
            matching_details=matching_details_model,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


class GetApplicationUseCase:
    """Get a single application with details."""

    def __init__(
        self,
        job_posting_repository: JobPostingRepository,
        job_application_repository: JobApplicationRepository,
        s3_client: S3StorageClient,
    ) -> None:
        self.job_posting_repository = job_posting_repository
        self.job_application_repository = job_application_repository
        self.s3_client = s3_client

    async def execute(self, application_id: UUID) -> JobApplicationReadModel:
        """Get application by ID."""
        application = await self.job_application_repository.get_by_id(application_id)
        if not application:
            raise JobApplicationNotFoundError(str(application_id))

        posting = await self.job_posting_repository.get_by_id(application.job_posting_id)

        # Generate presigned URL for CV download
        cv_download_url = None
        try:
            cv_download_url = await self.s3_client.get_presigned_url(
                key=application.cv_s3_key,
                expires_in=3600,
            )
        except Exception:
            pass

        return self._to_read_model(
            application,
            posting.title if posting else None,
            cv_download_url,
        )

    def _to_read_model(
        self,
        application: JobApplication,
        posting_title: Optional[str] = None,
        cv_download_url: Optional[str] = None,
    ) -> JobApplicationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh.from_status),
                to_status=str(sh.to_status),
                changed_at=sh.changed_at,
                changed_by=str(sh.changed_by) if sh.changed_by else None,
                comment=sh.comment,
            )
            for sh in application.status_history
        ]

        matching_details_model = None
        if application.matching_details:
            matching_details_model = MatchingDetailsReadModel(
                score=application.matching_details.score,
                strengths=application.matching_details.strengths,
                gaps=application.matching_details.gaps,
                summary=application.matching_details.summary,
            )

        return JobApplicationReadModel(
            id=str(application.id),
            job_posting_id=str(application.job_posting_id),
            job_posting_title=posting_title,
            first_name=application.first_name,
            last_name=application.last_name,
            full_name=application.full_name,
            email=application.email,
            phone=application.phone,
            job_title=application.job_title,
            # New fields
            availability=application.availability,
            availability_display=application.availability_display,
            employment_status=application.employment_status,
            employment_status_display=application.employment_status_display,
            english_level=application.english_level,
            english_level_display=application.english_level_display,
            tjm_current=application.tjm_current,
            tjm_desired=application.tjm_desired,
            salary_current=application.salary_current,
            salary_desired=application.salary_desired,
            tjm_range=application.tjm_range,
            salary_range=application.salary_range,
            # Legacy fields
            tjm_min=application.tjm_min,
            tjm_max=application.tjm_max,
            availability_date=application.availability_date,
            cv_s3_key=application.cv_s3_key,
            cv_filename=application.cv_filename,
            cv_download_url=cv_download_url,
            matching_score=application.matching_score,
            matching_details=matching_details_model,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


@dataclass
class UpdateApplicationStatusCommand:
    """Command for updating application status."""

    application_id: UUID
    new_status: ApplicationStatus
    changed_by: UUID
    comment: Optional[str] = None


class UpdateApplicationStatusUseCase:
    """Update application status with history tracking."""

    def __init__(
        self,
        job_application_repository: JobApplicationRepository,
        job_posting_repository: JobPostingRepository,
        user_repository: UserRepository,
        s3_client: S3StorageClient,
    ) -> None:
        self.job_application_repository = job_application_repository
        self.job_posting_repository = job_posting_repository
        self.user_repository = user_repository
        self.s3_client = s3_client

    async def execute(self, command: UpdateApplicationStatusCommand) -> JobApplicationReadModel:
        """Update application status."""
        application = await self.job_application_repository.get_by_id(command.application_id)
        if not application:
            raise JobApplicationNotFoundError(str(command.application_id))

        # Attempt status change
        success = application.change_status(
            new_status=command.new_status,
            changed_by=command.changed_by,
            comment=command.comment,
        )

        if not success:
            raise InvalidStatusTransitionError(
                str(application.status),
                str(command.new_status),
            )

        saved = await self.job_application_repository.save(application)

        # Get posting title
        posting = await self.job_posting_repository.get_by_id(application.job_posting_id)

        # Generate presigned URL
        cv_download_url = None
        try:
            cv_download_url = await self.s3_client.get_presigned_url(
                key=application.cv_s3_key,
                expires_in=3600,
            )
        except Exception:
            pass

        return await self._to_read_model(
            saved,
            posting.title if posting else None,
            cv_download_url,
        )

    async def _to_read_model(
        self,
        application: JobApplication,
        posting_title: Optional[str] = None,
        cv_download_url: Optional[str] = None,
    ) -> JobApplicationReadModel:
        # Enrich status history with user names
        status_history = []
        for sh in application.status_history:
            changed_by_name = None
            if sh.changed_by:
                user = await self.user_repository.get_by_id(sh.changed_by)
                if user:
                    changed_by_name = user.full_name

            status_history.append(
                StatusChangeReadModel(
                    from_status=str(sh.from_status),
                    to_status=str(sh.to_status),
                    changed_at=sh.changed_at,
                    changed_by=str(sh.changed_by) if sh.changed_by else None,
                    changed_by_name=changed_by_name,
                    comment=sh.comment,
                )
            )

        matching_details_model = None
        if application.matching_details:
            matching_details_model = MatchingDetailsReadModel(
                score=application.matching_details.score,
                strengths=application.matching_details.strengths,
                gaps=application.matching_details.gaps,
                summary=application.matching_details.summary,
            )

        return JobApplicationReadModel(
            id=str(application.id),
            job_posting_id=str(application.job_posting_id),
            job_posting_title=posting_title,
            first_name=application.first_name,
            last_name=application.last_name,
            full_name=application.full_name,
            email=application.email,
            phone=application.phone,
            job_title=application.job_title,
            # New fields
            availability=application.availability,
            availability_display=application.availability_display,
            employment_status=application.employment_status,
            employment_status_display=application.employment_status_display,
            english_level=application.english_level,
            english_level_display=application.english_level_display,
            tjm_current=application.tjm_current,
            tjm_desired=application.tjm_desired,
            salary_current=application.salary_current,
            salary_desired=application.salary_desired,
            tjm_range=application.tjm_range,
            salary_range=application.salary_range,
            # Legacy fields
            tjm_min=application.tjm_min,
            tjm_max=application.tjm_max,
            availability_date=application.availability_date,
            cv_s3_key=application.cv_s3_key,
            cv_filename=application.cv_filename,
            cv_download_url=cv_download_url,
            matching_score=application.matching_score,
            matching_details=matching_details_model,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


class UpdateApplicationNoteUseCase:
    """Update application notes."""

    def __init__(
        self,
        job_application_repository: JobApplicationRepository,
        job_posting_repository: JobPostingRepository,
        s3_client: S3StorageClient,
    ) -> None:
        self.job_application_repository = job_application_repository
        self.job_posting_repository = job_posting_repository
        self.s3_client = s3_client

    async def execute(
        self,
        application_id: UUID,
        notes: str,
    ) -> JobApplicationReadModel:
        """Update application notes."""
        application = await self.job_application_repository.get_by_id(application_id)
        if not application:
            raise JobApplicationNotFoundError(str(application_id))

        application.notes = notes
        application.updated_at = datetime.utcnow()

        saved = await self.job_application_repository.save(application)

        posting = await self.job_posting_repository.get_by_id(application.job_posting_id)

        cv_download_url = None
        try:
            cv_download_url = await self.s3_client.get_presigned_url(
                key=application.cv_s3_key,
                expires_in=3600,
            )
        except Exception:
            pass

        return self._to_read_model(
            saved,
            posting.title if posting else None,
            cv_download_url,
        )

    def _to_read_model(
        self,
        application: JobApplication,
        posting_title: Optional[str] = None,
        cv_download_url: Optional[str] = None,
    ) -> JobApplicationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh.from_status),
                to_status=str(sh.to_status),
                changed_at=sh.changed_at,
                changed_by=str(sh.changed_by) if sh.changed_by else None,
                comment=sh.comment,
            )
            for sh in application.status_history
        ]

        matching_details_model = None
        if application.matching_details:
            matching_details_model = MatchingDetailsReadModel(
                score=application.matching_details.score,
                strengths=application.matching_details.strengths,
                gaps=application.matching_details.gaps,
                summary=application.matching_details.summary,
            )

        return JobApplicationReadModel(
            id=str(application.id),
            job_posting_id=str(application.job_posting_id),
            job_posting_title=posting_title,
            first_name=application.first_name,
            last_name=application.last_name,
            full_name=application.full_name,
            email=application.email,
            phone=application.phone,
            job_title=application.job_title,
            # New fields
            availability=application.availability,
            availability_display=application.availability_display,
            employment_status=application.employment_status,
            employment_status_display=application.employment_status_display,
            english_level=application.english_level,
            english_level_display=application.english_level_display,
            tjm_current=application.tjm_current,
            tjm_desired=application.tjm_desired,
            salary_current=application.salary_current,
            salary_desired=application.salary_desired,
            tjm_range=application.tjm_range,
            salary_range=application.salary_range,
            # Legacy fields
            tjm_min=application.tjm_min,
            tjm_max=application.tjm_max,
            availability_date=application.availability_date,
            cv_s3_key=application.cv_s3_key,
            cv_filename=application.cv_filename,
            cv_download_url=cv_download_url,
            matching_score=application.matching_score,
            matching_details=matching_details_model,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


class CreateCandidateInBoondUseCase:
    """Create candidate in BoondManager from application."""

    def __init__(
        self,
        job_application_repository: JobApplicationRepository,
        job_posting_repository: JobPostingRepository,
        boond_client: BoondClient,
        s3_client: S3StorageClient,
    ) -> None:
        self.job_application_repository = job_application_repository
        self.job_posting_repository = job_posting_repository
        self.boond_client = boond_client
        self.s3_client = s3_client

    async def execute(self, application_id: UUID) -> JobApplicationReadModel:
        """Create candidate in BoondManager."""
        application = await self.job_application_repository.get_by_id(application_id)
        if not application:
            raise JobApplicationNotFoundError(str(application_id))

        if application.boond_candidate_id:
            raise ValueError("Candidate already exists in BoondManager")

        # Create candidate entity for Boond
        from app.domain.entities import Candidate
        from app.domain.value_objects import Email, Phone

        candidate = Candidate(
            email=Email(application.email),
            first_name=application.first_name,
            last_name=application.last_name,
            civility="M",  # Default, could be improved
            phone=Phone(application.phone) if application.phone else None,
            daily_rate=application.tjm_max,
            note=f"Candidature via formulaire public\nTJM: {application.tjm_min}€ - {application.tjm_max}€\nDisponibilité: {application.availability_date}\nPoste: {application.job_title}",
        )

        # Create in Boond
        try:
            external_id = await self.boond_client.create_candidate(candidate)
            application.boond_candidate_id = external_id
            application.updated_at = datetime.utcnow()
            saved = await self.job_application_repository.save(application)
        except Exception as e:
            raise ValueError(f"Failed to create candidate in BoondManager: {str(e)}")

        posting = await self.job_posting_repository.get_by_id(application.job_posting_id)

        cv_download_url = None
        try:
            cv_download_url = await self.s3_client.get_presigned_url(
                key=application.cv_s3_key,
                expires_in=3600,
            )
        except Exception:
            pass

        return self._to_read_model(
            saved,
            posting.title if posting else None,
            cv_download_url,
        )

    def _to_read_model(
        self,
        application: JobApplication,
        posting_title: Optional[str] = None,
        cv_download_url: Optional[str] = None,
    ) -> JobApplicationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh.from_status),
                to_status=str(sh.to_status),
                changed_at=sh.changed_at,
                changed_by=str(sh.changed_by) if sh.changed_by else None,
                comment=sh.comment,
            )
            for sh in application.status_history
        ]

        matching_details_model = None
        if application.matching_details:
            matching_details_model = MatchingDetailsReadModel(
                score=application.matching_details.score,
                strengths=application.matching_details.strengths,
                gaps=application.matching_details.gaps,
                summary=application.matching_details.summary,
            )

        return JobApplicationReadModel(
            id=str(application.id),
            job_posting_id=str(application.job_posting_id),
            job_posting_title=posting_title,
            first_name=application.first_name,
            last_name=application.last_name,
            full_name=application.full_name,
            email=application.email,
            phone=application.phone,
            job_title=application.job_title,
            # New fields
            availability=application.availability,
            availability_display=application.availability_display,
            employment_status=application.employment_status,
            employment_status_display=application.employment_status_display,
            english_level=application.english_level,
            english_level_display=application.english_level_display,
            tjm_current=application.tjm_current,
            tjm_desired=application.tjm_desired,
            salary_current=application.salary_current,
            salary_desired=application.salary_desired,
            tjm_range=application.tjm_range,
            salary_range=application.salary_range,
            # Legacy fields
            tjm_min=application.tjm_min,
            tjm_max=application.tjm_max,
            availability_date=application.availability_date,
            cv_s3_key=application.cv_s3_key,
            cv_filename=application.cv_filename,
            cv_download_url=cv_download_url,
            matching_score=application.matching_score,
            matching_details=matching_details_model,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


class GetApplicationCvUrlUseCase:
    """Get presigned URL for CV download."""

    def __init__(
        self,
        job_application_repository: JobApplicationRepository,
        s3_client: S3StorageClient,
    ) -> None:
        self.job_application_repository = job_application_repository
        self.s3_client = s3_client

    async def execute(self, application_id: UUID, expires_in: int = 3600) -> str:
        """Get presigned URL for CV download."""
        application = await self.job_application_repository.get_by_id(application_id)
        if not application:
            raise JobApplicationNotFoundError(str(application_id))

        return await self.s3_client.get_presigned_url(
            key=application.cv_s3_key,
            expires_in=expires_in,
        )
