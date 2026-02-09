"""Template management use cases."""

import logging

from app.quotation_generator.domain.ports import TemplateRepositoryPort
from app.quotation_generator.services.template_filler import (
    THALES_PSTF_VARIABLES,
    TemplateFillerService,
)

logger = logging.getLogger(__name__)


class UploadTemplateUseCase:
    """Use case for uploading a quotation template.

    This use case:
    1. Validates the template format
    2. Optionally validates required variables
    3. Stores the template in the repository
    """

    def __init__(
        self,
        template_repository: TemplateRepositoryPort,
        template_filler: TemplateFillerService,
    ) -> None:
        """Initialize use case.

        Args:
            template_repository: Repository for template storage.
            template_filler: Service for template validation.
        """
        self.template_repository = template_repository
        self.template_filler = template_filler

    async def execute(
        self,
        name: str,
        content: bytes,
        display_name: str,
        description: str | None = None,
        validate_variables: bool = True,
    ) -> dict:
        """Upload or update a template.

        Args:
            name: Template identifier.
            content: Template file content.
            display_name: Human-readable name.
            description: Optional description.
            validate_variables: Whether to validate required variables.

        Returns:
            Dictionary with upload result:
            - name: str
            - is_valid: bool
            - variables_found: list
            - missing_variables: list (if validate_variables=True)
            - warnings: list
        """
        logger.info(f"Uploading template: {name}")

        result = {
            "name": name,
            "is_valid": True,
            "variables_found": [],
            "missing_variables": [],
            "warnings": [],
        }

        # Validate template if requested
        if validate_variables:
            validation = self.template_filler.validate_template(
                content,
                required_variables=THALES_PSTF_VARIABLES,
            )
            result["variables_found"] = validation["variables_found"]
            result["missing_variables"] = validation["missing_variables"]

            if not validation["is_valid"]:
                result["warnings"] = validation["errors"]
                # Still allow upload with warnings
                logger.warning(f"Template {name} has validation warnings: {validation['errors']}")
        else:
            # Just extract variables without validation
            try:
                result["variables_found"] = self.template_filler.get_template_variables(content)
            except Exception as e:
                result["warnings"].append(f"Could not extract variables: {str(e)}")

        # Save template
        await self.template_repository.save_template(
            name=name,
            content=content,
            display_name=display_name,
            description=description,
        )

        logger.info(f"Template {name} uploaded successfully")
        return result


class ListTemplatesUseCase:
    """Use case for listing available templates."""

    def __init__(self, template_repository: TemplateRepositoryPort) -> None:
        """Initialize use case.

        Args:
            template_repository: Repository for template storage.
        """
        self.template_repository = template_repository

    async def execute(self) -> list[dict]:
        """List all available templates.

        Returns:
            List of template metadata dictionaries.
        """
        return await self.template_repository.list_templates()


class GetTemplateUseCase:
    """Use case for getting a template."""

    def __init__(self, template_repository: TemplateRepositoryPort) -> None:
        """Initialize use case.

        Args:
            template_repository: Repository for template storage.
        """
        self.template_repository = template_repository

    async def execute(self, name: str) -> bytes | None:
        """Get template content.

        Args:
            name: Template identifier.

        Returns:
            Template content or None if not found.
        """
        return await self.template_repository.get_template(name)


class DeleteTemplateUseCase:
    """Use case for deleting a template."""

    def __init__(self, template_repository: TemplateRepositoryPort) -> None:
        """Initialize use case.

        Args:
            template_repository: Repository for template storage.
        """
        self.template_repository = template_repository

    async def execute(self, name: str) -> bool:
        """Delete a template.

        Args:
            name: Template identifier.

        Returns:
            True if deleted, False if not found.
        """
        return await self.template_repository.delete_template(name)
