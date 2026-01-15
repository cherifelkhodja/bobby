"""Infrastructure adapters for quotation generator."""

from app.quotation_generator.infrastructure.adapters.boond_adapter import (
    BoondManagerAdapter,
)
from app.quotation_generator.infrastructure.adapters.libreoffice_adapter import (
    LibreOfficeAdapter,
)
from app.quotation_generator.infrastructure.adapters.redis_storage_adapter import (
    RedisStorageAdapter,
)
from app.quotation_generator.infrastructure.adapters.template_repository import (
    PostgresTemplateRepository,
)

__all__ = [
    "BoondManagerAdapter",
    "LibreOfficeAdapter",
    "RedisStorageAdapter",
    "PostgresTemplateRepository",
]
