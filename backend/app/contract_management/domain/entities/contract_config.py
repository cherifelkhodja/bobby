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
    mission_location: str = ""
    start_date: date | None = None
    end_date: date | None = None
    daily_rate: Decimal = Decimal("0")
    estimated_days: int | None = None

    # Payment
    payment_terms: str = "net_30"
    invoice_submission_method: str = "email"
    invoice_email: str = ""

    # Contract clauses (toggles)
    include_confidentiality: bool = True
    include_non_compete: bool = False
    non_compete_duration_months: int = 0
    non_compete_geographic_scope: str = ""
    include_intellectual_property: bool = True
    include_liability: bool = True

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
            "mission_location": self.mission_location,
            "start_date": self.start_date.strftime("%d/%m/%Y") if self.start_date else "",
            "end_date": self.end_date.strftime("%d/%m/%Y") if self.end_date else "",
            "daily_rate": f"{self.daily_rate:,.2f}".replace(",", " "),
            "estimated_days": self.estimated_days or "",
            "payment_terms": self.payment_terms,
            "invoice_submission_method": self.invoice_submission_method,
            "invoice_email": self.invoice_email,
            "include_confidentiality": self.include_confidentiality,
            "include_non_compete": self.include_non_compete,
            "non_compete_duration_months": self.non_compete_duration_months,
            "non_compete_geographic_scope": self.non_compete_geographic_scope,
            "include_intellectual_property": self.include_intellectual_property,
            "include_liability": self.include_liability,
            "special_conditions": self.special_conditions,
            "annexes": self.annexes,
        }
