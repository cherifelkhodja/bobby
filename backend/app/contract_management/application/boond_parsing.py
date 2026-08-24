"""Conversions des valeurs brutes renvoyées par BoondManager.

L'API renvoie indifféremment des chaînes vides, des nombres sous forme de
texte ou des dates ISO tronquées. Ces helpers ramènent tout cela aux types
attendus par les entités, en retournant ``None`` plutôt qu'en levant :
une donnée Boond illisible ne doit jamais faire échouer la création d'un
dossier, elle sera complétée à la main.
"""

from datetime import date
from decimal import Decimal, InvalidOperation


def parse_date(raw: object) -> date | None:
    """Convertit une date Boond (ISO, éventuellement horodatée) en `date`."""
    if isinstance(raw, date):
        return raw
    if raw and isinstance(raw, str):
        try:
            return date.fromisoformat(raw[:10])
        except (ValueError, TypeError):
            return None
    return None


def to_decimal(raw: object) -> Decimal | None:
    """Convertit un montant Boond en `Decimal`.

    Une valeur nulle ou vide donne ``None`` ; un zéro explicite est conservé,
    car « pas de tarif » et « tarif à zéro » ne sont pas la même chose.
    """
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None


def first_present(*values: object) -> object | None:
    """Première valeur renseignée parmi celles proposées.

    ``None`` et la chaîne vide valent « absent » ; un zéro explicite, non :
    zéro jour de gratuité est une donnée, pas un trou à combler par la source
    suivante.
    """
    for value in values:
        if value is not None and value != "":
            return value
    return None
