"""PostgreSQL template repository implementing TemplateRepositoryPort."""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.quotation_generator.domain.exceptions import TemplateStorageError
from app.quotation_generator.domain.ports import TemplateRepositoryPort
from app.quotation_generator.infrastructure.models import QuotationTemplate

logger = logging.getLogger(__name__)


class PostgresTemplateRepository(TemplateRepositoryPort):
    """PostgreSQL adapter for template storage.

    This adapter implements the TemplateRepositoryPort interface to store
    and retrieve Excel templates from the database.
    """

    def __init__(
        self,
        session: AsyncSession,
        temp_dir: Optional[Path] = None,
    ) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session.
            temp_dir: Directory for temporary files.
        """
        self.session = session
        self.temp_dir = temp_dir or Path(tempfile.gettempdir())
        self._temp_files: dict[str, Path] = {}

    async def get_template(self, name: str) -> Optional[bytes]:
        """Retrieve a template by name.

        Args:
            name: Template identifier (e.g., 'thales_pstf').

        Returns:
            Template file content as bytes, or None if not found.
        """
        result = await self.session.execute(
            select(QuotationTemplate).where(
                QuotationTemplate.name == name,
                QuotationTemplate.is_active == True,
            )
        )
        template = result.scalar_one_or_none()

        if template:
            return template.file_content
        return None

    async def save_template(
        self,
        name: str,
        content: bytes,
        display_name: str,
        description: Optional[str] = None,
    ) -> None:
        """Save or update a template.

        Args:
            name: Template identifier.
            content: Template file content.
            display_name: Human-readable template name.
            description: Optional template description.

        Raises:
            TemplateStorageError: If save fails.
        """
        try:
            # Check if template exists
            result = await self.session.execute(
                select(QuotationTemplate).where(QuotationTemplate.name == name)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing template
                existing.file_content = content
                existing.display_name = display_name
                existing.description = description
                existing.updated_at = datetime.utcnow()
                logger.info(f"Updated template: {name}")
            else:
                # Create new template
                template = QuotationTemplate(
                    id=uuid4(),
                    name=name,
                    display_name=display_name,
                    description=description,
                    file_content=content,
                    file_name=f"{name}.xlsx",
                    is_active=True,
                )
                self.session.add(template)
                logger.info(f"Created template: {name}")

            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save template {name}: {e}")
            raise TemplateStorageError(f"Failed to save template: {str(e)}") from e

    async def delete_template(self, name: str) -> bool:
        """Delete a template (soft delete by setting is_active=False).

        Args:
            name: Template identifier.

        Returns:
            True if deleted, False if not found.
        """
        result = await self.session.execute(
            select(QuotationTemplate).where(QuotationTemplate.name == name)
        )
        template = result.scalar_one_or_none()

        if template:
            template.is_active = False
            template.updated_at = datetime.utcnow()
            await self.session.commit()
            logger.info(f"Deactivated template: {name}")
            return True

        return False

    async def list_templates(self) -> list[dict]:
        """List all available templates.

        Returns:
            List of template metadata dictionaries.
        """
        result = await self.session.execute(
            select(QuotationTemplate).where(QuotationTemplate.is_active == True)
        )
        templates = result.scalars().all()

        return [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in templates
        ]

    async def template_exists(self, name: str) -> bool:
        """Check if a template exists.

        Args:
            name: Template identifier.

        Returns:
            True if template exists and is active.
        """
        result = await self.session.execute(
            select(QuotationTemplate.id).where(
                QuotationTemplate.name == name,
                QuotationTemplate.is_active == True,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_template_path(self, name: str) -> Optional[Path]:
        """Get filesystem path for a template.

        This creates a temporary file with the template content
        for use with LibreOffice conversion.

        Args:
            name: Template identifier.

        Returns:
            Path to template file, or None if not found.
        """
        # Check if we already have a cached temp file
        if name in self._temp_files:
            path = self._temp_files[name]
            if path.exists():
                return path

        # Get template content
        content = await self.get_template(name)
        if not content:
            return None

        # Create temp file
        temp_path = self.temp_dir / f"template_{name}.xlsx"
        temp_path.write_bytes(content)
        self._temp_files[name] = temp_path

        logger.debug(f"Created temp file for template {name}: {temp_path}")
        return temp_path

    async def cleanup_temp_files(self) -> None:
        """Clean up temporary template files."""
        for name, path in list(self._temp_files.items()):
            try:
                if path.exists():
                    path.unlink()
                    logger.debug(f"Cleaned up temp file: {path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {path}: {e}")
            finally:
                del self._temp_files[name]
