"""Port for contract document generation."""

from typing import Any, Protocol


class ContractGeneratorPort(Protocol):
    """Port for generating contract documents from templates."""

    async def generate_draft(
        self,
        template_context: dict[str, Any],
    ) -> bytes:
        """Generate a contract draft document.

        Args:
            template_context: Variables for the contract template.

        Returns:
            Generated document content as bytes (DOCX format).
        """
        ...
