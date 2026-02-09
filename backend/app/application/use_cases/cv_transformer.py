"""CV Transformer use cases."""

from uuid import UUID

from app.domain.entities import CvTemplate, CvTransformationLog
from app.domain.ports import (
    CvDataExtractorPort,
    CvDocumentGeneratorPort,
    CvTemplateRepositoryPort,
    CvTextExtractorPort,
    CvTransformationLogRepositoryPort,
)


class TransformCvUseCase:
    """Use case for transforming a CV into a standardized Word document.

    Follows Dependency Inversion Principle - depends on abstractions (ports),
    not concrete implementations.
    """

    def __init__(
        self,
        template_repository: CvTemplateRepositoryPort,
        log_repository: CvTransformationLogRepositoryPort,
        data_extractor: CvDataExtractorPort,
        document_generator: CvDocumentGeneratorPort,
        pdf_text_extractor: CvTextExtractorPort,
        docx_text_extractor: CvTextExtractorPort,
    ) -> None:
        self._template_repository = template_repository
        self._log_repository = log_repository
        self._data_extractor = data_extractor
        self._document_generator = document_generator
        self._pdf_extractor = pdf_text_extractor
        self._docx_extractor = docx_text_extractor

    async def execute(
        self,
        user_id: UUID,
        template_name: str,
        file_content: bytes,
        filename: str,
        gemini_model: str | None = None,
    ) -> bytes:
        """Transform a CV file into a standardized Word document.

        Args:
            user_id: ID of the user performing the transformation.
            template_name: Name of the template to use.
            file_content: Binary content of the uploaded CV file.
            filename: Original filename (used to determine file type).
            gemini_model: Optional Gemini model to use (uses default if not set).

        Returns:
            Generated Word document as bytes.

        Raises:
            ValueError: If transformation fails at any step.
        """
        template: CvTemplate | None = None

        try:
            # Get the template
            template = await self._template_repository.get_by_name(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' non trouvé")

            if not template.is_active:
                raise ValueError(f"Template '{template_name}' n'est pas actif")

            # Extract text based on file type (Single Responsibility - delegate to extractors)
            cv_text = self._extract_text(file_content, filename)

            # Extract structured data using AI
            cv_data = await self._data_extractor.extract_cv_data(cv_text, gemini_model)

            # Generate the output document
            output_content = self._document_generator.generate(
                template_content=template.file_content,
                cv_data=cv_data,
            )

            # Log success
            log = CvTransformationLog.create_success(
                user_id=user_id,
                template_id=template.id,
                template_name=template_name,
                original_filename=filename,
            )
            await self._log_repository.save(log)

            return output_content

        except Exception as e:
            # Log failure
            log = CvTransformationLog.create_failure(
                user_id=user_id,
                template_name=template_name,
                original_filename=filename,
                error_message=str(e),
                template_id=template.id if template else None,
            )
            await self._log_repository.save(log)
            raise

    def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from file based on extension.

        Args:
            file_content: Binary content of the file.
            filename: Original filename.

        Returns:
            Extracted text.

        Raises:
            ValueError: If file type is not supported.
        """
        file_lower = filename.lower()
        if file_lower.endswith(".pdf"):
            return self._pdf_extractor.extract(file_content)
        elif file_lower.endswith(".docx"):
            return self._docx_extractor.extract(file_content)
        elif file_lower.endswith(".doc"):
            raise ValueError(
                "Les fichiers .doc ne sont pas supportés. Veuillez convertir en .docx ou .pdf"
            )
        else:
            raise ValueError("Format de fichier non supporté. Utilisez PDF ou DOCX")


class GetTemplatesUseCase:
    """Use case for getting available CV templates."""

    def __init__(self, template_repository: CvTemplateRepositoryPort) -> None:
        self._template_repository = template_repository

    async def execute(self, include_inactive: bool = False) -> list[dict]:
        """Get list of available templates.

        Args:
            include_inactive: If True, include inactive templates.

        Returns:
            List of template info dicts (without file content).
        """
        if include_inactive:
            templates = await self._template_repository.list_all()
        else:
            templates = await self._template_repository.list_active()

        return [
            {
                "id": str(t.id),
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "is_active": t.is_active,
                "updated_at": t.updated_at.isoformat(),
            }
            for t in templates
        ]


class UploadTemplateUseCase:
    """Use case for uploading or updating a CV template."""

    def __init__(self, template_repository: CvTemplateRepositoryPort) -> None:
        self._template_repository = template_repository

    async def execute(
        self,
        name: str,
        display_name: str,
        file_content: bytes,
        file_name: str,
        description: str | None = None,
    ) -> dict:
        """Upload or update a template.

        Args:
            name: Unique template identifier (e.g., "gemini", "craftmania").
            display_name: Human-readable name.
            file_content: Binary content of the .docx template file.
            file_name: Original filename.
            description: Optional description.

        Returns:
            Template info dict.
        """
        # Check if template exists
        existing = await self._template_repository.get_by_name(name)

        if existing:
            # Update existing template
            existing.update_content(file_content, file_name)
            existing.display_name = display_name
            existing.description = description
            template = await self._template_repository.save(existing)
        else:
            # Create new template
            template = CvTemplate(
                name=name,
                display_name=display_name,
                description=description,
                file_content=file_content,
                file_name=file_name,
            )
            template = await self._template_repository.save(template)

        return {
            "id": str(template.id),
            "name": template.name,
            "display_name": template.display_name,
            "description": template.description,
            "is_active": template.is_active,
            "updated_at": template.updated_at.isoformat(),
        }


class GetTransformationStatsUseCase:
    """Use case for getting CV transformation statistics."""

    def __init__(self, log_repository: CvTransformationLogRepositoryPort) -> None:
        self._log_repository = log_repository

    async def execute(self) -> dict:
        """Get transformation statistics.

        Returns:
            Dict with total count and per-user stats.
        """
        total = await self._log_repository.get_total_count(success_only=True)
        by_user = await self._log_repository.get_stats_by_user()

        return {
            "total": total,
            "by_user": by_user,
        }
