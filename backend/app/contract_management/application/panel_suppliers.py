"""Sélection des fournisseurs du panel pour une société émettrice.

Le panel, ce n'est pas l'annuaire des tiers connus de Bobby : c'est la liste
des fournisseurs avec qui une société du groupe a un contrat cadre — signé, ou
en cours de signature. Un bon de commande ne peut se rattacher qu'à l'un
d'eux, et le cadre lie un fournisseur à **une** société émettrice : celui signé
avec Gemini ne rend pas le fournisseur disponible pour Craftmania.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.third_party.domain.entities.third_party import supplier_label

# Dossiers signés : ils autorisent l'envoi d'un bon de commande en signature.
SIGNED_FRAMEWORK_STATUSES = frozenset(
    {
        ContractRequestStatus.SIGNED.value,
        ContractRequestStatus.ACTIVE.value,
        ContractRequestStatus.ARCHIVED.value,
    }
)

# Dossiers qui ne mènent nulle part : ils ne font pas entrer dans le panel.
CLOSED_FRAMEWORK_STATUSES = frozenset(
    {
        ContractRequestStatus.CANCELLED.value,
        ContractRequestStatus.REDIRECTED_PAYFIT.value,
    }
)


@dataclass(frozen=True)
class PanelSupplier:
    """Un fournisseur du panel, vu depuis le contrat cadre qui l'y fait entrer."""

    third_party_id: UUID
    company_name: str | None
    third_party_type: str | None
    contract_request_id: UUID
    framework_reference: str
    framework_status: str
    framework_company_id: UUID | None
    signatory_first_name: str | None = None
    signatory_last_name: str | None = None
    contact_email: str | None = None

    @property
    def framework_signed(self) -> bool:
        """Le cadre est-il signé ? Sinon le bon de commande se prépare, sans s'envoyer."""
        return self.framework_status in SIGNED_FRAMEWORK_STATUSES

    @property
    def label(self) -> str:
        """Libellé de la liste : raison sociale, à défaut signataire ou contact."""
        return supplier_label(
            company_name=self.company_name,
            signatory_first_name=self.signatory_first_name,
            signatory_last_name=self.signatory_last_name,
            contact_email=self.contact_email,
        )


def is_usable_framework(status: str) -> bool:
    """Un dossier annulé ou redirigé Payfit ne fait pas entrer dans le panel."""
    return status not in CLOSED_FRAMEWORK_STATUSES


def select_panel_suppliers(
    candidates: Iterable[PanelSupplier], company_id: UUID | None
) -> list[PanelSupplier]:
    """Un fournisseur par ligne, avec le meilleur cadre pour la société émettrice.

    Ordre de préférence : cadre signé avec cette société, cadre signé sans
    société (dossiers antérieurs au multi-sociétés), puis les mêmes en cours de
    contractualisation. Un cadre signé avec une **autre** société du groupe
    n'ouvre rien : le fournisseur n'apparaît pas.

    Sans société émettrice — un bon de commande dont l'émetteur reste à
    choisir — aucun cadre n'est écarté : tous les fournisseurs du panel du
    groupe sont proposés.
    """
    best: dict[UUID, tuple[tuple[int, int], PanelSupplier]] = {}
    for candidate in candidates:
        if not is_usable_framework(candidate.framework_status):
            continue
        if company_id is not None and candidate.framework_company_id not in (company_id, None):
            continue
        rank = (
            0 if candidate.framework_signed else 1,
            0 if candidate.framework_company_id == company_id else 1,
        )
        current = best.get(candidate.third_party_id)
        if current is None or rank < current[0]:
            best[candidate.third_party_id] = (rank, candidate)

    return sorted(
        (candidate for _, candidate in best.values()),
        key=lambda s: (s.label.lower(), s.framework_reference),
    )
