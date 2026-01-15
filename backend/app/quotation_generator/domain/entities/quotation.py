"""Quotation entity representing a complete quotation."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from app.quotation_generator.domain.entities.quotation_line import QuotationLine
from app.quotation_generator.domain.value_objects import Money, Period, QuotationStatus


# Fixed legal text for Thales quotations
THALES_LEGALS = """Les frais de déplacement se réfèreront à la politique de voyage Thales (tout déplacement hors IDF fera l'objet de frais annexes)
La facturation se fera au réel consommé des unités d'œuvre, mensuel, sur la base d'un document type Procès-Verbal D'Acceptation, à remplir chaque mois.
Ce devis se réfère aux Conditions Générales d'Achats et aux exigences de sécurité Thales."""


@dataclass
class Quotation:
    """A complete quotation with all metadata and line items.

    This entity contains all data needed to:
    1. Create the quotation in BoondManager
    2. Fill the Thales PSTF template

    Attributes:
        resource_id: BoondManager resource ID.
        resource_name: Full name of the resource.
        resource_trigramme: 3-letter code (e.g., DAM).
        opportunity_id: BoondManager opportunity ID.
        company_id: BoondManager company ID.
        company_name: Company name.
        company_detail_id: Billing detail ID.
        contact_id: BoondManager contact ID.
        contact_name: Contact name.
        period: Service period (start/end dates).
        line: Quotation line item.
        sow_reference: SOW reference for Thales.
        object_of_need: Object of the need.
        c22_domain: C22 domain.
        c22_activity: C22 activity.
        complexity: Complexity level.
        max_price: Maximum GFA price.
        start_project: Initial project start date.
        comments: Optional comments.
    """

    # Resource info
    resource_id: str
    resource_name: str
    resource_trigramme: str

    # BoondManager relationships
    opportunity_id: str
    company_id: str
    company_name: str
    company_detail_id: str
    contact_id: str
    contact_name: str

    # Period and pricing
    period: Period
    line: QuotationLine

    # Thales-specific fields
    sow_reference: str
    object_of_need: str
    c22_domain: str
    c22_activity: str
    complexity: str
    max_price: Money
    start_project: date
    comments: Optional[str] = None

    # Internal state
    id: UUID = field(default_factory=uuid4)
    row_index: int = 0
    status: QuotationStatus = QuotationStatus.PENDING
    boond_quotation_id: Optional[str] = None
    boond_reference: Optional[str] = None
    error_message: Optional[str] = None
    validation_errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if quotation has no validation errors.

        Returns:
            True if valid.
        """
        return len(self.validation_errors) == 0

    @property
    def total_ht(self) -> Money:
        """Get total HT from line.

        Returns:
            Total amount excluding tax.
        """
        return self.line.total_ht

    @property
    def total_ttc(self) -> Money:
        """Get total TTC from line.

        Returns:
            Total amount including tax.
        """
        return self.line.total_ttc

    @property
    def tjm(self) -> Money:
        """Get daily rate (TJM).

        Returns:
            Unit price from line.
        """
        return self.line.unit_price_ht

    @property
    def quantity(self) -> int:
        """Get quantity (number of days).

        Returns:
            Quantity from line.
        """
        return self.line.quantity

    def validate(self) -> list[str]:
        """Run all validations and return errors.

        Returns:
            List of validation error messages.
        """
        errors = []

        # Validate trigramme format
        if len(self.resource_trigramme) != 3:
            errors.append(f"Trigramme must be 3 characters, got '{self.resource_trigramme}'")
        elif not self.resource_trigramme.isupper():
            errors.append(f"Trigramme must be uppercase, got '{self.resource_trigramme}'")

        # Validate period
        if self.period.start_date >= self.period.end_date:
            errors.append(f"Start date must be before end date")

        # Validate pricing
        if self.line.unit_price_ht.amount <= 0:
            errors.append("TJM must be positive")
        if self.line.quantity <= 0:
            errors.append("Quantity must be positive")

        # Validate max price
        if self.max_price.amount <= 0:
            errors.append("Max price must be positive")

        # Validate required string fields
        required_strings = [
            ("resource_id", self.resource_id),
            ("resource_name", self.resource_name),
            ("opportunity_id", self.opportunity_id),
            ("company_id", self.company_id),
            ("contact_id", self.contact_id),
            ("sow_reference", self.sow_reference),
            ("object_of_need", self.object_of_need),
            ("c22_domain", self.c22_domain),
            ("c22_activity", self.c22_activity),
            ("complexity", self.complexity),
        ]
        for field_name, value in required_strings:
            if not value or not value.strip():
                errors.append(f"'{field_name}' is required")

        self.validation_errors = errors
        return errors

    def to_boond_payload(self, number: str) -> dict:
        """Convert to BoondManager API payload format.

        Args:
            number: Quotation number/title.

        Returns:
            Dictionary in BoondManager API format.
        """
        return {
            "data": {
                "type": "quotation",
                "attributes": {
                    "date": date.today().isoformat(),
                    "state": 0,  # Draft
                    "currency": 0,  # EUR
                    "exchangeRate": 1,
                    "currencyAgency": 0,
                    "exchangeRateAgency": 1,
                    "turnoverInvoicedExcludingTax": self.total_ht.to_float(),
                    "turnoverInvoicedIncludingTax": self.total_ttc.to_float(),
                    "number": number,
                    "language": "fr",
                    "paymentTerm": 52,
                    "legals": THALES_LEGALS,
                    "informationComments": "",
                    "discountRate": 0,
                    "startDate": self.period.format_start(),
                    "endDate": self.period.format_end(),
                    "schedules": [],
                    "quotationRecords": [self.line.to_boond_record()],
                    "showCompanyRegistrationNumberOnPDF": False,
                    "showCompanyVATNumberOnPDF": False,
                    "showCompanyNumberOnPDF": False,
                    "showCommentsOnPDF": False,
                    "showFooterOnPDF": True,
                    "showOpportunityReferenceOnPDF": True,
                },
                "relationships": {
                    "mainManager": {"data": {"id": "1", "type": "resource"}},
                    "opportunity": {
                        "data": {
                            "id": str(self.opportunity_id).replace("AO", ""),
                            "type": "opportunity",
                        }
                    },
                    "company": {
                        "data": {"id": str(self.company_id), "type": "company"}
                    },
                    "contact": {
                        "data": {"id": str(self.contact_id), "type": "contact"}
                    },
                    "billingDetail": {
                        "data": {"id": str(self.company_detail_id), "type": "detail"}
                    },
                },
            }
        }

    def to_template_context(self, boond_reference: Optional[str] = None) -> dict:
        """Generate context for Thales template filling.

        Args:
            boond_reference: Reference generated by BoondManager.

        Returns:
            Dictionary of template variables.
        """
        return {
            "thales_stakeholder": self.contact_name,
            "procurement_buyer": "M Chérif GUESSOUM",
            "sow_reference": self.sow_reference,
            "object_of_need": self.object_of_need,
            "eacq_number": "mail",
            "reference": boond_reference or self.boond_reference or "",
            "sales_representative": "M Cherif EL KHODJA\n+33 7 57 81 73 83\ncherif.elkhodja@geminiconsulting.fr",
            "renewal": "YES",
            "initial_first_starting_date": self.start_project.strftime("%Y-%m-%d"),
            "total_uo": str(self.quantity),
            "po_start_date": self.period.format_start(),
            "po_end_date": self.period.format_end(),
            "c22_domain": self.c22_domain,
            "c22_activity": self.c22_activity,
            "activity_country": "France (IDF)",
            "complexity_level": self.complexity,
            "gfa_max_price": f"{self.max_price.amount:.2f}",
            "in_situ_ratio": "50%",
            "subcontracting": "NO",
            "tier2_supplier": "",
            "tier3_supplier": "",
            "additional_comments": self.comments or "",
        }

    def mark_as_processing(self, step: QuotationStatus) -> None:
        """Update status to a processing step.

        Args:
            step: The current processing step.
        """
        self.status = step

    def mark_as_completed(self, boond_id: str, reference: str) -> None:
        """Mark quotation as successfully completed.

        Args:
            boond_id: BoondManager quotation ID.
            reference: BoondManager reference.
        """
        self.status = QuotationStatus.COMPLETED
        self.boond_quotation_id = boond_id
        self.boond_reference = reference
        self.error_message = None

    def mark_as_failed(self, error: str) -> None:
        """Mark quotation as failed.

        Args:
            error: Error message.
        """
        self.status = QuotationStatus.FAILED
        self.error_message = error

    def __str__(self) -> str:
        """Format as readable string."""
        return f"Quotation({self.resource_trigramme}: {self.total_ht})"
