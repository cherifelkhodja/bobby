"""Service factory for centralized dependency injection.

This module provides a ServiceFactory class that centralizes the creation
of repositories, use cases, and external services. It reduces boilerplate
in route handlers and makes testing easier.
"""

from functools import cached_property
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings


class ServiceFactory:
    """Factory for creating application services with proper dependencies.

    Usage in routes:
        @router.post("")
        async def create_cooptation(
            request: CreateCooptationRequest,
            services: ServiceFactoryDep,
        ):
            use_case = services.create_cooptation_use_case()
            return await use_case.execute(command)
    """

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._repositories_cache: dict = {}

    # =========================================================================
    # Repositories
    # =========================================================================

    @property
    def user_repository(self):
        """Get or create UserRepository."""
        from app.infrastructure.database.repositories import UserRepository
        if "user" not in self._repositories_cache:
            self._repositories_cache["user"] = UserRepository(self._db)
        return self._repositories_cache["user"]

    @property
    def candidate_repository(self):
        """Get or create CandidateRepository."""
        from app.infrastructure.database.repositories import CandidateRepository
        if "candidate" not in self._repositories_cache:
            self._repositories_cache["candidate"] = CandidateRepository(self._db)
        return self._repositories_cache["candidate"]

    @property
    def opportunity_repository(self):
        """Get or create OpportunityRepository."""
        from app.infrastructure.database.repositories import OpportunityRepository
        if "opportunity" not in self._repositories_cache:
            self._repositories_cache["opportunity"] = OpportunityRepository(self._db)
        return self._repositories_cache["opportunity"]

    @property
    def cooptation_repository(self):
        """Get or create CooptationRepository."""
        from app.infrastructure.database.repositories import CooptationRepository
        if "cooptation" not in self._repositories_cache:
            self._repositories_cache["cooptation"] = CooptationRepository(self._db)
        return self._repositories_cache["cooptation"]

    @property
    def invitation_repository(self):
        """Get or create InvitationRepository."""
        from app.infrastructure.database.repositories import InvitationRepository
        if "invitation" not in self._repositories_cache:
            self._repositories_cache["invitation"] = InvitationRepository(self._db)
        return self._repositories_cache["invitation"]

    @property
    def published_opportunity_repository(self):
        """Get or create PublishedOpportunityRepository."""
        from app.infrastructure.database.repositories import PublishedOpportunityRepository
        if "published_opportunity" not in self._repositories_cache:
            self._repositories_cache["published_opportunity"] = PublishedOpportunityRepository(self._db)
        return self._repositories_cache["published_opportunity"]

    @property
    def job_posting_repository(self):
        """Get or create JobPostingRepository."""
        from app.infrastructure.database.repositories import JobPostingRepository
        if "job_posting" not in self._repositories_cache:
            self._repositories_cache["job_posting"] = JobPostingRepository(self._db)
        return self._repositories_cache["job_posting"]

    @property
    def job_application_repository(self):
        """Get or create JobApplicationRepository."""
        from app.infrastructure.database.repositories import JobApplicationRepository
        if "job_application" not in self._repositories_cache:
            self._repositories_cache["job_application"] = JobApplicationRepository(self._db)
        return self._repositories_cache["job_application"]

    @property
    def cv_template_repository(self):
        """Get or create CvTemplateRepository."""
        from app.infrastructure.database.repositories import CvTemplateRepository
        if "cv_template" not in self._repositories_cache:
            self._repositories_cache["cv_template"] = CvTemplateRepository(self._db)
        return self._repositories_cache["cv_template"]

    @property
    def cv_transformation_log_repository(self):
        """Get or create CvTransformationLogRepository."""
        from app.infrastructure.database.repositories import CvTransformationLogRepository
        if "cv_transformation_log" not in self._repositories_cache:
            self._repositories_cache["cv_transformation_log"] = CvTransformationLogRepository(self._db)
        return self._repositories_cache["cv_transformation_log"]

    @property
    def business_lead_repository(self):
        """Get or create BusinessLeadRepository."""
        from app.infrastructure.database.repositories import BusinessLeadRepository
        if "business_lead" not in self._repositories_cache:
            self._repositories_cache["business_lead"] = BusinessLeadRepository(self._db)
        return self._repositories_cache["business_lead"]

    # =========================================================================
    # External Services
    # =========================================================================

    @cached_property
    def boond_client(self):
        """Get or create BoondClient."""
        from app.infrastructure.boond.client import BoondClient
        return BoondClient(self._settings)

    @cached_property
    def email_service(self):
        """Get or create EmailService."""
        from app.infrastructure.email.sender import EmailService
        return EmailService(self._settings)

    @cached_property
    def gemini_anonymizer(self):
        """Get or create GeminiAnonymizer."""
        from app.infrastructure.anonymizer.gemini_anonymizer import GeminiAnonymizer
        return GeminiAnonymizer(self._settings)

    # =========================================================================
    # Use Cases - Auth
    # =========================================================================

    def create_login_use_case(self):
        """Create LoginUseCase."""
        from app.application.use_cases.auth import LoginUseCase
        return LoginUseCase(self.user_repository)

    def create_register_use_case(self):
        """Create RegisterUserUseCase."""
        from app.application.use_cases.auth import RegisterUserUseCase
        return RegisterUserUseCase(self.user_repository, self.email_service)

    def create_refresh_token_use_case(self):
        """Create RefreshTokenUseCase."""
        from app.application.use_cases.auth import RefreshTokenUseCase
        return RefreshTokenUseCase(self.user_repository)

    def create_verify_email_use_case(self):
        """Create VerifyEmailUseCase."""
        from app.application.use_cases.auth import VerifyEmailUseCase
        return VerifyEmailUseCase(self.user_repository)

    def create_forgot_password_use_case(self):
        """Create ForgotPasswordUseCase."""
        from app.application.use_cases.auth import ForgotPasswordUseCase
        return ForgotPasswordUseCase(self.user_repository, self.email_service)

    def create_reset_password_use_case(self):
        """Create ResetPasswordUseCase."""
        from app.application.use_cases.auth import ResetPasswordUseCase
        return ResetPasswordUseCase(self.user_repository)

    # =========================================================================
    # Use Cases - Cooptations
    # =========================================================================

    def create_cooptation_use_case(self):
        """Create CreateCooptationUseCase."""
        from app.application.use_cases.cooptations import CreateCooptationUseCase
        return CreateCooptationUseCase(
            cooptation_repository=self.cooptation_repository,
            candidate_repository=self.candidate_repository,
            opportunity_repository=self.opportunity_repository,
            published_opportunity_repository=self.published_opportunity_repository,
            user_repository=self.user_repository,
            boond_client=self.boond_client,
            email_service=self.email_service,
        )

    def create_list_cooptations_use_case(self):
        """Create ListCooptationsUseCase."""
        from app.application.use_cases.cooptations import ListCooptationsUseCase
        return ListCooptationsUseCase(
            cooptation_repository=self.cooptation_repository,
            candidate_repository=self.candidate_repository,
            opportunity_repository=self.opportunity_repository,
        )

    def create_get_cooptation_use_case(self):
        """Create GetCooptationUseCase."""
        from app.application.use_cases.cooptations import GetCooptationUseCase
        return GetCooptationUseCase(
            cooptation_repository=self.cooptation_repository,
            candidate_repository=self.candidate_repository,
            opportunity_repository=self.opportunity_repository,
        )

    def create_update_cooptation_status_use_case(self):
        """Create UpdateCooptationStatusUseCase."""
        from app.application.use_cases.cooptations import UpdateCooptationStatusUseCase
        return UpdateCooptationStatusUseCase(
            cooptation_repository=self.cooptation_repository,
            candidate_repository=self.candidate_repository,
            opportunity_repository=self.opportunity_repository,
        )

    # =========================================================================
    # Use Cases - Invitations
    # =========================================================================

    def create_send_invitation_use_case(self):
        """Create SendInvitationUseCase."""
        from app.application.use_cases.invitations import SendInvitationUseCase
        return SendInvitationUseCase(
            invitation_repository=self.invitation_repository,
            user_repository=self.user_repository,
            email_service=self.email_service,
        )

    def create_accept_invitation_use_case(self):
        """Create AcceptInvitationUseCase."""
        from app.application.use_cases.invitations import AcceptInvitationUseCase
        return AcceptInvitationUseCase(
            invitation_repository=self.invitation_repository,
            user_repository=self.user_repository,
        )

    # =========================================================================
    # Use Cases - Published Opportunities
    # =========================================================================

    def create_get_my_boond_opportunities_use_case(self):
        """Create GetMyBoondOpportunitiesUseCase."""
        from app.application.use_cases.published_opportunities import GetMyBoondOpportunitiesUseCase
        return GetMyBoondOpportunitiesUseCase(
            boond_client=self.boond_client,
            published_opportunity_repository=self.published_opportunity_repository,
            user_repository=self.user_repository,
        )

    def create_anonymize_opportunity_use_case(self):
        """Create AnonymizeOpportunityUseCase."""
        from app.application.use_cases.published_opportunities import AnonymizeOpportunityUseCase
        return AnonymizeOpportunityUseCase(
            anonymizer=self.gemini_anonymizer,
        )

    def create_publish_opportunity_use_case(self):
        """Create PublishOpportunityUseCase."""
        from app.application.use_cases.published_opportunities import PublishOpportunityUseCase
        return PublishOpportunityUseCase(
            published_opportunity_repository=self.published_opportunity_repository,
        )

    # =========================================================================
    # Use Cases - Admin
    # =========================================================================

    def create_list_users_use_case(self):
        """Create ListUsersUseCase."""
        from app.application.use_cases.admin.users import ListUsersUseCase
        return ListUsersUseCase(user_repository=self.user_repository)

    def create_get_user_use_case(self):
        """Create GetUserUseCase."""
        from app.application.use_cases.admin.users import GetUserUseCase
        return GetUserUseCase(user_repository=self.user_repository)

    def create_update_user_use_case(self):
        """Create UpdateUserUseCase."""
        from app.application.use_cases.admin.users import UpdateUserUseCase
        return UpdateUserUseCase(user_repository=self.user_repository)

    def create_delete_user_use_case(self):
        """Create DeleteUserUseCase."""
        from app.application.use_cases.admin.users import DeleteUserUseCase
        return DeleteUserUseCase(user_repository=self.user_repository)

    def create_get_boond_status_use_case(self):
        """Create GetBoondStatusUseCase."""
        from app.application.use_cases.admin.boond import GetBoondStatusUseCase
        return GetBoondStatusUseCase(boond_client=self.boond_client)

    def create_sync_boond_opportunities_use_case(self):
        """Create SyncBoondOpportunitiesUseCase."""
        from app.application.use_cases.admin.boond import SyncBoondOpportunitiesUseCase
        return SyncBoondOpportunitiesUseCase(
            boond_client=self.boond_client,
            opportunity_repository=self.opportunity_repository,
        )

    # =========================================================================
    # Use Cases - HR
    # =========================================================================

    def create_job_posting_use_case(self):
        """Create CreateJobPostingUseCase."""
        from app.application.use_cases.job_postings import CreateJobPostingUseCase
        return CreateJobPostingUseCase(
            job_posting_repository=self.job_posting_repository,
            opportunity_repository=self.opportunity_repository,
        )

    def create_list_job_postings_use_case(self):
        """Create ListJobPostingsUseCase."""
        from app.application.use_cases.job_postings import ListJobPostingsUseCase
        return ListJobPostingsUseCase(
            job_posting_repository=self.job_posting_repository,
        )

    def create_submit_job_application_use_case(self):
        """Create SubmitJobApplicationUseCase."""
        from app.application.use_cases.job_applications import SubmitJobApplicationUseCase
        return SubmitJobApplicationUseCase(
            job_application_repository=self.job_application_repository,
            job_posting_repository=self.job_posting_repository,
        )

    # =========================================================================
    # Use Cases - CV Transformer
    # =========================================================================

    def create_transform_cv_use_case(self):
        """Create TransformCvUseCase."""
        from app.application.use_cases.cv_transformer import TransformCvUseCase
        return TransformCvUseCase(
            cv_template_repository=self.cv_template_repository,
            cv_transformation_log_repository=self.cv_transformation_log_repository,
        )
