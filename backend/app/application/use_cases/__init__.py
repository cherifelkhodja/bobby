"""Application use cases."""

from app.application.use_cases.admin import (
    ActivateUserUseCase,
    ChangeUserRoleUseCase,
    DeactivateUserUseCase,
    DeleteUserUseCase,
    GetBoondResourcesUseCase,
    # Boond
    GetBoondStatusUseCase,
    GetUserUseCase,
    # Users
    ListUsersUseCase,
    SyncBoondOpportunitiesUseCase,
    TestBoondConnectionUseCase,
    UpdateUserUseCase,
)
from app.application.use_cases.auth import (
    ForgotPasswordUseCase,
    LoginUseCase,
    RefreshTokenUseCase,
    RegisterUserUseCase,
    ResetPasswordUseCase,
    VerifyEmailUseCase,
)
from app.application.use_cases.cooptations import (
    CreateCooptationUseCase,
    GetCooptationStatsUseCase,
    GetCooptationUseCase,
    ListCooptationsUseCase,
    UpdateCooptationStatusUseCase,
)
from app.application.use_cases.cv_transformer import (
    GetTemplatesUseCase,
    GetTransformationStatsUseCase,
    TransformCvUseCase,
    UploadTemplateUseCase,
)
from app.application.use_cases.job_applications import (
    CreateCandidateInBoondUseCase,
    GetApplicationCvUrlUseCase,
    GetApplicationUseCase,
    ListApplicationsForPostingUseCase,
    SubmitApplicationUseCase,
    UpdateApplicationNoteUseCase,
    UpdateApplicationStatusUseCase,
)
from app.application.use_cases.job_postings import (
    CloseJobPostingUseCase,
    CreateJobPostingUseCase,
    GetJobPostingByTokenUseCase,
    GetJobPostingUseCase,
    ListJobPostingsUseCase,
    ListOpenOpportunitiesForHRUseCase,
    PublishJobPostingUseCase,
    UpdateJobPostingUseCase,
)
from app.application.use_cases.opportunities import (
    ListOpportunitiesUseCase,
    SyncOpportunitiesUseCase,
)

__all__ = [
    # Auth
    "LoginUseCase",
    "RegisterUserUseCase",
    "VerifyEmailUseCase",
    "ForgotPasswordUseCase",
    "ResetPasswordUseCase",
    "RefreshTokenUseCase",
    # Cooptations
    "CreateCooptationUseCase",
    "ListCooptationsUseCase",
    "GetCooptationUseCase",
    "UpdateCooptationStatusUseCase",
    "GetCooptationStatsUseCase",
    # CV Transformer
    "TransformCvUseCase",
    "GetTemplatesUseCase",
    "UploadTemplateUseCase",
    "GetTransformationStatsUseCase",
    # HR - Job Postings
    "CloseJobPostingUseCase",
    "CreateJobPostingUseCase",
    "GetJobPostingByTokenUseCase",
    "GetJobPostingUseCase",
    "ListJobPostingsUseCase",
    "ListOpenOpportunitiesForHRUseCase",
    "PublishJobPostingUseCase",
    "UpdateJobPostingUseCase",
    # HR - Job Applications
    "CreateCandidateInBoondUseCase",
    "GetApplicationCvUrlUseCase",
    "GetApplicationUseCase",
    "ListApplicationsForPostingUseCase",
    "SubmitApplicationUseCase",
    "UpdateApplicationNoteUseCase",
    "UpdateApplicationStatusUseCase",
    # Opportunities
    "ListOpportunitiesUseCase",
    "SyncOpportunitiesUseCase",
    # Admin - Users
    "ListUsersUseCase",
    "GetUserUseCase",
    "UpdateUserUseCase",
    "ChangeUserRoleUseCase",
    "ActivateUserUseCase",
    "DeactivateUserUseCase",
    "DeleteUserUseCase",
    # Admin - Boond
    "GetBoondStatusUseCase",
    "SyncBoondOpportunitiesUseCase",
    "TestBoondConnectionUseCase",
    "GetBoondResourcesUseCase",
]
