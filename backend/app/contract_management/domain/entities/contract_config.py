"""Contract configuration entity."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass
class ContractConfig:
    """Configuration data for generating a contract document.

    Holds all the variables needed to fill the contract template.
    """

    # Mission details
    mission_description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    daily_rate: Decimal = Decimal("0")
    estimated_days: int | None = None

    # Payment
    payment_terms: str = "net_30"
    invoice_submission_method: str = "email"
    invoice_email: str = ""

    # Optional articles excluded for this contract (list of article_key strings)
    excluded_optional_article_keys: list[str] = field(default_factory=list)

    # Additional
    special_conditions: str = ""
    annexes: list[str] = field(default_factory=list)

    def to_template_context(self) -> dict[str, Any]:
        """Convert to a dictionary suitable for DOCX template rendering.

        Returns:
            Template context dictionary.
        """
        return {
            "mission_description": self.mission_description,
            "start_date": self.start_date.strftime("%d/%m/%Y") if self.start_date else "",
            "end_date": self.end_date.strftime("%d/%m/%Y") if self.end_date else "",
            "daily_rate": f"{self.daily_rate:,.2f}".replace(",", " "),
            "estimated_days": self.estimated_days or "",
            "payment_terms": self.payment_terms,
            "invoice_submission_method": self.invoice_submission_method,
            "invoice_email": self.invoice_email,
            "excluded_optional_article_keys": self.excluded_optional_article_keys,
            "special_conditions": self.special_conditions,
            "annexes": self.annexes,
        }
