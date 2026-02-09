"""CV Template domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class CvTemplate:
    """CV Template entity representing a Word template for CV transformation."""

    name: str  # Unique identifier (e.g., "gemini", "craftmania")
    display_name: str  # Human-readable name (e.g., "Template Gemini")
    file_content: bytes  # Binary content of the .docx file
    file_name: str  # Original filename
    description: str | None = None
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_content(self, file_content: bytes, file_name: str) -> None:
        """Update the template file content."""
        self.file_content = file_content
        self.file_name = file_name
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the template."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the template."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
