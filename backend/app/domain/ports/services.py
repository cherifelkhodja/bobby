"""Service port interfaces for external services."""

from typing import Any, Optional, Protocol

from app.domain.entities import Candidate, Opportunity


class BoondServicePort(Protocol):
    """Port for BoondManager API operations."""

    async def get_opportunities(self) -> list[Opportunity]:
        """Fetch opportunities from BoondManager."""
        ...

    async def get_opportunity(self, external_id: str) -> Optional[Opportunity]:
        """Fetch single opportunity from BoondManager."""
        ...

    async def create_candidate(self, candidate: Candidate) -> str:
        """Create candidate in BoondManager. Returns external ID."""
        ...

    async def create_positioning(
        self,
        candidate_external_id: str,
        opportunity_external_id: str,
    ) -> str:
        """Create positioning in BoondManager. Returns positioning ID."""
        ...

    async def health_check(self) -> bool:
        """Check BoondManager API availability."""
        ...


class EmailServicePort(Protocol):
    """Port for email sending operations."""

    async def send_verification_email(self, to: str, token: str, name: str) -> bool:
        """Send email verification link."""
        ...

    async def send_password_reset_email(self, to: str, token: str, name: str) -> bool:
        """Send password reset link."""
        ...

    async def send_magic_link_email(self, to: str, token: str, name: str) -> bool:
        """Send magic link for passwordless login."""
        ...

    async def send_cooptation_confirmation(
        self,
        to: str,
        name: str,
        candidate_name: str,
        opportunity_title: str,
    ) -> bool:
        """Send cooptation submission confirmation."""
        ...

    async def send_cooptation_status_update(
        self,
        to: str,
        name: str,
        candidate_name: str,
        opportunity_title: str,
        new_status: str,
    ) -> bool:
        """Send cooptation status update notification."""
        ...

    async def send_invitation_email(
        self,
        to_email: str,
        token: str,
        role: str,
    ) -> bool:
        """Send invitation email to join the platform."""
        ...


class CacheServicePort(Protocol):
    """Port for caching operations."""

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> bool:
        """Set value in cache with TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern. Returns count of deleted keys."""
        ...


class CvTextExtractorPort(Protocol):
    """Port for extracting text from CV documents."""

    def extract(self, content: bytes) -> str:
        """Extract text from document content.

        Args:
            content: Binary content of the document.

        Returns:
            Extracted text.

        Raises:
            ValueError: If extraction fails.
        """
        ...


class CvDataExtractorPort(Protocol):
    """Port for extracting structured data from CV text using AI."""

    async def extract_cv_data(self, cv_text: str) -> dict[str, Any]:
        """Extract structured CV data from text.

        Args:
            cv_text: Raw text extracted from CV.

        Returns:
            Structured CV data dictionary.

        Raises:
            ValueError: If extraction fails.
        """
        ...


class CvDocumentGeneratorPort(Protocol):
    """Port for generating CV documents from templates."""

    def generate(self, template_content: bytes, cv_data: dict[str, Any]) -> bytes:
        """Generate document from template and data.

        Args:
            template_content: Binary content of the template.
            cv_data: Structured CV data.

        Returns:
            Generated document as bytes.

        Raises:
            ValueError: If generation fails.
        """
        ...


class TurnoverITServicePort(Protocol):
    """Port for Turnover-IT API operations."""

    async def create_job(self, job_payload: dict[str, Any]) -> str:
        """Create a job posting on Turnover-IT.

        Args:
            job_payload: Job data formatted for Turnover-IT API.

        Returns:
            Turnover-IT job reference/ID.

        Raises:
            TurnoverITError: If API call fails.
        """
        ...

    async def update_job(self, reference: str, job_payload: dict[str, Any]) -> bool:
        """Update an existing job posting on Turnover-IT.

        Args:
            reference: Turnover-IT job reference.
            job_payload: Updated job data.

        Returns:
            True if update was successful.

        Raises:
            TurnoverITError: If API call fails.
        """
        ...

    async def close_job(self, reference: str) -> bool:
        """Close/deactivate a job posting on Turnover-IT.

        Args:
            reference: Turnover-IT job reference.

        Returns:
            True if closing was successful.

        Raises:
            TurnoverITError: If API call fails.
        """
        ...

    async def get_skills(self, search: Optional[str] = None) -> list[dict[str, str]]:
        """Get available skills from Turnover-IT.

        Args:
            search: Optional search query to filter skills.

        Returns:
            List of skills with name and slug.
        """
        ...

    async def health_check(self) -> bool:
        """Check Turnover-IT API availability.

        Returns:
            True if API is available.
        """
        ...


class S3StorageServicePort(Protocol):
    """Port for S3/MinIO object storage operations."""

    async def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Upload a file to S3 storage.

        Args:
            key: Storage key/path for the file.
            content: File content as bytes.
            content_type: MIME type of the file.

        Returns:
            The storage key of the uploaded file.

        Raises:
            S3StorageError: If upload fails.
        """
        ...

    async def download_file(self, key: str) -> bytes:
        """Download a file from S3 storage.

        Args:
            key: Storage key/path of the file.

        Returns:
            File content as bytes.

        Raises:
            S3StorageError: If download fails.
        """
        ...

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for file download.

        Args:
            key: Storage key/path of the file.
            expires_in: URL expiration time in seconds (default 1 hour).

        Returns:
            Presigned URL for direct download.

        Raises:
            S3StorageError: If URL generation fails.
        """
        ...

    async def delete_file(self, key: str) -> bool:
        """Delete a file from S3 storage.

        Args:
            key: Storage key/path of the file.

        Returns:
            True if deletion was successful.

        Raises:
            S3StorageError: If deletion fails.
        """
        ...

    async def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3 storage.

        Args:
            key: Storage key/path of the file.

        Returns:
            True if file exists.
        """
        ...


class CvMatchingServicePort(Protocol):
    """Port for AI-powered CV matching analysis."""

    async def calculate_match(
        self,
        cv_text: str,
        job_description: str,
    ) -> dict[str, Any]:
        """Calculate matching score between CV and job description.

        Args:
            cv_text: Extracted text from candidate's CV.
            job_description: Job posting description and requirements.

        Returns:
            Matching result dictionary with:
                - score: int (0-100)
                - strengths: list[str] - matching skills/experience
                - gaps: list[str] - missing requirements
                - summary: str - brief analysis summary

        Raises:
            CvMatchingError: If analysis fails.
        """
        ...
