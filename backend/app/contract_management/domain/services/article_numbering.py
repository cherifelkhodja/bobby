"""Dynamic article numbering for contract generation."""

from typing import Any


def compute_article_numbers(config: dict[str, Any]) -> dict[str, int]:
    """Compute article numbers dynamically based on active clauses.

    Contract articles are numbered sequentially, skipping articles
    for disabled clauses. This keeps numbering clean and correct
    regardless of which optional clauses are included.

    Args:
        config: Contract configuration with clause toggles.

    Returns:
        Dictionary mapping article keys to their numbers.
    """
    articles = []

    # Fixed articles
    articles.append("objet")
    articles.append("duree")
    articles.append("conditions_financieres")
    articles.append("modalites_facturation")
    articles.append("obligations_prestataire")

    # Conditional articles
    if config.get("include_confidentiality", True):
        articles.append("confidentialite")
    if config.get("include_non_compete", False):
        articles.append("non_concurrence")
    if config.get("include_intellectual_property", True):
        articles.append("propriete_intellectuelle")
    if config.get("include_liability", True):
        articles.append("responsabilite")

    # Fixed final articles
    articles.append("resiliation")
    articles.append("droit_applicable")

    return {key: idx + 1 for idx, key in enumerate(articles)}
