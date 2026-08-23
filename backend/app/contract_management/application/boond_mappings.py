"""Correspondances entre les types de tiers de Bobby et les codes BoondManager.

Ces valeurs sont **configurées dans BoondManager** (Administration → Types des
ressources & candidats, types de contrats) : les changer côté CRM impose de les
changer ici. Elles sont regroupées pour qu'un type de tiers ajouté n'oblige pas
à retrouver trois tables dispersées.
"""

# `typeOf` du contrat Boond, par type de tiers.
CONTRACT_TYPE_BY_THIRD_PARTY_TYPE: dict[str, int] = {
    "sous_traitant": 2,
    "freelance": 3,
    "portage_salarial": 6,
    "portage_commercial": 7,
}

# Repli quand le type de tiers est inconnu : freelance, le cas le plus courant.
DEFAULT_CONTRACT_TYPE = 3

# `typeOf` de la ressource Boond, par type de tiers.
#   0 = Consultant Interne (interne facturable)
#   1 = Consultant Externe (externe facturable)
#  10 = Consultant Portage Commercial (externe facturable)
# Freelance, sous-traitance et portage salarial partagent le type externe ; seul
# le portage commercial a le sien.
RESOURCE_TYPE_BY_THIRD_PARTY_TYPE: dict[str, int] = {
    "salarie": 0,
    "freelance": 1,
    "sous_traitant": 1,
    "portage_salarial": 1,
    "portage_commercial": 10,
}

RESOURCE_TYPE_INTERNAL = 0
RESOURCE_TYPE_EXTERNAL = 1


def contract_type_of(third_party_type: str | None) -> int:
    """Type de contrat Boond correspondant au type de tiers."""
    return CONTRACT_TYPE_BY_THIRD_PARTY_TYPE.get(third_party_type or "", DEFAULT_CONTRACT_TYPE)


def resource_type_of(third_party_type: str | None) -> int:
    """Type de ressource Boond correspondant au type de tiers.

    Un type inconnu donne « Consultant Externe » : c'est le cas d'un dossier
    ouvert avant que le type ne soit renseigné, et il vaut mieux une ressource
    externe qu'un consultant compté comme interne.
    """
    return RESOURCE_TYPE_BY_THIRD_PARTY_TYPE.get(third_party_type or "", RESOURCE_TYPE_EXTERNAL)


def state_reason_type_of(third_party_type: str | None) -> int:
    """Motif du changement d'état de la ressource : interne ou externe.

    Distinct du type de ressource : le motif ne connaît que ces deux valeurs,
    quel que soit le détail du type.
    """
    return RESOURCE_TYPE_INTERNAL if third_party_type == "salarie" else RESOURCE_TYPE_EXTERNAL
