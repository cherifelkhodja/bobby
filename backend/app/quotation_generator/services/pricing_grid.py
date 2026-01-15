"""Pricing grid service for Thales quotations.

Provides max GFA (Gross Fixed Amount) lookup based on:
- Activity code/name (e.g., "2-Data Architect" or "12-AI - AI/ML Engineer")
- Region (IDF or Région) - defaults to IDF if not specified
- Complexity level (Simple, Medium/Intermediate, Complex)
"""

from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Pricing grid data: short_activity_code -> {region -> {complexity -> price}}
# Format: "NUM-Activity Name" (matches C22_activity column from CSV)
PRICING_GRID: dict[str, dict[str, dict[str, Decimal]]] = {
    # DATA Domain (124-DATA)
    "1-Data Analyst": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "2-Data Architect": {
        "IDF": {"Simple": Decimal("690"), "Medium": Decimal("900"), "Complex": Decimal("1130")},
        "Région": {"Simple": Decimal("590"), "Medium": Decimal("770"), "Complex": Decimal("960")},
    },
    "3-Data developer - Mendix Low Code": {
        "IDF": {"Simple": Decimal("610"), "Medium": Decimal("800"), "Complex": Decimal("1000")},
        "Région": {"Simple": Decimal("520"), "Medium": Decimal("680"), "Complex": Decimal("850")},
    },
    "4-Data developer - UIPath (RPA)": {
        "IDF": {"Simple": Decimal("620"), "Medium": Decimal("810"), "Complex": Decimal("1020")},
        "Région": {"Simple": Decimal("530"), "Medium": Decimal("690"), "Complex": Decimal("870")},
    },
    "5-Data Visualisation Developer - Power BI": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "6-Data Modeller": {
        "IDF": {"Simple": Decimal("640"), "Medium": Decimal("840"), "Complex": Decimal("1050")},
        "Région": {"Simple": Decimal("540"), "Medium": Decimal("710"), "Complex": Decimal("890")},
    },
    "7-Data Test and QA Engineer - test automation": {
        "IDF": {"Simple": Decimal("580"), "Medium": Decimal("760"), "Complex": Decimal("950")},
        "Région": {"Simple": Decimal("490"), "Medium": Decimal("650"), "Complex": Decimal("810")},
    },
    "8-Data Engineer - IBM Data Stage (ETL)": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "9-Data Engineer  - Talend (ETL)": {  # Note: double space to match CSV
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "9-Data Engineer - Talend (ETL)": {  # Also single space version
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "10-AI - AI Infrastructure Engineer": {
        "IDF": {"Simple": Decimal("685"), "Medium": Decimal("900"), "Complex": Decimal("1130")},
        "Région": {"Simple": Decimal("580"), "Medium": Decimal("770"), "Complex": Decimal("960")},
    },
    "11-AI - LLM OpsEngineer": {
        "IDF": {"Simple": Decimal("680"), "Medium": Decimal("890"), "Complex": Decimal("1120")},
        "Région": {"Simple": Decimal("580"), "Medium": Decimal("760"), "Complex": Decimal("950")},
    },
    "12-AI - AI/ML Engineer": {
        "IDF": {"Simple": Decimal("680"), "Medium": Decimal("890"), "Complex": Decimal("1120")},
        "Région": {"Simple": Decimal("580"), "Medium": Decimal("760"), "Complex": Decimal("950")},
    },
    "13-AI - Prompt Engineer": {
        "IDF": {"Simple": Decimal("620"), "Medium": Decimal("810"), "Complex": Decimal("1020")},
        "Région": {"Simple": Decimal("530"), "Medium": Decimal("690"), "Complex": Decimal("870")},
    },
    "14-AI - Security Analyst": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "15-AI - MLOps Engineer": {
        "IDF": {"Simple": Decimal("680"), "Medium": Decimal("890"), "Complex": Decimal("1120")},
        "Région": {"Simple": Decimal("580"), "Medium": Decimal("760"), "Complex": Decimal("950")},
    },
    "16-AI - AI Regulation & Compliance Manager": {
        "IDF": {"Simple": Decimal("695"), "Medium": Decimal("910"), "Complex": Decimal("1140")},
        "Région": {"Simple": Decimal("590"), "Medium": Decimal("770"), "Complex": Decimal("970")},
    },
}

# Domains that support auto-fill (case-insensitive)
SUPPORTED_DOMAINS = {"124-data", "124-Data", "124-DATA"}

# Build lookup indexes for flexible matching
_ACTIVITY_NAME_INDEX: dict[str, str] = {}
_ACTIVITY_NUMBER_INDEX: dict[str, str] = {}

for activity_code in PRICING_GRID.keys():
    activity_lower = activity_code.lower().strip()
    _ACTIVITY_NAME_INDEX[activity_lower] = activity_code

    # Also index by just the number prefix (e.g., "2" -> "2-Data Architect")
    if "-" in activity_code:
        number = activity_code.split("-")[0]
        _ACTIVITY_NUMBER_INDEX[number] = activity_code

# Complexity level aliases
COMPLEXITY_ALIASES: dict[str, str] = {
    "simple": "Simple",
    "junior": "Simple",
    "medium": "Medium",
    "intermediate": "Medium",  # Added for CSV compatibility
    "confirmé": "Medium",
    "confirme": "Medium",
    "senior": "Medium",
    "complex": "Complex",
    "complexe": "Complex",
    "expert": "Complex",
}

# Region aliases
REGION_ALIASES: dict[str, str] = {
    "idf": "IDF",
    "ile-de-france": "IDF",
    "ile de france": "IDF",
    "paris": "IDF",
    "france idf": "IDF",
    "france (idf)": "IDF",
    "région": "Région",
    "region": "Région",
    "régions": "Région",
    "regions": "Région",
    "province": "Région",
    "france région": "Région",
    "france régions": "Région",
    "france (régions)": "Région",
    "france (regions)": "Région",
}

# Default region when not specified
DEFAULT_REGION = "IDF"


class PricingGridService:
    """Service for looking up max GFA prices from the Thales pricing grid."""

    def get_max_gfa(
        self,
        c22_domain: str,
        c22_activity: str,
        complexity: str,
        region: Optional[str] = None,
    ) -> Optional[Decimal]:
        """Look up the max GFA for a given activity, region, and complexity.

        Args:
            c22_domain: Domain code (e.g., "124-Data"). Only 124-Data is supported.
            c22_activity: Activity code (e.g., "2-Data Architect", "12-AI - AI/ML Engineer")
            complexity: Complexity level (e.g., "Simple", "Medium", "Intermediate", "Complex")
            region: Region (e.g., "IDF", "Région"). Defaults to IDF if not specified.

        Returns:
            Max GFA as Decimal, or None if not found (domain not supported or activity not in grid).
        """
        # Check if domain is supported
        if c22_domain and c22_domain.strip().lower() not in {d.lower() for d in SUPPORTED_DOMAINS}:
            logger.debug(f"Domain {c22_domain} not supported for auto-fill")
            return None

        # Normalize inputs
        normalized_region = self._normalize_region(region) if region else DEFAULT_REGION
        normalized_complexity = self._normalize_complexity(complexity)

        if not normalized_complexity:
            logger.warning(f"Could not normalize complexity={complexity}")
            return None

        # Find the activity in the grid
        full_code = self._find_activity(c22_activity)
        if not full_code:
            logger.warning(f"Activity not found in pricing grid: {c22_activity}")
            return None

        # Look up the price
        try:
            price = PRICING_GRID[full_code][normalized_region][normalized_complexity]
            logger.info(
                f"Found max GFA: {price} for activity={c22_activity}, "
                f"region={normalized_region}, complexity={normalized_complexity}"
            )
            return price
        except KeyError:
            logger.warning(
                f"Price not found for activity={full_code}, "
                f"region={normalized_region}, complexity={normalized_complexity}"
            )
            return None

    def is_domain_supported(self, c22_domain: str) -> bool:
        """Check if a domain is supported for auto-fill."""
        if not c22_domain:
            return False
        return c22_domain.strip().lower() in {d.lower() for d in SUPPORTED_DOMAINS}

    def _normalize_region(self, region: str) -> Optional[str]:
        """Normalize region name to IDF or Région."""
        if not region:
            return DEFAULT_REGION
        normalized = REGION_ALIASES.get(region.lower().strip())
        if normalized:
            return normalized
        # Direct match
        if region in ("IDF", "Région"):
            return region
        return DEFAULT_REGION  # Default to IDF if unknown

    def _normalize_complexity(self, complexity: str) -> Optional[str]:
        """Normalize complexity level to Simple, Medium, or Complex."""
        if not complexity:
            return None
        normalized = COMPLEXITY_ALIASES.get(complexity.lower().strip())
        if normalized:
            return normalized
        # Direct match
        if complexity in ("Simple", "Medium", "Complex"):
            return complexity
        return None

    def _find_activity(self, activity: str) -> Optional[str]:
        """Find the activity code from input.

        Supports:
        - Exact match: "2-Data Architect"
        - Case-insensitive: "2-data architect"
        - Number only: "2" (returns first match)
        """
        if not activity:
            return None

        activity_stripped = activity.strip()
        activity_lower = activity_stripped.lower()

        # Exact match
        if activity_stripped in PRICING_GRID:
            return activity_stripped

        # Case-insensitive match
        if activity_lower in _ACTIVITY_NAME_INDEX:
            return _ACTIVITY_NAME_INDEX[activity_lower]

        # Match by number prefix only
        if activity_stripped in _ACTIVITY_NUMBER_INDEX:
            return _ACTIVITY_NUMBER_INDEX[activity_stripped]

        # Partial match (activity contains the key or key contains activity)
        for name, full_code in _ACTIVITY_NAME_INDEX.items():
            if activity_lower in name or name in activity_lower:
                return full_code

        return None

    def get_available_activities(self) -> list[str]:
        """Get list of all available activity codes."""
        return list(PRICING_GRID.keys())

    def get_supported_domains(self) -> list[str]:
        """Get list of supported domains for auto-fill."""
        return list(SUPPORTED_DOMAINS)

    def get_regions(self) -> list[str]:
        """Get list of valid regions."""
        return ["IDF", "Région"]

    def get_complexity_levels(self) -> list[str]:
        """Get list of valid complexity levels."""
        return ["Simple", "Medium", "Complex"]
