"""Lecture des événements webhook BoondManager.

Boond poste un tableau d'événements de type ``webhookevent`` : l'entité
concernée est dans ``relationships.dependsOn`` et le changement d'état dans le
log inclus (``content.diff.state.new``). Le format « données directes » est
également accepté, c'est celui des rejeux manuels.
"""

from typing import Any

# Entités Boond dont on sait lire un changement d'état.
_SUPPORTED_ENTITIES = ("positioning",)


def parse_positioning_event(data: dict[str, Any]) -> tuple[int | None, int | None]:
    """Extrait (id du positionnement, nouvel état) d'un événement webhook.

    Retourne ``(None, None)`` quand l'événement ne concerne pas un
    positionnement ou n'est pas exploitable — l'appelant se contente alors de
    l'ignorer, un webhook ne devant jamais échouer côté Boond.
    """
    if data.get("type") == "webhookevent":
        depends_on = data.get("relationships", {}).get("dependsOn", {})
        if depends_on.get("type") not in _SUPPORTED_ENTITIES:
            return None, None

        positioning_id = _to_int(depends_on.get("id"))
        if positioning_id is None:
            return None, None

        for included in data.get("included", []):
            if included.get("type") != "log":
                continue
            state_diff = (
                included.get("attributes", {}).get("content", {}).get("diff", {}).get("state", {})
            )
            if "new" in state_diff:
                return positioning_id, state_diff["new"]

        return positioning_id, None

    # Repli : données de positionnement transmises directement (rejeu manuel).
    positioning_id = _to_int(data.get("id"))
    if positioning_id is None:
        return None, None
    return positioning_id, data.get("attributes", {}).get("state")


def iter_events(payload: dict[str, Any] | list) -> list[dict[str, Any]]:
    """Normalise le corps du webhook en une liste d'objets ``data``."""
    entries = payload if isinstance(payload, list) else [payload]
    return [entry.get("data", entry) for entry in entries if isinstance(entry, dict)]


def _to_int(raw: object) -> int | None:
    """Convertit un identifiant Boond en entier, sans lever."""
    try:
        value = int(str(raw))
    except (ValueError, TypeError):
        return None
    return value or None
