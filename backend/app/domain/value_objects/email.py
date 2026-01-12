"""Email value object."""

import re
from dataclasses import dataclass

from app.domain.exceptions import InvalidEmailError


@dataclass(frozen=True, slots=True)
class Email:
    """Email value object with validation."""

    value: str

    def __post_init__(self) -> None:
        """Validate email format after initialization."""
        if not self._is_valid_email(self.value):
            raise InvalidEmailError(self.value)

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Check if email format is valid."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Compare emails case-insensitively."""
        if isinstance(other, Email):
            return self.value.lower() == other.value.lower()
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return False

    def __hash__(self) -> int:
        """Hash based on lowercase email."""
        return hash(self.value.lower())

    @property
    def domain(self) -> str:
        """Extract domain from email."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Extract local part from email."""
        return self.value.split("@")[0]
