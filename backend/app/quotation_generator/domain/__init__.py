"""Domain layer for quotation generator."""

from app.quotation_generator.domain.entities import (
    Quotation,
    QuotationLine,
    QuotationBatch,
)
from app.quotation_generator.domain.value_objects import (
    Money,
    Period,
    BatchStatus,
    QuotationStatus,
)
from app.quotation_generator.domain.exceptions import (
    QuotationGeneratorError,
    CSVParsingError,
    MissingColumnsError,
    ValidationError,
    BoondManagerAPIError,
    TemplateNotFoundError,
    PDFConversionError,
    BatchNotFoundError,
    DownloadNotReadyError,
    TemplateStorageError,
    TemplateFillerError,
)
from app.quotation_generator.domain.ports import (
    BatchStoragePort,
    ERPPort,
    PDFConverterPort,
    TemplateRepositoryPort,
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
