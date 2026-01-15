"""CSV parser service for quotation generation."""

import csv
import io
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, BinaryIO, Optional
from uuid import UUID

if TYPE_CHECKING:
    from app.quotation_generator.services.boond_enrichment import (
        BoondEnrichmentService,
        EnrichedQuotationData,
    )

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
from app.quotation_generator.services.pricing_grid import PricingGridService

logger = logging.getLogger(__name__)


# Expected CSV columns mapping (actual column names from CSV -> internal field names)
COLUMN_MAPPING = {
    # Resource info
    "resource_id": ["ressource_id", "resource_id", "id_resource", "id_ressource"],
    "resource_first_name": ["Prénom", "Prenom", "prenom", "first_name", "prénom", "PRÉNOM", "PRENOM", "firstName", "firstname", "FirstName"],
    "resource_last_name": ["Nom", "nom", "last_name", "NOM", "lastName", "lastname", "LastName"],
    "resource_name": ["ressource_name", "resource_name", "nom_resource", "nom_ressource", "consultant"],
    "resource_trigramme": ["ressource_trigramme", "trigramme", "resource_trigramme", "code"],
    # BoondManager relationships
    "opportunity_id": ["opportunity_id", "id_opportunite", "ao", "affaire"],
    "company_id": ["company_id", "id_societe", "id_company"],
    "company_name": ["company_name", "nom_societe", "societe", "client"],
    "company_detail_id": ["company_detail_id", "id_detail_facturation", "detail_id"],
    "contact_id": ["contact_id", "id_contact"],
    "contact_name": ["contact_name", "nom_contact", "contact"],
    # Quotation date (date du devis)
    "quotation_date": ["date", "date_devis", "quotation_date"],
    # Period - using po_start_date and po_end_date from actual CSV
    "start_date": ["po_start_date", "start_date", "date_debut", "debut", "date_start"],
    "end_date": ["po_end_date", "end_date", "date_fin", "fin", "date_end"],
    "period_name": ["Periode", "periode", "period", "période"],
    # Pricing - amount_ht_unit is TJM, total_uo is quantity
    "tjm": ["amount_ht_unit", "tjm", "taux_journalier", "daily_rate", "tarif"],
    "quantity": ["total_uo", "quantity", "quantite", "nb_jours", "jours", "days"],
    "tax_rate": ["tax_rate", "taux_tva", "tva"],
    "turnover_ht": ["turnover_ht", "ca_ht"],
    "total_amount_ht": ["total_amount_ht", "montant_total_ht"],
    # Thales-specific
    "sow_reference": ["sow_reference", "ref_sow", "sow", "reference_sow"],
    "object_of_need": ["object_of_need", "objet_besoin", "besoin", "object"],
    "need_title": ["need_title", "titre_besoin", "title_need", "titre_du_besoin"],
    "eacq_number": ["eacq_number", "eacq", "numero_eacq"],
    "c22_domain": ["c22_domain", "C22_domain", "domaine_c22", "domaine"],
    "c22_activity": ["c22_activity", "C22_activity", "activite_c22", "activite"],
    "complexity": ["complexity", "complexite", "niveau"],
    "region": ["region", "région", "zone", "localisation", "activity_country"],
    "max_price": ["max_price", "prix_max", "gfa_max", "prix_plafond"],
    "in_situ_ratio": ["in_situ_ratio", "ratio_site", "taux_presentiel"],
    "subcontracting": ["subcontracting", "sous_traitance"],
    "tier2_supplier": ["tier2_supplier", "fournisseur_tier2"],
    "tier3_supplier": ["tier3_supplier", "fournisseur_tier3"],
    "start_project": ["initial_first_starting_date", "start_project", "debut_projet", "date_debut_projet"],
    "comments": ["additional_comments", "comments", "commentaires", "notes", "remarques"],
    # Additional fields from actual CSV (optional)
    "title": ["Title", "title", "titre"],
    "description": ["description"],
    "renewal": ["renewal", "renouvellement"],
    "state": ["state", "etat", "statut"],
}

# Required columns for SIMPLIFIED format (auto-enriched via BoondManager)
# Only requires: name, period, pricing, Thales-specific fields
REQUIRED_COLUMNS_SIMPLIFIED = [
    "resource_first_name",
    "resource_last_name",
    "start_date",
    "end_date",
    "tjm",
    "quantity",
    "c22_domain",
    "c22_activity",
    "complexity",
]

# Required columns for FULL format (all IDs provided in CSV)
REQUIRED_COLUMNS_FULL = [
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
    "c22_domain",
    "c22_activity",
    "complexity",
]


class CSVParserService:
    """Service for parsing CSV files into QuotationBatch entities.

    This service handles:
    - Semicolon (;) and comma (,) delimiters auto-detection
    - Column name mapping (French/English)
    - Data type conversion
    - Validation of required fields
    - Auto-fill of max_price from pricing grid (for 124-Data domain)
    - Auto-enrichment from BoondManager for simplified CSV format
    - Creation of domain entities

    Two CSV formats supported:
    1. SIMPLIFIED: Only Prénom, Nom + pricing + Thales fields
       - BoondManager IDs auto-fetched via API
    2. FULL: All IDs provided in CSV (legacy format)
    """

    def __init__(self, enrichment_service: Optional["BoondEnrichmentService"] = None) -> None:
        """Initialize the CSV parser service.

        Args:
            enrichment_service: Optional service for auto-enriching from BoondManager.
        """
        self._column_map: dict[str, str] = {}
        self._pricing_grid = PricingGridService()
        self._enrichment_service = enrichment_service
        self._is_simplified_format = False
        self._enrichment_cache: dict[str, "EnrichedQuotationData"] = {}

    def _detect_format(self) -> bool:
        """Detect if CSV is in simplified format.

        Returns:
            True if simplified format (no resource_id column), False otherwise.
        """
        has_resource_id = "resource_id" in self._column_map
        has_first_name = "resource_first_name" in self._column_map
        has_last_name = "resource_last_name" in self._column_map

        # Simplified format: has first/last name but no resource_id
        if has_first_name and has_last_name and not has_resource_id:
            return True

        return False

    async def parse_async(self, file_content: bytes, user_id: UUID) -> QuotationBatch:
        """Parse CSV content into a QuotationBatch (async version with enrichment).

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

            # Detect delimiter (semicolon or comma)
            delimiter = self._detect_delimiter(text_content)
            logger.info(f"Detected CSV delimiter: '{delimiter}'")

            # Parse CSV
            reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)

            if not reader.fieldnames:
                raise CSVParsingError("CSV file is empty or has no headers")

            # Build column mapping
            self._build_column_mapping(reader.fieldnames)

            # Detect format (simplified vs full)
            self._is_simplified_format = self._detect_format()
            logger.info(f"CSV format: {'SIMPLIFIED' if self._is_simplified_format else 'FULL'}")

            # Check required columns based on format
            self._validate_required_columns()

            # Create batch
            batch = QuotationBatch(user_id=user_id)

            # Parse rows
            rows = list(reader)  # Need to iterate twice for async enrichment
            for row_index, row in enumerate(rows):
                # Skip empty rows (like total rows at the end)
                if self._is_empty_row(row):
                    continue

                try:
                    quotation = await self._parse_row_async(row, row_index)
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

    def parse(self, file_content: bytes, user_id: UUID) -> QuotationBatch:
        """Parse CSV content into a QuotationBatch (sync version, full format only).

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

            # Detect delimiter (semicolon or comma)
            delimiter = self._detect_delimiter(text_content)
            logger.info(f"Detected CSV delimiter: '{delimiter}'")

            # Parse CSV
            reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)

            if not reader.fieldnames:
                raise CSVParsingError("CSV file is empty or has no headers")

            # Build column mapping
            self._build_column_mapping(reader.fieldnames)

            # Detect format
            self._is_simplified_format = self._detect_format()

            if self._is_simplified_format and not self._enrichment_service:
                raise CSVParsingError(
                    "Format CSV simplifié détecté mais le service d'enrichissement n'est pas disponible. "
                    "Utilisez le format complet ou réessayez."
                )

            # Check required columns
            self._validate_required_columns()

            # Create batch
            batch = QuotationBatch(user_id=user_id)

            # Parse rows
            for row_index, row in enumerate(reader):
                # Skip empty rows (like total rows at the end)
                if self._is_empty_row(row):
                    continue

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

    def _detect_delimiter(self, content: str) -> str:
        """Detect CSV delimiter by analyzing the first line.

        Args:
            content: CSV content as string.

        Returns:
            Delimiter character (';' or ',')
        """
        first_line = content.split('\n')[0] if '\n' in content else content
        semicolon_count = first_line.count(';')
        comma_count = first_line.count(',')

        # Use semicolon if it appears more often in the header
        return ';' if semicolon_count > comma_count else ','

    def _is_empty_row(self, row: dict) -> bool:
        """Check if a row is empty or is a total/summary row.

        Args:
            row: CSV row dictionary.

        Returns:
            True if row should be skipped.
        """
        # For simplified format, check first_name/last_name
        if self._is_simplified_format:
            first_name_col = self._column_map.get("resource_first_name")
            last_name_col = self._column_map.get("resource_last_name")
            if first_name_col and not row.get(first_name_col, "").strip():
                return True
            if last_name_col and not row.get(last_name_col, "").strip():
                return True
        else:
            # For full format, check resource_id
            resource_id_col = self._column_map.get("resource_id")
            if resource_id_col and not row.get(resource_id_col, "").strip():
                return True

        # Check if quantity is 0 or empty - likely a total row
        quantity_col = self._column_map.get("quantity")
        if quantity_col:
            qty_str = row.get(quantity_col, "").strip()
            if not qty_str:
                return True
            # Parse quantity and skip if 0
            try:
                qty_normalized = qty_str.replace(" ", "").replace(",", ".")
                if "." in qty_normalized:
                    qty_normalized = qty_normalized.split(".")[0]
                if int(qty_normalized) == 0:
                    logger.debug("Skipping row with quantity=0")
                    return True
            except (ValueError, TypeError):
                pass  # Let the parser handle invalid quantity

        return False

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

        Uses REQUIRED_COLUMNS_SIMPLIFIED or REQUIRED_COLUMNS_FULL based on format.

        Raises:
            MissingColumnsError: If required columns are missing.
        """
        # Select required columns based on format
        required_columns = (
            REQUIRED_COLUMNS_SIMPLIFIED
            if self._is_simplified_format
            else REQUIRED_COLUMNS_FULL
        )

        missing = []
        for required in required_columns:
            if required not in self._column_map:
                # Get human-readable column names
                possible = COLUMN_MAPPING.get(required, [required])
                missing.append(f"{required} ({', '.join(possible)})")

        if missing:
            raise MissingColumnsError(missing)

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

        # Parse quotation_date (date du devis) - optional, defaults to start_date
        quotation_date_str = self._get_value(row, "quotation_date")
        quotation_date: Optional[date] = None
        if quotation_date_str:
            quotation_date = self._parse_date(quotation_date_str, "quotation_date")

        # Parse start_project - optional, defaults to start_date
        start_project_str = self._get_value(row, "start_project")
        if start_project_str:
            start_project = self._parse_date(start_project_str, "start_project")
        else:
            start_project = start_date

        # Get period name from CSV (human-readable, e.g., "Janvier 2026")
        period_name = self._get_value(row, "period_name") or ""

        # Parse money values
        tjm = self._parse_decimal(self._get_value(row, "tjm"), "tjm")

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
        c22_domain = self._require_value(row, "c22_domain")
        c22_activity = self._require_value(row, "c22_activity")
        complexity = self._require_value(row, "complexity")

        # Optional fields
        sow_reference = self._get_value(row, "sow_reference") or ""
        object_of_need = self._get_value(row, "object_of_need") or ""
        # need_title: in sync mode, only from CSV (no enrichment available)
        need_title = self._get_value(row, "need_title") or ""
        region = self._get_value(row, "region")  # Optional, defaults to IDF in pricing grid
        comments = self._get_value(row, "comments")
        title = self._get_value(row, "title")
        description = self._get_value(row, "description")

        # Additional Thales fields with defaults
        eacq_number = self._get_value(row, "eacq_number") or "mail"
        renewal_str = self._get_value(row, "renewal")
        is_renewal = self._parse_bool(renewal_str, default=True)
        in_situ_ratio = self._get_value(row, "in_situ_ratio") or "50%"
        subcontracting_str = self._get_value(row, "subcontracting")
        subcontracting = self._parse_bool(subcontracting_str, default=False)
        tier2_supplier = self._get_value(row, "tier2_supplier") or ""
        tier3_supplier = self._get_value(row, "tier3_supplier") or ""

        # Parse max_price - auto-fill if not provided and domain is 124-Data
        max_price_str = self._get_value(row, "max_price")
        max_price: Decimal
        max_price_source = "csv"

        if max_price_str:
            # User provided max_price in CSV
            max_price = self._parse_decimal(max_price_str, "max_price")
        else:
            # Try to auto-fill from pricing grid
            auto_price = self._pricing_grid.get_max_gfa(
                c22_domain=c22_domain,
                c22_activity=c22_activity,
                complexity=complexity,
                region=region,
            )
            if auto_price:
                max_price = auto_price
                max_price_source = "grille"
                logger.info(
                    f"Row {row_index + 2}: Auto-filled max_price={max_price} "
                    f"for domain={c22_domain}, activity={c22_activity}, complexity={complexity}"
                )
            else:
                # Domain not supported - max_price is required
                if self._pricing_grid.is_domain_supported(c22_domain):
                    # Domain is supported but activity not found
                    raise ValueError(
                        f"Activité '{c22_activity}' non trouvée dans la grille tarifaire 124-Data. "
                        f"Veuillez spécifier max_price manuellement."
                    )
                else:
                    # Domain not supported at all
                    raise ValueError(
                        f"max_price requis pour le domaine '{c22_domain}'. "
                        f"L'auto-complétion n'est disponible que pour le domaine 124-Data."
                    )

        # Build description for line item
        line_description = title or description or f"Prestation de conseil - {resource_name}"

        # Create line item
        line = QuotationLine(
            description=line_description,
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
            period_name=period_name,
            quotation_date=quotation_date,
            line=line,
            sow_reference=sow_reference,
            object_of_need=object_of_need,
            need_title=need_title,
            c22_domain=c22_domain,
            c22_activity=c22_activity,
            complexity=complexity,
            max_price=Money(amount=max_price),
            start_project=start_project,
            comments=comments,
            eacq_number=eacq_number,
            is_renewal=is_renewal,
            in_situ_ratio=in_situ_ratio,
            subcontracting=subcontracting,
            tier2_supplier=tier2_supplier,
            tier3_supplier=tier3_supplier,
            row_index=row_index,
        )

    async def _parse_row_async(self, row: dict, row_index: int) -> Quotation:
        """Parse a single CSV row into a Quotation (async version with enrichment).

        For simplified format, enriches data from BoondManager.

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

        # Parse quotation_date (date du devis) - optional, defaults to start_date
        quotation_date_str = self._get_value(row, "quotation_date")
        quotation_date: Optional[date] = None
        if quotation_date_str:
            quotation_date = self._parse_date(quotation_date_str, "quotation_date")

        # Parse start_project - optional, defaults to start_date
        start_project_str = self._get_value(row, "start_project")
        if start_project_str:
            start_project = self._parse_date(start_project_str, "start_project")
        else:
            start_project = start_date

        # Get period name from CSV (human-readable, e.g., "Janvier 2026")
        period_name = self._get_value(row, "period_name") or ""

        # Parse money values
        tjm = self._parse_decimal(self._get_value(row, "tjm"), "tjm")

        # Parse quantity
        quantity = self._parse_int(self._get_value(row, "quantity"), "quantity")

        # Handle enrichment for simplified format
        if self._is_simplified_format:
            first_name = self._require_value(row, "resource_first_name")
            last_name = self._require_value(row, "resource_last_name")

            # Check cache first
            cache_key = f"{first_name.lower()}_{last_name.lower()}"
            if cache_key not in self._enrichment_cache:
                # Fetch from BoondManager
                if not self._enrichment_service:
                    raise ValueError("Service d'enrichissement non disponible")

                enriched = await self._enrichment_service.enrich_quotation_data(
                    first_name, last_name
                )
                if not enriched:
                    raise ValueError(
                        f"Ressource '{first_name} {last_name}' non trouvée dans BoondManager "
                        f"ou pas de projet Thales actif"
                    )
                self._enrichment_cache[cache_key] = enriched

            enriched = self._enrichment_cache[cache_key]

            # Use enriched data
            resource_id = enriched.resource_id
            resource_name = enriched.resource_name
            resource_trigramme = enriched.resource_trigramme
            opportunity_id = enriched.opportunity_id
            opportunity_title = enriched.opportunity_title
            company_id = enriched.company_id
            company_name = enriched.company_name
            company_detail_id = enriched.company_detail_id
            contact_id = enriched.contact_id
            contact_name = enriched.contact_name
        else:
            # Full format - get from CSV
            resource_id = self._require_value(row, "resource_id")
            resource_name = self._require_value(row, "resource_name")
            resource_trigramme = self._require_value(row, "resource_trigramme").upper()
            opportunity_id = self._require_value(row, "opportunity_id")
            opportunity_title = ""  # Not available in full format, must be in CSV
            company_id = self._require_value(row, "company_id")
            company_name = self._require_value(row, "company_name")
            company_detail_id = self._get_value(row, "company_detail_id") or company_id
            contact_id = self._require_value(row, "contact_id")
            contact_name = self._require_value(row, "contact_name")

        # Get Thales-specific fields (always from CSV)
        c22_domain = self._require_value(row, "c22_domain")
        c22_activity = self._require_value(row, "c22_activity")
        complexity = self._require_value(row, "complexity")

        # Optional fields
        sow_reference = self._get_value(row, "sow_reference") or ""
        object_of_need = self._get_value(row, "object_of_need") or ""
        # need_title: use CSV value if provided, otherwise use opportunity title from enrichment
        need_title = self._get_value(row, "need_title") or opportunity_title or ""
        region = self._get_value(row, "region")
        comments = self._get_value(row, "comments")
        title = self._get_value(row, "title")
        description = self._get_value(row, "description")

        # Additional Thales fields with defaults
        eacq_number = self._get_value(row, "eacq_number") or "mail"
        renewal_str = self._get_value(row, "renewal")
        is_renewal = self._parse_bool(renewal_str, default=True)
        in_situ_ratio = self._get_value(row, "in_situ_ratio") or "50%"
        subcontracting_str = self._get_value(row, "subcontracting")
        subcontracting = self._parse_bool(subcontracting_str, default=False)
        tier2_supplier = self._get_value(row, "tier2_supplier") or ""
        tier3_supplier = self._get_value(row, "tier3_supplier") or ""

        # Parse max_price - auto-fill if not provided and domain is 124-Data
        max_price_str = self._get_value(row, "max_price")
        max_price: Decimal
        max_price_source = "csv"

        if max_price_str:
            max_price = self._parse_decimal(max_price_str, "max_price")
        else:
            auto_price = self._pricing_grid.get_max_gfa(
                c22_domain=c22_domain,
                c22_activity=c22_activity,
                complexity=complexity,
                region=region,
            )
            if auto_price:
                max_price = auto_price
                max_price_source = "grille"
                logger.info(
                    f"Row {row_index + 2}: Auto-filled max_price={max_price} "
                    f"for domain={c22_domain}, activity={c22_activity}, complexity={complexity}"
                )
            else:
                if self._pricing_grid.is_domain_supported(c22_domain):
                    raise ValueError(
                        f"Activité '{c22_activity}' non trouvée dans la grille tarifaire 124-Data. "
                        f"Veuillez spécifier max_price manuellement."
                    )
                else:
                    raise ValueError(
                        f"max_price requis pour le domaine '{c22_domain}'. "
                        f"L'auto-complétion n'est disponible que pour le domaine 124-Data."
                    )

        # Build description for line item
        line_description = title or description or f"Prestation de conseil - {resource_name}"

        # Create line item
        line = QuotationLine(
            description=line_description,
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
            period_name=period_name,
            quotation_date=quotation_date,
            line=line,
            sow_reference=sow_reference,
            object_of_need=object_of_need,
            need_title=need_title,
            c22_domain=c22_domain,
            c22_activity=c22_activity,
            complexity=complexity,
            max_price=Money(amount=max_price),
            start_project=start_project,
            comments=comments,
            eacq_number=eacq_number,
            is_renewal=is_renewal,
            in_situ_ratio=in_situ_ratio,
            subcontracting=subcontracting,
            tier2_supplier=tier2_supplier,
            tier3_supplier=tier3_supplier,
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

        Handles formats like:
        - "550" (simple)
        - "1 130" (with space as thousand separator)
        - "1 070,00" (with comma as decimal separator)
        - "1,130.00" (with comma as thousand separator)

        Args:
            value: Decimal string.
            field_name: Field name for error messages.

        Returns:
            Parsed decimal.

        Raises:
            ValueError: If format is invalid.
        """
        if not value:
            raise ValueError(f"Missing required field: {field_name}")

        # Normalize: remove spaces, handle European/French format
        normalized = value.replace(" ", "").replace("€", "")

        # Handle French format: "1 070,00" -> "1070.00"
        # If comma is present and appears to be decimal separator
        if "," in normalized and "." not in normalized:
            # Comma is decimal separator
            normalized = normalized.replace(",", ".")
        elif "," in normalized and "." in normalized:
            # Both present - comma is thousand separator
            normalized = normalized.replace(",", "")

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

        # Remove spaces and handle decimal part if present
        normalized = value.replace(" ", "").replace(",", ".")
        if "." in normalized:
            normalized = normalized.split(".")[0]

        try:
            return int(normalized)
        except ValueError:
            raise ValueError(f"Invalid integer format for {field_name}: {value}")

    def _parse_bool(self, value: Optional[str], default: bool = False) -> bool:
        """Parse boolean from string.

        Recognizes: yes/no, oui/non, true/false, 1/0

        Args:
            value: Boolean string.
            default: Default value if string is empty/None.

        Returns:
            Parsed boolean.
        """
        if not value:
            return default

        value_lower = value.lower().strip()
        if value_lower in ("yes", "oui", "true", "1", "y", "o"):
            return True
        if value_lower in ("no", "non", "false", "0", "n"):
            return False

        return default

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
            sow_reference=self._get_value(row, "sow_reference") or "",
            object_of_need=self._get_value(row, "object_of_need") or "",
            c22_domain=self._get_value(row, "c22_domain") or "Unknown",
            c22_activity=self._get_value(row, "c22_activity") or "Unknown",
            complexity=self._get_value(row, "complexity") or "Unknown",
            max_price=Money(amount=Decimal("0")),
            start_project=today,
            row_index=row_index,
            validation_errors=[f"CSV parsing error: {error_message}"],
        )

        return quotation
