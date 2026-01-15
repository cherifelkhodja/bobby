"""CSV parser service for quotation generation."""

import csv
import io
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import BinaryIO, Optional
from uuid import UUID

from app.quotation_generator.domain.entities import (
    Quotation,
    QuotationBatch,
    QuotationLine,
)
from app.quotation_generator.domain.exceptions import (
    CSVParsingError,
    MissingColumnsError,
)
from app.quotation_generator.domain.value_objects import Money, Period

logger = logging.getLogger(__name__)


# Expected CSV columns mapping (French -> English field names)
COLUMN_MAPPING = {
    # Resource info
    "resource_id": ["resource_id", "id_resource", "id_ressource"],
    "resource_name": ["resource_name", "nom_resource", "nom_ressource", "consultant"],
    "resource_trigramme": ["trigramme", "resource_trigramme", "code"],
    # BoondManager relationships
    "opportunity_id": ["opportunity_id", "id_opportunite", "ao", "affaire"],
    "company_id": ["company_id", "id_societe", "id_company"],
    "company_name": ["company_name", "nom_societe", "societe", "client"],
    "company_detail_id": ["company_detail_id", "id_detail_facturation", "detail_id"],
    "contact_id": ["contact_id", "id_contact"],
    "contact_name": ["contact_name", "nom_contact", "contact"],
    # Period
    "start_date": ["start_date", "date_debut", "debut", "date_start"],
    "end_date": ["end_date", "date_fin", "fin", "date_end"],
    # Pricing
    "tjm": ["tjm", "taux_journalier", "daily_rate", "tarif"],
    "quantity": ["quantity", "quantite", "nb_jours", "jours", "days"],
    # Thales-specific
    "sow_reference": ["sow_reference", "ref_sow", "sow", "reference_sow"],
    "object_of_need": ["object_of_need", "objet_besoin", "besoin", "object"],
    "c22_domain": ["c22_domain", "domaine_c22", "domaine"],
    "c22_activity": ["c22_activity", "activite_c22", "activite"],
    "complexity": ["complexity", "complexite", "niveau"],
    "max_price": ["max_price", "prix_max", "gfa_max", "prix_plafond"],
    "start_project": ["start_project", "debut_projet", "date_debut_projet"],
    "comments": ["comments", "commentaires", "notes", "remarques"],
}

# Required columns (must be present)
REQUIRED_COLUMNS = [
    "resource_id",
    "resource_name",
    "resource_trigramme",
    "opportunity_id",
    "company_id",
    "company_name",
    "contact_id",
    "contact_name",
    "start_date",
    "end_date",
    "tjm",
    "quantity",
    "sow_reference",
    "object_of_need",
    "c22_domain",
    "c22_activity",
    "complexity",
    "max_price",
    "start_project",
]


class CSVParserService:
    """Service for parsing CSV files into QuotationBatch entities.

    This service handles:
    - Column name mapping (French/English)
    - Data type conversion
    - Validation of required fields
    - Creation of domain entities
    """

    def __init__(self) -> None:
        """Initialize the CSV parser service."""
        self._column_map: dict[str, str] = {}

    def parse(self, file_content: bytes, user_id: UUID) -> QuotationBatch:
        """Parse CSV content into a QuotationBatch.

        Args:
            file_content: Raw CSV file content as bytes.
            user_id: ID of the user creating the batch.

        Returns:
            QuotationBatch containing parsed quotations.

        Raises:
            CSVParsingError: If CSV cannot be parsed.
            MissingColumnsError: If required columns are missing.
        """
        try:
            # Detect encoding and decode
            text_content = self._decode_content(file_content)

            # Parse CSV
            reader = csv.DictReader(io.StringIO(text_content))

            if not reader.fieldnames:
                raise CSVParsingError("CSV file is empty or has no headers")

            # Build column mapping
            self._build_column_mapping(reader.fieldnames)

            # Check required columns
            self._validate_required_columns()

            # Create batch
            batch = QuotationBatch(user_id=user_id)

            # Parse rows
            for row_index, row in enumerate(reader):
                try:
                    quotation = self._parse_row(row, row_index)
                    batch.add_quotation(quotation)
                except Exception as e:
                    logger.warning(f"Error parsing row {row_index + 2}: {e}")
                    # Create quotation with error
                    error_quotation = self._create_error_quotation(
                        row, row_index, str(e)
                    )
                    batch.add_quotation(error_quotation)

            logger.info(f"Parsed {batch.total_count} quotations from CSV")
            return batch

        except (CSVParsingError, MissingColumnsError):
            raise
        except Exception as e:
            logger.error(f"CSV parsing failed: {e}")
            raise CSVParsingError(f"Failed to parse CSV: {str(e)}") from e

    def parse_file(self, file: BinaryIO, user_id: UUID) -> QuotationBatch:
        """Parse CSV file object into a QuotationBatch.

        Args:
            file: File-like object with CSV content.
            user_id: ID of the user creating the batch.

        Returns:
            QuotationBatch containing parsed quotations.
        """
        content = file.read()
        return self.parse(content, user_id)

    def _decode_content(self, content: bytes) -> str:
        """Decode CSV content trying multiple encodings.

        Args:
            content: Raw bytes content.

        Returns:
            Decoded string content.

        Raises:
            CSVParsingError: If decoding fails.
        """
        # Try common encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue

        raise CSVParsingError("Could not decode CSV file. Please use UTF-8 encoding.")

    def _build_column_mapping(self, fieldnames: list[str]) -> None:
        """Build mapping from CSV column names to field names.

        Args:
            fieldnames: List of column names from CSV header.
        """
        self._column_map = {}
        fieldnames_lower = {f.lower().strip(): f for f in fieldnames}

        for field_name, possible_names in COLUMN_MAPPING.items():
            for possible_name in possible_names:
                if possible_name.lower() in fieldnames_lower:
                    self._column_map[field_name] = fieldnames_lower[
                        possible_name.lower()
                    ]
                    break

        logger.debug(f"Column mapping: {self._column_map}")

    def _validate_required_columns(self) -> None:
        """Validate that all required columns are present.

        Raises:
            MissingColumnsError: If required columns are missing.
        """
        missing = []
        for required in REQUIRED_COLUMNS:
            if required not in self._column_map:
                # Get human-readable column names
                possible = COLUMN_MAPPING.get(required, [required])
                missing.append(f"{required} ({', '.join(possible)})")

        if missing:
            raise MissingColumnsError(
                f"Missing required columns: {', '.join(missing)}"
            )

    def _get_value(self, row: dict, field_name: str) -> Optional[str]:
        """Get value from row using column mapping.

        Args:
            row: CSV row dictionary.
            field_name: Internal field name.

        Returns:
            Value as string or None.
        """
        column_name = self._column_map.get(field_name)
        if column_name and column_name in row:
            value = row[column_name]
            if value and value.strip():
                return value.strip()
        return None

    def _parse_row(self, row: dict, row_index: int) -> Quotation:
        """Parse a single CSV row into a Quotation.

        Args:
            row: CSV row dictionary.
            row_index: Zero-based row index.

        Returns:
            Quotation entity.

        Raises:
            ValueError: If required field is missing or invalid.
        """
        # Parse dates
        start_date = self._parse_date(self._get_value(row, "start_date"), "start_date")
        end_date = self._parse_date(self._get_value(row, "end_date"), "end_date")
        start_project = self._parse_date(
            self._get_value(row, "start_project"), "start_project"
        )

        # Parse money values
        tjm = self._parse_decimal(self._get_value(row, "tjm"), "tjm")
        max_price = self._parse_decimal(self._get_value(row, "max_price"), "max_price")

        # Parse quantity
        quantity = self._parse_int(self._get_value(row, "quantity"), "quantity")

        # Get required strings
        resource_id = self._require_value(row, "resource_id")
        resource_name = self._require_value(row, "resource_name")
        resource_trigramme = self._require_value(row, "resource_trigramme").upper()
        opportunity_id = self._require_value(row, "opportunity_id")
        company_id = self._require_value(row, "company_id")
        company_name = self._require_value(row, "company_name")
        company_detail_id = self._get_value(row, "company_detail_id") or company_id
        contact_id = self._require_value(row, "contact_id")
        contact_name = self._require_value(row, "contact_name")
        sow_reference = self._require_value(row, "sow_reference")
        object_of_need = self._require_value(row, "object_of_need")
        c22_domain = self._require_value(row, "c22_domain")
        c22_activity = self._require_value(row, "c22_activity")
        complexity = self._require_value(row, "complexity")

        # Optional fields
        comments = self._get_value(row, "comments")

        # Create line item
        line = QuotationLine(
            description=f"Prestation de conseil - {resource_name}",
            quantity=quantity,
            unit_price_ht=Money(amount=tjm),
        )

        return Quotation(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_trigramme=resource_trigramme,
            opportunity_id=opportunity_id,
            company_id=company_id,
            company_name=company_name,
            company_detail_id=company_detail_id,
            contact_id=contact_id,
            contact_name=contact_name,
            period=Period(start_date=start_date, end_date=end_date),
            line=line,
            sow_reference=sow_reference,
            object_of_need=object_of_need,
            c22_domain=c22_domain,
            c22_activity=c22_activity,
            complexity=complexity,
            max_price=Money(amount=max_price),
            start_project=start_project,
            comments=comments,
            row_index=row_index,
        )

    def _require_value(self, row: dict, field_name: str) -> str:
        """Get required value or raise error.

        Args:
            row: CSV row dictionary.
            field_name: Field name.

        Returns:
            Non-empty string value.

        Raises:
            ValueError: If value is missing or empty.
        """
        value = self._get_value(row, field_name)
        if not value:
            raise ValueError(f"Missing required field: {field_name}")
        return value

    def _parse_date(self, value: Optional[str], field_name: str) -> date:
        """Parse date from string.

        Supports formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY

        Args:
            value: Date string.
            field_name: Field name for error messages.

        Returns:
            Parsed date.

        Raises:
            ValueError: If date format is invalid.
        """
        if not value:
            raise ValueError(f"Missing required date field: {field_name}")

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Invalid date format for {field_name}: {value}")

    def _parse_decimal(self, value: Optional[str], field_name: str) -> Decimal:
        """Parse decimal from string.

        Args:
            value: Decimal string (accepts comma or dot).
            field_name: Field name for error messages.

        Returns:
            Parsed decimal.

        Raises:
            ValueError: If format is invalid.
        """
        if not value:
            raise ValueError(f"Missing required field: {field_name}")

        # Normalize: remove spaces, replace comma with dot
        normalized = value.replace(" ", "").replace(",", ".").replace("€", "")

        try:
            return Decimal(normalized)
        except InvalidOperation:
            raise ValueError(f"Invalid number format for {field_name}: {value}")

    def _parse_int(self, value: Optional[str], field_name: str) -> int:
        """Parse integer from string.

        Args:
            value: Integer string.
            field_name: Field name for error messages.

        Returns:
            Parsed integer.

        Raises:
            ValueError: If format is invalid.
        """
        if not value:
            raise ValueError(f"Missing required field: {field_name}")

        # Remove decimal part if present
        normalized = value.replace(" ", "").replace(",", ".")
        if "." in normalized:
            normalized = normalized.split(".")[0]

        try:
            return int(normalized)
        except ValueError:
            raise ValueError(f"Invalid integer format for {field_name}: {value}")

    def _create_error_quotation(
        self, row: dict, row_index: int, error_message: str
    ) -> Quotation:
        """Create a quotation placeholder for rows with parsing errors.

        Args:
            row: Original CSV row.
            row_index: Row index.
            error_message: Error description.

        Returns:
            Quotation with validation errors set.
        """
        # Try to extract whatever we can
        today = date.today()

        quotation = Quotation(
            resource_id=self._get_value(row, "resource_id") or "UNKNOWN",
            resource_name=self._get_value(row, "resource_name") or "Unknown",
            resource_trigramme=self._get_value(row, "resource_trigramme") or "UNK",
            opportunity_id=self._get_value(row, "opportunity_id") or "UNKNOWN",
            company_id=self._get_value(row, "company_id") or "UNKNOWN",
            company_name=self._get_value(row, "company_name") or "Unknown",
            company_detail_id=self._get_value(row, "company_detail_id") or "UNKNOWN",
            contact_id=self._get_value(row, "contact_id") or "UNKNOWN",
            contact_name=self._get_value(row, "contact_name") or "Unknown",
            period=Period(start_date=today, end_date=today),
            line=QuotationLine(
                description="ERROR",
                quantity=0,
                unit_price_ht=Money(amount=Decimal("0")),
            ),
            sow_reference=self._get_value(row, "sow_reference") or "UNKNOWN",
            object_of_need=self._get_value(row, "object_of_need") or "Unknown",
            c22_domain=self._get_value(row, "c22_domain") or "Unknown",
            c22_activity=self._get_value(row, "c22_activity") or "Unknown",
            complexity=self._get_value(row, "complexity") or "Unknown",
            max_price=Money(amount=Decimal("0")),
            start_project=today,
            row_index=row_index,
            validation_errors=[f"CSV parsing error: {error_message}"],
        )

        return quotation
