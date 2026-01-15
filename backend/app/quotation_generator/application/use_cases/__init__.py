"""Use cases for quotation generator."""

from app.quotation_generator.application.use_cases.preview_batch import (
    PreviewBatchUseCase,
)
from app.quotation_generator.application.use_cases.generate_batch import (
    GenerateBatchUseCase,
)
from app.quotation_generator.application.use_cases.get_progress import (
    GetBatchProgressUseCase,
)
from app.quotation_generator.application.use_cases.download_batch import (
    DownloadBatchUseCase,
)
from app.quotation_generator.application.use_cases.template_management import (
    UploadTemplateUseCase,
    ListTemplatesUseCase,
)

__all__ = [
    "PreviewBatchUseCase",
    "GenerateBatchUseCase",
    "GetBatchProgressUseCase",
    "DownloadBatchUseCase",
    "UploadTemplateUseCase",
    "ListTemplatesUseCase",
]
