"""Port for electronic signature service."""

from typing import Protocol


class SignatureServicePort(Protocol):
    """Port for electronic signature operations (YouSign)."""

    async def create_procedure(
        self,
        document_content: bytes,
        document_name: str,
        signer_name: str,
        signer_email: str,
        signer_phone: str | None = None,
    ) -> str:
        """Create a signature procedure.

        Args:
            document_content: PDF document content.
            document_name: Document name.
            signer_name: Name of the signer.
            signer_email: Email of the signer.
            signer_phone: Phone of the signer (optional).

        Returns:
            Procedure ID from the signature service.
        """
        ...

    async def get_procedure_status(self, procedure_id: str) -> str:
        """Get the status of a signature procedure.

        Args:
            procedure_id: ID of the procedure.

        Returns:
            Status string.
        """
        ...

    async def get_signed_document(self, procedure_id: str) -> bytes:
        """Download the signed document.

        Args:
            procedure_id: ID of the completed procedure.

        Returns:
            Signed PDF content as bytes.
        """
        ...
