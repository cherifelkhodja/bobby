"""Template repository port interface for Excel template operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class TemplateRepositoryPort(ABC):
    """Interface for template storage and retrieval.

    This port defines the contract for managing Excel templates
    used to generate PSTF documents.
    """

    @abstractmethod
    async def get_template(self, name: str) -> bytes | None:
        """Retrieve a template by name.

        Args:
            name: Template identifier (e.g., 'thales_pstf').

        Returns:
            Template file content as bytes, or None if not found.
        """
        ...

    @abstractmethod
    async def save_template(
        self,
        name: str,
        content: bytes,
        display_name: str,
        description: str | None = None,
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
        ...

    @abstractmethod
    async def delete_template(self, name: str) -> bool:
        """Delete a template.

        Args:
            name: Template identifier.

        Returns:
            True if deleted, False if not found.
        """
        ...

    @abstractmethod
    async def list_templates(self) -> list[dict]:
        """List all available templates.

        Returns:
            List of template metadata dictionaries with keys:
            - name: Template identifier
            - display_name: Human-readable name
            - description: Optional description
            - updated_at: Last update timestamp
        """
        ...

    @abstractmethod
    async def template_exists(self, name: str) -> bool:
        """Check if a template exists.

        Args:
            name: Template identifier.

        Returns:
            True if template exists.
        """
        ...

    @abstractmethod
    async def get_template_path(self, name: str) -> Path | None:
        """Get filesystem path for a template.

        This is used for LibreOffice conversion which requires
        a file path rather than bytes.

        Args:
            name: Template identifier.

        Returns:
            Path to template file, or None if not found.
        """
        ...
