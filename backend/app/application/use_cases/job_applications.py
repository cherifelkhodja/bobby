"""Job application use cases for HR feature."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from app.application.read_models.hr import (
    AccountQualityScoreReadModel,
    ApplicationSubmissionResultReadModel,
    BonusMalusReadModel,
    ContinuityScoreReadModel,
    CvQualityDetailsNotesReadModel,
    CvQualityReadModel,
    EducationScoreReadModel,
    JobApplicationListReadModel,
    JobApplicationReadModel,
    MatchingDetailsReadModel,
    MatchingRecommendationReadModel,
    ScoresDetailsReadModel,
    StabilityScoreReadModel,
    StatusChangeReadModel,
)
from app.domain.entities import ApplicationStatus, JobApplication, JobPostingStatus
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
    cv_content: bytes
    cv_filename: str
    cv_content_type: str
    civility: Optional[str] = None  # M, Mme
    tjm_current: Optional[float] = None  # For freelance/both
    tjm_desired: Optional[float] = None  # For freelance/both
    salary_current: Optional[float] = None  # For employee/both
    salary_desired: Optional[float] = None  # For employee/both


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

        # Upload CV to S3 with formatted name: "Prenom NOM - date.ext"
        import os
        file_ext = os.path.splitext(command.cv_filename)[1].lower()  # .pdf or .docx
        upload_date = datetime.utcnow().strftime('%Y%m%d')
        formatted_name = f"{command.first_name} {command.last_name.upper()}"
        cv_display_name = f"{formatted_name} - {upload_date}{file_ext}"
        cv_s3_key = f"cvs/{posting.id}/{cv_display_name}"

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

        # Calculate matching score and CV quality evaluation in parallel
        matching_score = None
        matching_details = None
        cv_quality_score = None
        cv_quality = None

        if cv_text:
            try:
                import asyncio

                # Build job description for matching
                job_description = f"""
{posting.description}

Qualifications requises:
{posting.qualifications}
"""
                # Build TJM range string
                tjm_range_str = None
                if command.tjm_current or command.tjm_desired:
                    parts = []
                    if command.tjm_current:
                        parts.append(f"Actuel: {command.tjm_current}€")
                    if command.tjm_desired:
                        parts.append(f"Souhaité: {command.tjm_desired}€")
                    tjm_range_str = " / ".join(parts)

                # Map availability to display string
                availability_map = {
                    "asap": "Immédiate",
                    "1_month": "Sous 1 mois",
                    "2_months": "Sous 2 mois",
                    "3_months": "Sous 3 mois",
                    "more_3_months": "Plus de 3 mois",
                }
                availability_display = availability_map.get(command.availability, command.availability)

                # Run both evaluations in parallel
                matching_task = self.matching_service.calculate_match_enhanced(
                    cv_text=cv_text,
                    job_title_offer=posting.title,
                    job_description=job_description,
                    required_skills=posting.skills,
                    candidate_job_title=command.job_title,
                    candidate_tjm_range=tjm_range_str,
                    candidate_availability=availability_display,
                )
                quality_task = self.matching_service.evaluate_cv_quality(cv_text)

                results = await asyncio.gather(
                    matching_task,
                    quality_task,
                    return_exceptions=True,
                )

                # Process matching result
                matching_result = results[0]
                if not isinstance(matching_result, Exception):
                    matching_score = matching_result.get("score_global", matching_result.get("score", 0))
                    # Store full enhanced matching details
                    matching_details = {
                        "score": matching_score,
                        "score_global": matching_result.get("score_global", matching_score),
                        "scores_details": matching_result.get("scores_details", {}),
                        "competences_matchees": matching_result.get("competences_matchees", []),
                        "competences_manquantes": matching_result.get("competences_manquantes", []),
                        "points_forts": matching_result.get("points_forts", []),
                        "points_vigilance": matching_result.get("points_vigilance", []),
                        "synthese": matching_result.get("synthese", matching_result.get("summary", "")),
                        "recommandation": matching_result.get("recommandation", {}),
                        # Legacy fields for backward compatibility
                        "strengths": matching_result.get("strengths", matching_result.get("points_forts", [])),
                        "gaps": matching_result.get("gaps", matching_result.get("competences_manquantes", [])),
                        "summary": matching_result.get("summary", matching_result.get("synthese", "")),
                    }

                # Process CV quality result
                quality_result = results[1]
                if not isinstance(quality_result, Exception):
                    cv_quality_score = quality_result.get("note_globale", 0)
                    cv_quality = quality_result

            except Exception:
                # Continue without matching/quality evaluation
                pass

        # Create application
        application = JobApplication(
            job_posting_id=posting.id,
            first_name=command.first_name,
            last_name=command.last_name,
            email=command.email.lower(),
            phone=command.phone,
            job_title=command.job_title,
            civility=command.civility,
            availability=command.availability,
            employment_status=command.employment_status,
            english_level=command.english_level,
            tjm_current=command.tjm_current,
            tjm_desired=command.tjm_desired,
            salary_current=command.salary_current,
            salary_desired=command.salary_desired,
            cv_s3_key=cv_s3_key,
            cv_filename=cv_display_name,
            cv_text=cv_text,
            matching_score=matching_score,
            matching_details=matching_details,
            cv_quality_score=cv_quality_score,
            cv_quality=cv_quality,
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
        employment_status: Optional[str] = None,
        availability: Optional[str] = None,
        sort_by: str = "score",
        sort_order: str = "desc",
    ) -> JobApplicationListReadModel:
        """List applications for a job posting.

        Args:
            posting_id: Job posting UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by application status
            employment_status: Filter by employment status (freelance, employee, both)
            availability: Filter by availability (asap, 1_month, 2_months, 3_months, more_3_months)
            sort_by: Sort field (score, tjm, salary, date)
            sort_order: Sort direction (asc, desc)
        """
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
            employment_status=employment_status,
            availability=availability,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total = await self.job_application_repository.count_by_posting(
            posting_id=posting_id,
            status=status,
            employment_status=employment_status,
            availability=availability,
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
                from_status=str(sh["from_status"]),
                to_status=str(sh["to_status"]),
                changed_at=sh["changed_at"],
                changed_by=str(sh["changed_by"]) if sh.get("changed_by") else None,
                comment=sh.get("comment"),
            )
            for sh in application.status_history
        ]

        matching_details_model = _build_matching_details_model(application.matching_details)
        cv_quality_model = _build_cv_quality_model(application.cv_quality)

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
            civility=application.civility,
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
            cv_quality_score=application.cv_quality_score,
            cv_quality=cv_quality_model,
            is_read=application.is_read,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            boond_sync_error=application.boond_sync_error,
            boond_synced_at=application.boond_synced_at,
            boond_sync_status=application.boond_sync_status,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


def _build_matching_details_model(
    matching_details: Optional[dict],
) -> Optional[MatchingDetailsReadModel]:
    """Build MatchingDetailsReadModel from matching details dict.

    Handles both legacy and enhanced matching result formats.
    """
    if not matching_details:
        return None

    # Build scores_details if present
    scores_details_model = None
    if matching_details.get("scores_details"):
        sd = matching_details["scores_details"]
        scores_details_model = ScoresDetailsReadModel(
            competences_techniques=sd.get("competences_techniques", 0),
            experience=sd.get("experience", 0),
            formation=sd.get("formation", 0),
            soft_skills=sd.get("soft_skills", 0),
        )

    # Build recommandation if present
    recommandation_model = None
    if matching_details.get("recommandation"):
        reco = matching_details["recommandation"]
        recommandation_model = MatchingRecommendationReadModel(
            niveau=reco.get("niveau", "faible"),
            action_suggeree=reco.get("action_suggeree", ""),
        )

    return MatchingDetailsReadModel(
        # Legacy fields
        score=matching_details.get("score", 0),
        strengths=matching_details.get("strengths", []),
        gaps=matching_details.get("gaps", []),
        summary=matching_details.get("summary", ""),
        # Enhanced fields
        score_global=matching_details.get("score_global"),
        scores_details=scores_details_model,
        competences_matchees=matching_details.get("competences_matchees", []),
        competences_manquantes=matching_details.get("competences_manquantes", []),
        points_forts=matching_details.get("points_forts", []),
        points_vigilance=matching_details.get("points_vigilance", []),
        synthese=matching_details.get("synthese", ""),
        recommandation=recommandation_model,
    )


def _build_cv_quality_model(
    cv_quality: Optional[dict],
) -> Optional[CvQualityReadModel]:
    """Build CvQualityReadModel from cv_quality dict.

    Converts the raw CV quality evaluation result into a structured read model.
    """
    if not cv_quality:
        return None

    # Build details_notes if present
    details_notes_model = None
    if cv_quality.get("details_notes"):
        dn = cv_quality["details_notes"]

        # Stabilite missions
        stabilite = dn.get("stabilite_missions", {})
        stabilite_model = StabilityScoreReadModel(
            note=stabilite.get("note", 0),
            max=stabilite.get("max", 8),
            duree_moyenne_mois=stabilite.get("duree_moyenne_mois", 0),
            commentaire=stabilite.get("commentaire", ""),
        ) if stabilite else None

        # Qualite comptes
        comptes = dn.get("qualite_comptes", {})
        comptes_model = AccountQualityScoreReadModel(
            note=comptes.get("note", 0),
            max=comptes.get("max", 6),
            comptes_identifies=comptes.get("comptes_identifies", []),
            commentaire=comptes.get("commentaire", ""),
        ) if comptes else None

        # Parcours scolaire
        parcours = dn.get("parcours_scolaire", {})
        parcours_model = EducationScoreReadModel(
            note=parcours.get("note", 0),
            max=parcours.get("max", 4),
            formations_identifiees=parcours.get("formations_identifiees", []),
            commentaire=parcours.get("commentaire", ""),
        ) if parcours else None

        # Continuite parcours
        continuite = dn.get("continuite_parcours", {})
        continuite_model = ContinuityScoreReadModel(
            note=continuite.get("note", 0),
            max=continuite.get("max", 4),
            trous_identifies=continuite.get("trous_identifies", []),
            commentaire=continuite.get("commentaire", ""),
        ) if continuite else None

        # Bonus/malus
        bonus = dn.get("bonus_malus", {})
        bonus_model = BonusMalusReadModel(
            valeur=bonus.get("valeur", 0),
            raisons=bonus.get("raisons", []),
        ) if bonus else None

        details_notes_model = CvQualityDetailsNotesReadModel(
            stabilite_missions=stabilite_model,
            qualite_comptes=comptes_model,
            parcours_scolaire=parcours_model,
            continuite_parcours=continuite_model,
            bonus_malus=bonus_model,
        )

    return CvQualityReadModel(
        niveau_experience=cv_quality.get("niveau_experience", "CONFIRME"),
        annees_experience=cv_quality.get("annees_experience", 0),
        note_globale=cv_quality.get("note_globale", 0),
        details_notes=details_notes_model,
        points_forts=cv_quality.get("points_forts", []),
        points_faibles=cv_quality.get("points_faibles", []),
        synthese=cv_quality.get("synthese", ""),
        classification=cv_quality.get("classification", "MOYEN"),
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

    async def execute(
        self,
        application_id: UUID,
        mark_viewed: bool = False,
        viewed_by: Optional[UUID] = None,
    ) -> JobApplicationReadModel:
        """Get application by ID.

        Args:
            application_id: Application UUID
            mark_viewed: If True and status is NOUVEAU, auto-transition to EN_COURS
            viewed_by: User ID who viewed (for status history)
        """
        application = await self.job_application_repository.get_by_id(application_id)
        if not application:
            raise JobApplicationNotFoundError(str(application_id))

        # Mark as read when viewed
        if mark_viewed and not application.is_read:
            application.mark_as_read()
            application = await self.job_application_repository.save(application)

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
                from_status=str(sh["from_status"]),
                to_status=str(sh["to_status"]),
                changed_at=sh["changed_at"],
                changed_by=str(sh["changed_by"]) if sh.get("changed_by") else None,
                comment=sh.get("comment"),
            )
            for sh in application.status_history
        ]

        matching_details_model = _build_matching_details_model(application.matching_details)
        cv_quality_model = _build_cv_quality_model(application.cv_quality)

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
            civility=application.civility,
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
            cv_quality_score=application.cv_quality_score,
            cv_quality=cv_quality_model,
            is_read=application.is_read,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            boond_sync_error=application.boond_sync_error,
            boond_synced_at=application.boond_synced_at,
            boond_sync_status=application.boond_sync_status,
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
        boond_client: Optional[BoondClient] = None,
    ) -> None:
        self.job_application_repository = job_application_repository
        self.job_posting_repository = job_posting_repository
        self.user_repository = user_repository
        self.s3_client = s3_client
        self.boond_client = boond_client

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

        # Auto-create candidate in Boond when validated
        if (
            command.new_status == ApplicationStatus.VALIDE
            and not application.boond_candidate_id
            and self.boond_client
        ):
            try:
                from app.domain.entities import Candidate
                from app.domain.value_objects import Email, Phone

                candidate = Candidate(
                    email=Email(application.email),
                    first_name=application.first_name,
                    last_name=application.last_name,
                    civility=application.civility or "M",
                    phone=Phone(application.phone) if application.phone else None,
                    daily_rate=application.tjm_desired or application.tjm_current or application.tjm_max,
                    note=(
                        f"Candidature validée - {application.job_title}\n"
                        f"TJM: {application.tjm_range}\n"
                        f"Disponibilité: {application.availability_display}"
                    ),
                )
                external_id = await self.boond_client.create_candidate(candidate)
                saved.boond_candidate_id = external_id
                saved.boond_synced_at = datetime.utcnow()
                saved.boond_sync_error = None
            except Exception as e:
                saved.boond_sync_error = str(e)
                import structlog
                structlog.get_logger(__name__).error(
                    "boond_auto_sync_failed",
                    application_id=str(application.id),
                    error=str(e),
                )
            # Re-save with Boond sync result
            saved = await self.job_application_repository.save(saved)

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
            changed_by_id = sh.get("changed_by")
            if changed_by_id:
                from uuid import UUID
                user = await self.user_repository.get_by_id(UUID(changed_by_id))
                if user:
                    changed_by_name = user.full_name

            status_history.append(
                StatusChangeReadModel(
                    from_status=str(sh["from_status"]),
                    to_status=str(sh["to_status"]),
                    changed_at=sh["changed_at"],
                    changed_by=str(changed_by_id) if changed_by_id else None,
                    changed_by_name=changed_by_name,
                    comment=sh.get("comment"),
                )
            )

        matching_details_model = _build_matching_details_model(application.matching_details)
        cv_quality_model = _build_cv_quality_model(application.cv_quality)

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
            civility=application.civility,
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
            cv_quality_score=application.cv_quality_score,
            cv_quality=cv_quality_model,
            is_read=application.is_read,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            boond_sync_error=application.boond_sync_error,
            boond_synced_at=application.boond_synced_at,
            boond_sync_status=application.boond_sync_status,
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
                from_status=str(sh["from_status"]),
                to_status=str(sh["to_status"]),
                changed_at=sh["changed_at"],
                changed_by=str(sh["changed_by"]) if sh.get("changed_by") else None,
                comment=sh.get("comment"),
            )
            for sh in application.status_history
        ]

        matching_details_model = _build_matching_details_model(application.matching_details)
        cv_quality_model = _build_cv_quality_model(application.cv_quality)

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
            civility=application.civility,
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
            cv_quality_score=application.cv_quality_score,
            cv_quality=cv_quality_model,
            is_read=application.is_read,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            boond_sync_error=application.boond_sync_error,
            boond_synced_at=application.boond_synced_at,
            boond_sync_status=application.boond_sync_status,
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
            civility=application.civility or "M",
            phone=Phone(application.phone) if application.phone else None,
            daily_rate=application.tjm_desired or application.tjm_current or application.tjm_max,
            note=(
                f"Candidature via formulaire public\n"
                f"TJM: {application.tjm_range}\n"
                f"Disponibilité: {application.availability_display}\n"
                f"Poste: {application.job_title}"
            ),
        )

        # Create in Boond
        try:
            external_id = await self.boond_client.create_candidate(candidate)
            application.boond_candidate_id = external_id
            application.boond_synced_at = datetime.utcnow()
            application.boond_sync_error = None
            application.updated_at = datetime.utcnow()
            saved = await self.job_application_repository.save(application)
        except Exception as e:
            application.boond_sync_error = str(e)
            application.updated_at = datetime.utcnow()
            await self.job_application_repository.save(application)
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
                from_status=str(sh["from_status"]),
                to_status=str(sh["to_status"]),
                changed_at=sh["changed_at"],
                changed_by=str(sh["changed_by"]) if sh.get("changed_by") else None,
                comment=sh.get("comment"),
            )
            for sh in application.status_history
        ]

        matching_details_model = _build_matching_details_model(application.matching_details)
        cv_quality_model = _build_cv_quality_model(application.cv_quality)

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
            civility=application.civility,
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
            cv_quality_score=application.cv_quality_score,
            cv_quality=cv_quality_model,
            is_read=application.is_read,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            boond_sync_error=application.boond_sync_error,
            boond_synced_at=application.boond_synced_at,
            boond_sync_status=application.boond_sync_status,
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


class ReanalyzeApplicationUseCase:
    """Re-run AI analyses (matching + CV quality) for an application."""

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

    async def execute(self, application_id: UUID) -> JobApplicationReadModel:
        """Re-run analyses for an application."""
        import asyncio

        application = await self.job_application_repository.get_by_id(application_id)
        if not application:
            raise JobApplicationNotFoundError(str(application_id))

        posting = await self.job_posting_repository.get_by_id(application.job_posting_id)
        if not posting:
            raise JobPostingNotFoundError(str(application.job_posting_id))

        # Re-run analyses if CV text is available
        if application.cv_text:
            # Build job description for matching
            job_description = f"""
{posting.description}

Qualifications requises:
{posting.qualifications}
"""
            # Build TJM range string
            tjm_range_str = None
            if application.tjm_current or application.tjm_desired:
                parts = []
                if application.tjm_current:
                    parts.append(f"Actuel: {application.tjm_current}€")
                if application.tjm_desired:
                    parts.append(f"Souhaité: {application.tjm_desired}€")
                tjm_range_str = " / ".join(parts)

            # Run both evaluations in parallel
            matching_task = self.matching_service.calculate_match_enhanced(
                cv_text=application.cv_text,
                job_title_offer=posting.title,
                job_description=job_description,
                required_skills=posting.skills,
                candidate_job_title=application.job_title,
                candidate_tjm_range=tjm_range_str,
                candidate_availability=application.availability_display,
            )
            quality_task = self.matching_service.evaluate_cv_quality(application.cv_text)

            results = await asyncio.gather(
                matching_task,
                quality_task,
                return_exceptions=True,
            )

            # Process matching result
            matching_result = results[0]
            if not isinstance(matching_result, Exception):
                matching_score = matching_result.get("score_global", matching_result.get("score", 0))
                application.matching_score = matching_score
                application.matching_details = {
                    "score": matching_score,
                    "score_global": matching_result.get("score_global", matching_score),
                    "scores_details": matching_result.get("scores_details", {}),
                    "competences_matchees": matching_result.get("competences_matchees", []),
                    "competences_manquantes": matching_result.get("competences_manquantes", []),
                    "points_forts": matching_result.get("points_forts", []),
                    "points_vigilance": matching_result.get("points_vigilance", []),
                    "synthese": matching_result.get("synthese", matching_result.get("summary", "")),
                    "recommandation": matching_result.get("recommandation", {}),
                    "strengths": matching_result.get("strengths", matching_result.get("points_forts", [])),
                    "gaps": matching_result.get("gaps", matching_result.get("competences_manquantes", [])),
                    "summary": matching_result.get("summary", matching_result.get("synthese", "")),
                }

            # Process CV quality result
            quality_result = results[1]
            if not isinstance(quality_result, Exception):
                application.cv_quality_score = quality_result.get("note_globale", 0)
                application.cv_quality = quality_result

            application.updated_at = datetime.utcnow()
            application = await self.job_application_repository.save(application)

        # Generate presigned URL for CV download
        cv_download_url = None
        try:
            cv_download_url = await self.s3_client.get_presigned_url(
                key=application.cv_s3_key,
                expires_in=3600,
            )
        except Exception:
            pass

        return self._to_read_model(application, posting.title, cv_download_url)

    def _to_read_model(
        self,
        application: JobApplication,
        posting_title: Optional[str] = None,
        cv_download_url: Optional[str] = None,
    ) -> JobApplicationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh["from_status"]),
                to_status=str(sh["to_status"]),
                changed_at=sh["changed_at"],
                changed_by=str(sh["changed_by"]) if sh.get("changed_by") else None,
                comment=sh.get("comment"),
            )
            for sh in application.status_history
        ]

        matching_details_model = _build_matching_details_model(application.matching_details)
        cv_quality_model = _build_cv_quality_model(application.cv_quality)

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
            civility=application.civility,
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
            tjm_min=application.tjm_min,
            tjm_max=application.tjm_max,
            availability_date=application.availability_date,
            cv_s3_key=application.cv_s3_key,
            cv_filename=application.cv_filename,
            cv_download_url=cv_download_url,
            matching_score=application.matching_score,
            matching_details=matching_details_model,
            cv_quality_score=application.cv_quality_score,
            cv_quality=cv_quality_model,
            is_read=application.is_read,
            status=str(application.status),
            status_display=application.status.display_name,
            status_history=status_history,
            notes=application.notes,
            boond_candidate_id=application.boond_candidate_id,
            boond_sync_error=application.boond_sync_error,
            boond_synced_at=application.boond_synced_at,
            boond_sync_status=application.boond_sync_status,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )
