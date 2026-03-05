"""Third party type value object."""

from enum import Enum


class ThirdPartyType(str, Enum):
    """Type of third party (freelance, subcontractor, employee)."""

    FREELANCE = "freelance"
    SOUS_TRAITANT = "sous_traitant"
    SALARIE = "salarie"
    PORTAGE_SALARIAL = "portage_salarial"

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
        }
        return names[self]

    @property
    def requires_contract(self) -> bool:
        """Check if this type requires a contract in Bobby."""
        return self in (ThirdPartyType.FREELANCE, ThirdPartyType.SOUS_TRAITANT, ThirdPartyType.PORTAGE_SALARIAL)
