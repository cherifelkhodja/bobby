"""Domain ports - interfaces for external dependencies."""

from app.domain.ports.repositories import (
    CooptationRepositoryPort,
    CvTemplateRepositoryPort,
    CvTransformationLogRepositoryPort,
    OpportunityRepositoryPort,
    UserRepositoryPort,
)
from app.domain.ports.services import (
    BoondServicePort,
    CacheServicePort,
    CvDataExtractorPort,
    CvDocumentGeneratorPort,
    CvTextExtractorPort,
    EmailServicePort,
)

__all__ = [
    "CooptationRepositoryPort",
    "CvTemplateRepositoryPort",
    "CvTransformationLogRepositoryPort",
    "OpportunityRepositoryPort",
    "UserRepositoryPort",
    "BoondServicePort",
    "CacheServicePort",
    "CvDataExtractorPort",
    "CvDocumentGeneratorPort",
    "CvTextExtractorPort",
    "EmailServicePort",
]
