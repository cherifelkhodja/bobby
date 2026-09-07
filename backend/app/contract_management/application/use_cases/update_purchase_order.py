"""Use case: Complete or correct a purchase order (mission data)."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog

from app.contract_management.application.purchase_order_framework import (
    attach_framework_contract,
)
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    InvalidPurchaseOrderDataError,
    PurchaseOrderNotEditableError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)

logger = structlog.get_logger()

# Champs dont la modification périme le document déjà généré : le bon de
# commande doit alors être régénéré avant d'être envoyé.
DOCUMENT_BEARING_FIELDS = frozenset(
    {
        "third_party_id",
        "company_id",
        "client_name",
        "mission_title",
        "mission_description",
        "mission_site_name",
        "mission_address",
        "mission_postal_code",
        "mission_city",
        "purchase_daily_rate",
        "days_sold",
        "free_days",
        "start_date",
        "end_date",
        "consultant_civility",
        "consultant_first_name",
        "consultant_last_name",
    }
)


@dataclass
class UpdatePurchaseOrderCommand:
    """Champs à mettre à jour. Seuls les champs présents sont appliqués.

    La présence de la clé, et non sa valeur, décide de l'application : passer
    `{"sale_daily_rate": None}` efface le TJM, alors que ne pas transmettre la
    clé le laisse intact.
    """

    purchase_order_id: UUID
    fields: dict[str, Any] = field(default_factory=dict)


class UpdatePurchaseOrderUseCase:
    """Complète un bon de commande : fournisseur, mission, conditions.

    C'est l'étape que fait l'ADV après la création — automatique par webhook ou
    manuelle. Le rattachement du fournisseur entraîne celui de son contrat
    cadre : le bon de commande sait dès lors sous quel cadre il vit, et si ce
    cadre est signé.
    """

    ALLOWED_FIELDS = frozenset(
        {
            "third_party_id",
            "company_id",
            "client_name",
            "mission_title",
            "mission_description",
            "mission_site_name",
            "mission_address",
            "mission_postal_code",
            "mission_city",
            "sale_daily_rate",
            "purchase_daily_rate",
            "days_sold",
            "free_days",
            "start_date",
            "end_date",
            "consultant_civility",
            "consultant_first_name",
            "consultant_last_name",
            "consultant_email",
            "consultant_phone",
            "boond_need_id",
            "commercial_email",
        }
    )

    def __init__(
        self,
        purchase_order_repository,
        contract_request_repository,
    ) -> None:
        self._po_repo = purchase_order_repository
        self._cr_repo = contract_request_repository

    async def execute(self, command: UpdatePurchaseOrderCommand) -> PurchaseOrder:
        """Execute the use case.

        Raises:
            PurchaseOrderNotFoundError: If the purchase order does not exist.
            PurchaseOrderNotEditableError: If it was already sent for signature.
            InvalidPurchaseOrderDataError: If the mission data is inconsistent.
        """
        po = await self._po_repo.get_by_id(command.purchase_order_id)
        if not po:
            raise PurchaseOrderNotFoundError(str(command.purchase_order_id))

        if not po.status.is_editable:
            raise PurchaseOrderNotEditableError(po.display_reference, po.status.display_name)

        unknown = set(command.fields) - self.ALLOWED_FIELDS
        if unknown:
            raise InvalidPurchaseOrderDataError(
                f"Champs non modifiables : {', '.join(sorted(unknown))}."
            )

        changed = self._apply(po, command.fields)

        # Le cadre dépend du couple fournisseur + société émettrice : changer
        # l'un ou l'autre peut rendre le rattachement actuel caduc.
        if changed & {"third_party_id", "company_id"}:
            await self._attach_framework_contract(po)

        # Le numéro définitif vit dans la séquence de la société émettrice :
        # changer de société le périme. Le suivant sera pris à la génération.
        if "company_id" in changed:
            po.release_reference()

        self._check_consistency(po)

        # Un document déjà généré ne reflète plus la mission : retour en
        # brouillon pour forcer la régénération avant l'envoi.
        if po.status == PurchaseOrderStatus.GENERATED and changed & DOCUMENT_BEARING_FIELDS:
            po.s3_key_draft = None
            po.transition_to(PurchaseOrderStatus.DRAFT)

        saved = await self._po_repo.save(po)
        logger.info(
            "purchase_order_updated",
            purchase_order_id=str(saved.id),
            reference=saved.display_reference,
            changed=sorted(changed),
            missing_fields=saved.missing_fields,
        )
        return saved

    def _apply(self, po: PurchaseOrder, fields: dict[str, Any]) -> set[str]:
        """Applique les champs transmis et retourne ceux réellement modifiés."""
        changed: set[str] = set()
        for name, value in fields.items():
            if getattr(po, name) != value:
                setattr(po, name, value)
                changed.add(name)
        return changed

    async def _attach_framework_contract(self, po: PurchaseOrder) -> None:
        """Rattache le bon de commande au dossier cadre de son fournisseur.

        La règle est partagée avec la génération du document, qui rattrape un
        cadre signé après la dernière modification de la mission.
        """
        await attach_framework_contract(po, self._cr_repo)

    def _check_consistency(self, po: PurchaseOrder) -> None:
        """Vérifie la cohérence des conditions saisies."""
        if po.days_sold is not None and po.days_sold <= Decimal("0"):
            raise InvalidPurchaseOrderDataError(
                "Le nombre de jours vendus doit être supérieur à zéro."
            )
        if po.free_days is not None and po.free_days < Decimal("0"):
            raise InvalidPurchaseOrderDataError("Les jours de gratuité ne peuvent être négatifs.")
        if po.days_sold is not None and po.free_days is not None and po.free_days > po.days_sold:
            raise InvalidPurchaseOrderDataError(
                "Les jours de gratuité ne peuvent pas dépasser les jours vendus."
            )
        for label, rate in (
            ("Le CJM", po.purchase_daily_rate),
            ("Le TJM", po.sale_daily_rate),
        ):
            if rate is not None and rate < Decimal("0"):
                raise InvalidPurchaseOrderDataError(f"{label} ne peut pas être négatif.")
        if (
            isinstance(po.start_date, date)
            and isinstance(po.end_date, date)
            and po.end_date < po.start_date
        ):
            raise InvalidPurchaseOrderDataError(
                "La date de fin ne peut pas précéder la date de début."
            )
