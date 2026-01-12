"""Phone value object."""

import re
from dataclasses import dataclass

from app.domain.exceptions import InvalidPhoneError


@dataclass(frozen=True, slots=True)
class Phone:
    """Phone number value object with validation."""

    value: str

    def __post_init__(self) -> None:
        """Validate and normalize phone number after initialization."""
        normalized = self._normalize(self.value)
        if not self._is_valid_phone(normalized):
            raise InvalidPhoneError(self.value)
        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def _normalize(phone: str) -> str:
        """Normalize phone number by removing spaces and special characters."""
        return re.sub(r"[\s\-\.\(\)]", "", phone)

    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        """Check if phone format is valid (French or international)."""
        # French format: 0XXXXXXXXX or +33XXXXXXXXX
        # International: +XXXXXXXXXXX (10-15 digits)
        pattern = r"^(\+33[1-9][0-9]{8}|0[1-9][0-9]{8}|\+[1-9][0-9]{9,14})$"
        return bool(re.match(pattern, phone))

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Compare phone numbers."""
        if isinstance(other, Phone):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == self._normalize(other)
        return False

    def __hash__(self) -> int:
        """Hash based on normalized phone."""
        return hash(self.value)

    @property
    def formatted(self) -> str:
        """Return phone in formatted display format."""
        if self.value.startswith("+33"):
            # French international format: +33 X XX XX XX XX
            digits = self.value[3:]
            return f"+33 {digits[0]} {digits[1:3]} {digits[3:5]} {digits[5:7]} {digits[7:9]}"
        if self.value.startswith("0"):
            # French national format: 0X XX XX XX XX
            return f"{self.value[0:2]} {self.value[2:4]} {self.value[4:6]} {self.value[6:8]} {self.value[8:10]}"
        return self.value
