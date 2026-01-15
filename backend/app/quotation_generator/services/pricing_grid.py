"""Pricing grid service for Thales quotations.

Provides max GFA (Gross Fixed Amount) lookup based on:
- Activity code/name
- Region (IDF or Région)
- Complexity level (Simple, Medium, Complex)
"""

from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Pricing grid data: activity_code -> {region -> {complexity -> price}}
# Format: "CODE-DOMAIN-NUM-Activity Name"
PRICING_GRID: dict[str, dict[str, dict[str, Decimal]]] = {
    # DATA Domain
    "124-DATA-1-Data Analyst": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "124-DATA-2-Data Architect": {
        "IDF": {"Simple": Decimal("690"), "Medium": Decimal("900"), "Complex": Decimal("1130")},
        "Région": {"Simple": Decimal("590"), "Medium": Decimal("770"), "Complex": Decimal("960")},
    },
    "124-DATA-3-Data developer - Mendix Low Code": {
        "IDF": {"Simple": Decimal("610"), "Medium": Decimal("800"), "Complex": Decimal("1000")},
        "Région": {"Simple": Decimal("520"), "Medium": Decimal("680"), "Complex": Decimal("850")},
    },
    "124-DATA-4-Data developer - UIPath (RPA)": {
        "IDF": {"Simple": Decimal("620"), "Medium": Decimal("810"), "Complex": Decimal("1020")},
        "Région": {"Simple": Decimal("530"), "Medium": Decimal("690"), "Complex": Decimal("870")},
    },
    "124-DATA-5-Data Visualisation Developer - Power BI": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "124-DATA-6-Data Modeller": {
        "IDF": {"Simple": Decimal("640"), "Medium": Decimal("840"), "Complex": Decimal("1050")},
        "Région": {"Simple": Decimal("540"), "Medium": Decimal("710"), "Complex": Decimal("890")},
    },
    "124-DATA-7-Data Test and QA Engineer - test automation": {
        "IDF": {"Simple": Decimal("580"), "Medium": Decimal("760"), "Complex": Decimal("950")},
        "Région": {"Simple": Decimal("490"), "Medium": Decimal("650"), "Complex": Decimal("810")},
    },
    "124-DATA-8-Data Engineer - IBM Data Stage (ETL)": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "124-DATA-9-Data Engineer - Talend (ETL)": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "124-DATA-10-AI - AI Infrastructure Engineer": {
        "IDF": {"Simple": Decimal("685"), "Medium": Decimal("900"), "Complex": Decimal("1130")},
        "Région": {"Simple": Decimal("580"), "Medium": Decimal("770"), "Complex": Decimal("960")},
    },
    "124-DATA-11-AI - LLM OpsEngineer": {
        "IDF": {"Simple": Decimal("680"), "Medium": Decimal("890"), "Complex": Decimal("1120")},
        "Région": {"Simple": Decimal("580"), "Medium": Decimal("760"), "Complex": Decimal("950")},
    },
    "124-DATA-12-AI - AI/ML Engineer": {
        "IDF": {"Simple": Decimal("680"), "Medium": Decimal("890"), "Complex": Decimal("1120")},
        "Région": {"Simple": Decimal("580"), "Medium": Decimal("760"), "Complex": Decimal("950")},
    },
    "124-DATA-13-AI - Prompt Engineer": {
        "IDF": {"Simple": Decimal("620"), "Medium": Decimal("810"), "Complex": Decimal("1020")},
        "Région": {"Simple": Decimal("530"), "Medium": Decimal("690"), "Complex": Decimal("870")},
    },
    "124-DATA-14-AI - Security Analyst": {
        "IDF": {"Simple": Decimal("650"), "Medium": Decimal("850"), "Complex": Decimal("1070")},
        "Région": {"Simple": Decimal("550"), "Medium": Decimal("720"), "Complex": Decimal("910")},
    },
    "124-DATA-15-AI - MLOps Engineer": {
        "IDF": {"Simple": Decimal("680"), "Medium": Decimal("890"), "Complex": Decimal("1120")},
        "Région": {"Simple": Decimal("580"), "Medium": Decimal("760"), "Complex": Decimal("950")},
    },
    "124-DATA-16-AI - AI Regulation & Compliance Manager": {
        "IDF": {"Simple": Decimal("695"), "Medium": Decimal("910"), "Complex": Decimal("1140")},
        "Région": {"Simple": Decimal("590"), "Medium": Decimal("770"), "Complex": Decimal("970")},
    },
}

# Build lookup indexes for flexible matching
_ACTIVITY_NAME_INDEX: dict[str, str] = {}
_ACTIVITY_CODE_INDEX: dict[str, str] = {}

for full_code in PRICING_GRID.keys():
    # Index by activity name (last part after the number)
    parts = full_code.split("-", 3)
    if len(parts) >= 4:
        activity_name = parts[3].strip().lower()
        _ACTIVITY_NAME_INDEX[activity_name] = full_code
        # Also index by code prefix (e.g., "124-DATA-1")
        code_prefix = f"{parts[0]}-{parts[1]}-{parts[2]}"
        _ACTIVITY_CODE_INDEX[code_prefix.lower()] = full_code

# Complexity level aliases
COMPLEXITY_ALIASES: dict[str, str] = {
    "simple": "Simple",
    "junior": "Simple",
    "medium": "Medium",
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


class PricingGridService:
    """Service for looking up max GFA prices from the Thales pricing grid."""

    def get_max_gfa(
        self,
        activity: str,
        region: str,
        complexity: str,
    ) -> Optional[Decimal]:
        """Look up the max GFA for a given activity, region, and complexity.

        Args:
            activity: Activity code or name (e.g., "124-DATA-1-Data Analyst" or "Data Analyst")
            region: Region (e.g., "IDF", "Région", "Paris", "Province")
            complexity: Complexity level (e.g., "Simple", "Medium", "Complex", "Junior", "Senior", "Expert")

        Returns:
            Max GFA as Decimal, or None if not found.
        """
        # Normalize inputs
        normalized_region = self._normalize_region(region)
        normalized_complexity = self._normalize_complexity(complexity)

        if not normalized_region or not normalized_complexity:
            logger.warning(
                f"Could not normalize region={region} or complexity={complexity}"
            )
            return None

        # Find the activity in the grid
        full_code = self._find_activity(activity)
        if not full_code:
            logger.warning(f"Activity not found in pricing grid: {activity}")
            return None

        # Look up the price
        try:
            price = PRICING_GRID[full_code][normalized_region][normalized_complexity]
            logger.info(
                f"Found max GFA: {price} for activity={activity}, "
                f"region={normalized_region}, complexity={normalized_complexity}"
            )
            return price
        except KeyError:
            logger.warning(
                f"Price not found for activity={full_code}, "
                f"region={normalized_region}, complexity={normalized_complexity}"
            )
            return None

    def _normalize_region(self, region: str) -> Optional[str]:
        """Normalize region name to IDF or Région."""
        if not region:
            return None
        normalized = REGION_ALIASES.get(region.lower().strip())
        if normalized:
            return normalized
        # Direct match
        if region in ("IDF", "Région"):
            return region
        return None

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
        """Find the full activity code from a partial match."""
        if not activity:
            return None

        activity_lower = activity.lower().strip()

        # Exact match
        if activity in PRICING_GRID:
            return activity

        # Match by activity name
        if activity_lower in _ACTIVITY_NAME_INDEX:
            return _ACTIVITY_NAME_INDEX[activity_lower]

        # Match by code prefix
        if activity_lower in _ACTIVITY_CODE_INDEX:
            return _ACTIVITY_CODE_INDEX[activity_lower]

        # Partial match on activity name
        for name, full_code in _ACTIVITY_NAME_INDEX.items():
            if activity_lower in name or name in activity_lower:
                return full_code

        return None

    def get_available_activities(self) -> list[str]:
        """Get list of all available activity codes."""
        return list(PRICING_GRID.keys())

    def get_regions(self) -> list[str]:
        """Get list of valid regions."""
        return ["IDF", "Région"]

    def get_complexity_levels(self) -> list[str]:
        """Get list of valid complexity levels."""
        return ["Simple", "Medium", "Complex"]
