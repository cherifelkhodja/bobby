"""Pydantic schemas for the purchase order (bon de commande) API.

Note de confidentialité : `sale_daily_rate` et `estimated_margin` sont des
données internes. Elles circulent sur cette API, réservée aux rôles internes,
mais ne doivent jamais alimenter le document remis au fournisseur ni le
portail tiers.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PurchaseOrderCreate(BaseModel):
    """Créer un bon de commande depuis un positionnement Boond."""

    boond_positioning_id: int = Field(
        ..., gt=0, description="ID du positionnement Boond à l'origine de la mission"
    )


class PurchaseOrderUpdate(BaseModel):
    """Compléter ou corriger un bon de commande.

    Seuls les champs transmis sont appliqués : transmettre `null` efface la
    valeur, ne pas transmettre la clé la laisse intacte.
    """

    third_party_id: UUID | None = None
    company_id: UUID | None = None
    client_name: str | None = Field(None, max_length=255)
    mission_title: str | None = Field(None, max_length=500)
    mission_description: str | None = None
    mission_site_name: str | None = Field(None, max_length=255)
    mission_address: str | None = Field(None, max_length=500)
    mission_postal_code: str | None = Field(None, max_length=10)
    mission_city: str | None = Field(None, max_length=255)
    sale_daily_rate: Decimal | None = Field(None, description="TJM de vente client (interne)")
    purchase_daily_rate: Decimal | None = Field(None, description="CJM d'achat fournisseur")
    days_sold: Decimal | None = None
    free_days: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    consultant_civility: str | None = Field(None, max_length=10)
    consultant_first_name: str | None = Field(None, max_length=255)
    consultant_last_name: str | None = Field(None, max_length=255)
    consultant_email: str | None = Field(None, max_length=255)
    consultant_phone: str | None = Field(None, max_length=50)
    boond_need_id: int | None = None
    commercial_email: str | None = Field(None, max_length=255)


class PurchaseOrderAttachDelivery(BaseModel):
    """Rattacher à la main la prestation Boond d'une mission.

    Recours quand le report n'a pas su la retrouver alors que le CRM l'a bien
    créée : sans elle, l'achat fournisseur n'a rien à quoi pendre.
    """

    delivery_id: int = Field(gt=0, description="Identifiant de la prestation dans BoondManager")


class PurchaseOrderRenew(BaseModel):
    """Reconduire une mission par un nouveau bon de commande.

    Seules la période et les conditions qui changent sont transmises : le reste
    (consultant, fournisseur, mission, positionnement) est repris du bon de
    commande d'origine.
    """

    start_date: date
    end_date: date
    days_sold: Decimal | None = None
    free_days: Decimal | None = None
    purchase_daily_rate: Decimal | None = None
    sale_daily_rate: Decimal | None = None


class PurchaseOrderResponse(BaseModel):
    """Bon de commande, enrichi des données calculées et du contexte cadre."""

    id: UUID
    provisional_reference: str
    reference: str | None = None
    # Référence à afficher : définitive dès la génération, provisoire avant.
    display_reference: str
    status: str
    status_display: str
    is_editable: bool

    # Fournisseur et contrat cadre
    third_party_id: UUID | None = None
    third_party_name: str | None = None
    needs_third_party: bool = False
    contract_request_id: UUID | None = None
    framework_contract_reference: str | None = None
    framework_contract_status: str | None = None
    framework_contract_signed: bool = False
    can_send_for_signature: bool = False

    # Société émettrice : deux missions d'un même fournisseur peuvent relever
    # de deux sociétés du groupe, sous deux contrats cadres différents.
    company_id: UUID | None = None
    company_name: str | None = None

    # Consultant
    boond_consultant_id: int | None = None
    boond_consultant_type: str | None = None
    consultant_civility: str | None = None
    consultant_first_name: str | None = None
    consultant_last_name: str | None = None
    consultant_name: str | None = None
    consultant_email: str | None = None
    consultant_phone: str | None = None

    # Origine Boond
    boond_positioning_id: int | None = None
    boond_need_id: int | None = None
    boond_delivery_id: int | None = None

    # Mission
    client_name: str | None = None
    mission_title: str | None = None
    mission_description: str | None = None
    mission_site_name: str | None = None
    mission_address: str | None = None
    mission_postal_code: str | None = None
    mission_city: str | None = None

    # Conditions financières
    sale_daily_rate: float | None = None
    purchase_daily_rate: float | None = None
    days_sold: float | None = None
    free_days: float = 0
    billable_days: float = 0
    total_amount: float = 0
    estimated_margin: float | None = None
    start_date: date | None = None
    end_date: date | None = None

    # Documents et signature
    has_draft: bool = False
    has_signed_document: bool = False
    sent_for_signature_at: datetime | None = None
    signed_at: datetime | None = None

    # Synchronisation Boond
    boond_contract_id: int | None = None
    boond_purchase_order_id: int | None = None
    boond_sync_error: str | None = None

    parent_purchase_order_id: UUID | None = None
    commercial_email: str | None = None
    missing_fields: list[str] = []
    status_history: list[dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class PurchaseOrderListResponse(BaseModel):
    """Liste paginée de bons de commande."""

    items: list[PurchaseOrderResponse]
    total: int
    skip: int
    limit: int


class PanelSupplierResponse(BaseModel):
    """Un fournisseur du panel, proposé au rattachement d'un bon de commande."""

    third_party_id: UUID
    # Libellé prêt à afficher : raison sociale, à défaut signataire ou contact.
    label: str
    company_name: str | None = None
    third_party_type: str | None = None
    contract_request_id: UUID
    # Le cadre identifie le fournisseur bien mieux que son SIREN : c'est lui
    # qui autorise la mission, et il est propre à la société émettrice.
    framework_reference: str
    framework_status: str
    framework_signed: bool = False


class PanelSupplierListResponse(BaseModel):
    """Panel fournisseur d'une société émettrice."""

    items: list[PanelSupplierResponse]
    total: int


class BoondDeletionResponse(BaseModel):
    """Compte rendu d'une suppression dans BoondManager (outil de test)."""

    purchase_order: PurchaseOrderResponse
    # Une ligne par objet traité : ce qui a été supprimé, ce qui a résisté.
    report: list[str]
