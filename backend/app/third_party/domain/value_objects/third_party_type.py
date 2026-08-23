"""Third party type value object."""

from enum import Enum


class ThirdPartyType(str, Enum):
    """Type of third party (freelance, subcontractor, employee)."""

    FREELANCE = "freelance"
    SOUS_TRAITANT = "sous_traitant"
    SALARIE = "salarie"
    PORTAGE_SALARIAL = "portage_salarial"
    PORTAGE_COMMERCIAL = "portage_commercial"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable type name."""
        names = {
            ThirdPartyType.FREELANCE: "Freelance",
            ThirdPartyType.SOUS_TRAITANT: "Sous-traitant",
            ThirdPartyType.SALARIE: "Salarié",
            ThirdPartyType.PORTAGE_SALARIAL: "Portage salarial",
            ThirdPartyType.PORTAGE_COMMERCIAL: "Portage commercial",
        }
        return names[self]

    @property
    def is_external(self) -> bool:
        """Le consultant intervient-il sous contrat externe ?

        Détermine les chartes qui lui sont opposables (`consultant_scope`) :
        seul le salarié embauché directement est interne.
        """
        return self is not ThirdPartyType.SALARIE

    @property
    def requires_contract(self) -> bool:
        """Check if this type requires a contract in Bobby."""
        return self in (
            ThirdPartyType.FREELANCE,
            ThirdPartyType.SOUS_TRAITANT,
            ThirdPartyType.PORTAGE_SALARIAL,
            ThirdPartyType.PORTAGE_COMMERCIAL,
        )


# Types dont le consultant intervient sous contrat externe, sous forme de
# chaînes : les entités portent `third_party_type` en texte libre.
EXTERNAL_THIRD_PARTY_TYPES = frozenset(t.value for t in ThirdPartyType if t.is_external)
