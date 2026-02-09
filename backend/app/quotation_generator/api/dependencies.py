"""API dependencies for quotation generator."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.dependencies import get_db
from app.quotation_generator.application.use_cases import (
    DownloadBatchUseCase,
    GenerateBatchUseCase,
    GetBatchProgressUseCase,
    ListTemplatesUseCase,
    PreviewBatchUseCase,
    UploadTemplateUseCase,
)
from app.quotation_generator.application.use_cases.generate_batch import (
    StartGenerationUseCase,
)
from app.quotation_generator.application.use_cases.get_progress import (
    GetBatchDetailsUseCase,
    ListUserBatchesUseCase,
)
from app.quotation_generator.infrastructure.adapters import (
    BoondManagerAdapter,
    LibreOfficeAdapter,
    PostgresTemplateRepository,
    RedisStorageAdapter,
)
from app.quotation_generator.services import CSVParserService, TemplateFillerService
from app.quotation_generator.services.boond_enrichment import BoondEnrichmentService


async def get_enrichment_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> BoondEnrichmentService:
    """Get BoondManager enrichment service."""
    return BoondEnrichmentService(settings)


async def get_csv_parser(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CSVParserService:
    """Get CSV parser service with enrichment."""
    enrichment_service = BoondEnrichmentService(settings)
    return CSVParserService(enrichment_service=enrichment_service)


def get_template_filler() -> TemplateFillerService:
    """Get template filler service."""
    return TemplateFillerService()


async def get_batch_storage(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedisStorageAdapter:
    """Get batch storage adapter."""
    return RedisStorageAdapter(settings.REDIS_URL)


async def get_erp_adapter(
    settings: Annotated[Settings, Depends(get_settings)],
) -> BoondManagerAdapter:
    """Get ERP (BoondManager) adapter."""
    return BoondManagerAdapter(settings)


def get_pdf_converter() -> LibreOfficeAdapter:
    """Get PDF converter adapter."""
    return LibreOfficeAdapter()


async def get_template_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostgresTemplateRepository:
    """Get template repository."""
    return PostgresTemplateRepository(db)


# Use Case factories


async def get_preview_batch_use_case(
    csv_parser: Annotated[CSVParserService, Depends(get_csv_parser)],
    batch_storage: Annotated[RedisStorageAdapter, Depends(get_batch_storage)],
    boond_adapter: Annotated[BoondManagerAdapter, Depends(get_erp_adapter)],
) -> PreviewBatchUseCase:
    """Get preview batch use case."""
    return PreviewBatchUseCase(csv_parser, batch_storage, boond_adapter)


async def get_generate_batch_use_case(
    batch_storage: Annotated[RedisStorageAdapter, Depends(get_batch_storage)],
    erp_adapter: Annotated[BoondManagerAdapter, Depends(get_erp_adapter)],
    template_repository: Annotated[PostgresTemplateRepository, Depends(get_template_repository)],
    pdf_converter: Annotated[LibreOfficeAdapter, Depends(get_pdf_converter)],
    template_filler: Annotated[TemplateFillerService, Depends(get_template_filler)],
) -> GenerateBatchUseCase:
    """Get generate batch use case."""
    return GenerateBatchUseCase(
        batch_storage=batch_storage,
        erp_adapter=erp_adapter,
        template_repository=template_repository,
        pdf_converter=pdf_converter,
        template_filler=template_filler,
    )


async def get_start_generation_use_case(
    batch_storage: Annotated[RedisStorageAdapter, Depends(get_batch_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StartGenerationUseCase:
    """Get start generation use case.

    Uses a factory to create GenerateBatchUseCase with fresh DB session
    for background task execution.
    """
    from app.infrastructure.database.connection import async_session_factory

    def create_generate_use_case() -> GenerateBatchUseCase:
        """Factory that creates GenerateBatchUseCase with fresh DB session."""
        # Create a new session for the background task
        session = async_session_factory()
        template_repository = PostgresTemplateRepository(session)

        return GenerateBatchUseCase(
            batch_storage=RedisStorageAdapter(settings.REDIS_URL),
            erp_adapter=BoondManagerAdapter(settings),
            template_repository=template_repository,
            pdf_converter=LibreOfficeAdapter(),
            template_filler=TemplateFillerService(),
        )

    return StartGenerationUseCase(batch_storage, create_generate_use_case)


async def get_progress_use_case(
    batch_storage: Annotated[RedisStorageAdapter, Depends(get_batch_storage)],
) -> GetBatchProgressUseCase:
    """Get batch progress use case."""
    return GetBatchProgressUseCase(batch_storage)


async def get_batch_details_use_case(
    batch_storage: Annotated[RedisStorageAdapter, Depends(get_batch_storage)],
) -> GetBatchDetailsUseCase:
    """Get batch details use case."""
    return GetBatchDetailsUseCase(batch_storage)


async def get_list_user_batches_use_case(
    batch_storage: Annotated[RedisStorageAdapter, Depends(get_batch_storage)],
) -> ListUserBatchesUseCase:
    """Get list user batches use case."""
    return ListUserBatchesUseCase(batch_storage)


async def get_download_batch_use_case(
    batch_storage: Annotated[RedisStorageAdapter, Depends(get_batch_storage)],
) -> DownloadBatchUseCase:
    """Get download batch use case."""
    return DownloadBatchUseCase(batch_storage)


async def get_upload_template_use_case(
    template_repository: Annotated[PostgresTemplateRepository, Depends(get_template_repository)],
    template_filler: Annotated[TemplateFillerService, Depends(get_template_filler)],
) -> UploadTemplateUseCase:
    """Get upload template use case."""
    return UploadTemplateUseCase(template_repository, template_filler)


async def get_list_templates_use_case(
    template_repository: Annotated[PostgresTemplateRepository, Depends(get_template_repository)],
) -> ListTemplatesUseCase:
    """Get list templates use case."""
    return ListTemplatesUseCase(template_repository)
