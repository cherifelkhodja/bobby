"""Period value object for handling date ranges."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Period:
    """Immutable value object representing a date period.

    Attributes:
        start_date: Start date of the period.
        end_date: End date of the period.

    Raises:
        ValueError: If end_date is before start_date.

    Example:
        >>> period = Period(date(2026, 1, 1), date(2026, 3, 31))
        >>> period.days
        90
    """

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        """Validate period dates."""
        if self.end_date < self.start_date:
            raise ValueError(
                f"End date ({self.end_date}) cannot be before start date ({self.start_date})"
            )

    @classmethod
    def from_strings(cls, start: str, end: str, fmt: str = "%Y-%m-%d") -> "Period":
        """Create Period from string dates.

        Args:
            start: Start date string.
            end: End date string.
            fmt: Date format string (default: YYYY-MM-DD).

        Returns:
            Period instance.
        """
        from datetime import datetime

        start_date = datetime.strptime(start, fmt).date()
        end_date = datetime.strptime(end, fmt).date()
        return cls(start_date=start_date, end_date=end_date)

    @property
    def days(self) -> int:
        """Calculate number of days in the period (inclusive).

        Returns:
            Number of days.
        """
        return (self.end_date - self.start_date).days + 1

    @property
    def months(self) -> int:
        """Calculate approximate number of months.

        Returns:
            Number of months (rounded).
        """
        return max(1, round(self.days / 30))

    @property
    def quarter(self) -> str:
        """Get the quarter designation (e.g., Q1 2026).

        Returns:
            Quarter string.
        """
        quarter_num = (self.start_date.month - 1) // 3 + 1
        return f"Q{quarter_num} {self.start_date.year}"

    def contains(self, dt: date) -> bool:
        """Check if a date is within the period.

        Args:
            dt: Date to check.

        Returns:
            True if date is within period.
        """
        return self.start_date <= dt <= self.end_date

    def overlaps(self, other: "Period") -> bool:
        """Check if this period overlaps with another.

        Args:
            other: Another Period.

        Returns:
            True if periods overlap.
        """
        return self.start_date <= other.end_date and self.end_date >= other.start_date

    def format_start(self, fmt: str = "%Y-%m-%d") -> str:
        """Format start date as string.

        Args:
            fmt: Date format string.

        Returns:
            Formatted start date.
        """
        return self.start_date.strftime(fmt)

    def format_end(self, fmt: str = "%Y-%m-%d") -> str:
        """Format end date as string.

        Args:
            fmt: Date format string.

        Returns:
            Formatted end date.
        """
        return self.end_date.strftime(fmt)

    def __str__(self) -> str:
        """Format as readable string."""
        return f"{self.start_date} to {self.end_date}"

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Period({self.start_date}, {self.end_date})"
