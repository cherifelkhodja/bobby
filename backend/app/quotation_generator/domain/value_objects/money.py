"""Money value object for handling monetary amounts."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Money:
    """Immutable value object representing a monetary amount.

    Attributes:
        amount: The monetary amount as a Decimal.
        currency: Currency code (default: EUR).

    Example:
        >>> price = Money(Decimal("850.00"))
        >>> total = price * 63
        >>> total.amount
        Decimal('53550.00')
    """

    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self) -> None:
        """Validate and normalize the amount."""
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        # Round to 2 decimal places
        rounded = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", rounded)

    @classmethod
    def from_float(cls, value: float, currency: str = "EUR") -> "Money":
        """Create Money from a float value.

        Args:
            value: Float amount.
            currency: Currency code.

        Returns:
            Money instance.
        """
        return cls(amount=Decimal(str(value)), currency=currency)

    @classmethod
    def zero(cls, currency: str = "EUR") -> "Money":
        """Create a zero Money instance.

        Args:
            currency: Currency code.

        Returns:
            Money with amount 0.
        """
        return cls(amount=Decimal("0"), currency=currency)

    def __add__(self, other: "Money") -> "Money":
        """Add two Money instances."""
        if not isinstance(other, Money):
            raise TypeError(f"Cannot add Money and {type(other)}")
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract two Money instances."""
        if not isinstance(other, Money):
            raise TypeError(f"Cannot subtract Money and {type(other)}")
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, factor: int | float | Decimal) -> "Money":
        """Multiply Money by a factor."""
        if isinstance(factor, (int, float)):
            factor = Decimal(str(factor))
        return Money(amount=self.amount * factor, currency=self.currency)

    def __rmul__(self, factor: int | float | Decimal) -> "Money":
        """Right multiply Money by a factor."""
        return self.__mul__(factor)

    def with_vat(self, vat_rate: Decimal = Decimal("0.20")) -> "Money":
        """Calculate amount including VAT.

        Args:
            vat_rate: VAT rate as decimal (default: 0.20 for 20%).

        Returns:
            Money including VAT.
        """
        return Money(
            amount=self.amount * (Decimal("1") + vat_rate),
            currency=self.currency,
        )

    def vat_amount(self, vat_rate: Decimal = Decimal("0.20")) -> "Money":
        """Calculate VAT amount.

        Args:
            vat_rate: VAT rate as decimal (default: 0.20 for 20%).

        Returns:
            VAT amount as Money.
        """
        return Money(
            amount=self.amount * vat_rate,
            currency=self.currency,
        )

    def to_float(self) -> float:
        """Convert to float for JSON serialization."""
        return float(self.amount)

    def __str__(self) -> str:
        """Format as string with currency."""
        return f"{self.amount:.2f} {self.currency}"

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Money({self.amount}, '{self.currency}')"
