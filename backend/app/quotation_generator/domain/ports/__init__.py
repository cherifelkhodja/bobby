"""Domain ports (interfaces) for quotation generator."""

from app.quotation_generator.domain.ports.batch_storage_port import BatchStoragePort
from app.quotation_generator.domain.ports.erp_port import ERPPort
from app.quotation_generator.domain.ports.pdf_converter_port import PDFConverterPort
from app.quotation_generator.domain.ports.template_repository_port import (
    TemplateRepositoryPort,
)

__all__ = [
    "BatchStoragePort",
    "ERPPort",
    "PDFConverterPort",
    "TemplateRepositoryPort",
]
