"""Quotation line entity representing a single line item."""

from dataclasses import dataclass, field
from decimal import Decimal

from app.quotation_generator.domain.value_objects import Money


@dataclass
class QuotationLine:
    """A single line item in a quotation.

    Represents one service line with description, quantity, and pricing.

    Attributes:
        description: Description of the service.
        quantity: Number of units (days).
        unit_price_ht: Unit price excluding tax.
        tax_rate: Tax rate as decimal (default: 0.20 for 20% VAT).

    Example:
        >>> line = QuotationLine(
        ...     description="Prestation Data Engineer Q1 2026",
        ...     quantity=63,
        ...     unit_price_ht=Money.from_float(850.00),
        ... )
        >>> line.total_ht.amount
        Decimal('53550.00')
    """

    description: str
    quantity: int
    unit_price_ht: Money
    tax_rate: Decimal = field(default_factory=lambda: Decimal("0.20"))

    def __post_init__(self) -> None:
        """Validate the line item."""
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {self.quantity}")
        if self.unit_price_ht.amount <= 0:
            raise ValueError(f"Unit price must be positive, got {self.unit_price_ht}")

    @property
    def total_ht(self) -> Money:
        """Calculate total excluding tax.

        Returns:
            Total amount HT.
        """
        return self.unit_price_ht * self.quantity

    @property
    def total_ttc(self) -> Money:
        """Calculate total including tax.

        Returns:
            Total amount TTC.
        """
        return self.total_ht.with_vat(self.tax_rate)

    @property
    def tax_amount(self) -> Money:
        """Calculate tax amount.

        Returns:
            Tax amount.
        """
        return self.total_ht.vat_amount(self.tax_rate)

    @property
    def tax_rate_percent(self) -> int:
        """Get tax rate as percentage.

        Returns:
            Tax rate as integer percentage (e.g., 20 for 20%).
        """
        return int(self.tax_rate * 100)

    def to_boond_record(self) -> dict:
        """Convert to BoondManager quotation record format.

        Returns:
            Dictionary in BoondManager API format.
        """
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unitPrice": self.unit_price_ht.to_float(),
            "unit": "day",
            "taxRate": self.tax_rate_percent,
        }

    def __str__(self) -> str:
        """Format as readable string."""
        return f"{self.description}: {self.quantity} x {self.unit_price_ht} = {self.total_ht}"
