"""Domain layer for quotation generator."""

from app.quotation_generator.domain.entities import (
    Quotation,
    QuotationBatch,
    QuotationLine,
)
from app.quotation_generator.domain.exceptions import (
    BatchNotFoundError,
    BoondManagerAPIError,
    CSVParsingError,
    DownloadNotReadyError,
    MissingColumnsError,
    PDFConversionError,
    QuotationGeneratorError,
    TemplateFillerError,
    TemplateNotFoundError,
    TemplateStorageError,
    ValidationError,
)
from app.quotation_generator.domain.ports import (
    BatchStoragePort,
    ERPPort,
    PDFConverterPort,
    TemplateRepositoryPort,
)
from app.quotation_generator.domain.value_objects import (
    BatchStatus,
    Money,
    Period,
    QuotationStatus,
)

__all__ = [
    # Entities
    "Quotation",
    "QuotationLine",
    "QuotationBatch",
    # Value Objects
    "Money",
    "Period",
    "BatchStatus",
    "QuotationStatus",
    # Exceptions
    "QuotationGeneratorError",
    "CSVParsingError",
    "MissingColumnsError",
    "ValidationError",
    "BoondManagerAPIError",
    "TemplateNotFoundError",
    "PDFConversionError",
    "BatchNotFoundError",
    "DownloadNotReadyError",
    "TemplateStorageError",
    "TemplateFillerError",
    # Ports
    "BatchStoragePort",
    "ERPPort",
    "PDFConverterPort",
    "TemplateRepositoryPort",
]
