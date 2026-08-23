"""Pydantic schemas for contract management API."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class ContractRequestResponse(BaseModel):
    """Contract request response."""

    id: UUID
    provisional_reference: str
    reference: str | None = None
    display_reference: str
    trigger_type: str | None = None
    previous_contract_request_id: UUID | None = None
    boond_positioning_id: int | None = None
    boond_candidate_id: int | None = None
    boond_consultant_type: str | None = None
    boond_resource_id: int | None = None
    status: str
    status_display: str
    third_party_type: str | None = None
    daily_rate: float | None = None
    quantity_sold: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    client_name: str | None = None
    mission_title: str | None = None
    mission_description: str | None = None
    consultant_civility: str | None = None
    consultant_first_name: str | None = None
    consultant_last_name: str | None = None
    consultant_email: str | None = None
    consultant_phone: str | None = None
    mission_site_name: str | None = None
    mission_address: str | None = None
    mission_postal_code: str | None = None
    mission_city: str | None = None
    commercial_email: str | None = None
    commercial_name: str | None = None
    contractualization_contact_email: str | None = None
    third_party_id: UUID | None = None
    third_party_name: str | None = None
    portal_url: str | None = None
    compliance_override: bool
    compliance_override_reason: str | None = None
    documents_skipped: bool = False
    company_id: UUID | None = None
    company_name: str | None = None
    # Nombre de bons de commande rattachés : ce qui vit sous ce contrat cadre.
    purchase_orders_count: int = 0
    contract_config: dict | None = None
    status_history: list[dict] = []
    created_at: datetime
    updated_at: datetime


class ContractRequestListResponse(BaseModel):
    """Paginated list of contract requests."""

    items: list[ContractRequestResponse]
    total: int
    skip: int
    limit: int


class CommercialValidationRequest(BaseModel):
    """Request for commercial validation (simplified for contrat cadre).

    Only type tiers + contact email are required.
    Mission-specific fields (TJM, dates, address) belong to BDC.
    """

    third_party_type: str = Field(
        ..., pattern=r"^(freelance|sous_traitant|salarie|portage_salarial)$"
    )
    contact_email: EmailStr
    company_id: UUID | None = None
    consultant_civility: str | None = Field(None, max_length=10)
    consultant_first_name: str | None = Field(None, max_length=255)
    consultant_last_name: str | None = Field(None, max_length=255)
    consultant_email: str | None = Field(None, max_length=255)
    consultant_phone: str | None = Field(None, max_length=50)
    notify_third_party: bool = Field(
        True,
        description=(
            "Envoyer le lien de collecte au tiers. Décocher pour une saisie "
            "manuelle par l'ADV, sans solliciter le fournisseur."
        ),
    )
    skip_documents: bool = Field(
        False,
        description=(
            "Ignorer le dépôt des documents de vigilance (saisie en personne). "
            "La demande passe directement en revue de conformité avec une "
            "dérogation tracée. Nécessite notify_third_party=False."
        ),
    )

    @model_validator(mode="after")
    def _check_skip_documents(self) -> "CommercialValidationRequest":
        """Interdire de sauter la collecte tout en sollicitant le fournisseur.

        Sauter le dépôt n'a de sens qu'en saisie manuelle : envoyer un lien de
        collecte à un tiers dont les documents ne seront jamais attendus serait
        incohérent côté fournisseur.
        """
        if self.skip_documents and self.notify_third_party:
            raise ValueError(
                "Le dépôt des documents ne peut être ignoré qu'en saisie manuelle "
                "(notify_third_party=False)."
            )
        return self


class ManualContractRequestCreate(BaseModel):
    """Create a contract request from scratch (manual ADV entry, no Boond webhook).

    The ADV enters the Boond ID of the consultant and whether it is a candidate or
    a resource. The consultant identity is best-effort enriched from Boond. All
    other fields are optional and can also be filled later during commercial
    validation.
    """

    boond_consultant_id: int = Field(..., gt=0, description="ID Boond du consultant")
    consultant_type: str = Field(
        "candidate",
        pattern=r"^(candidate|resource)$",
        description="'candidate' (candidat Boond, converti à la signature) ou 'resource'",
    )
    company_id: UUID | None = None
    client_name: str | None = Field(None, max_length=255)
    mission_title: str | None = Field(None, max_length=255)
    consultant_civility: str | None = Field(None, max_length=10)
    consultant_first_name: str | None = Field(None, max_length=255)
    consultant_last_name: str | None = Field(None, max_length=255)
    consultant_email: str | None = Field(None, max_length=255)
    consultant_phone: str | None = Field(None, max_length=50)


class SupplierDossierCreate(BaseModel):
    """Ouvrir un dossier de contractualisation pour un fournisseur.

    Point d'entrée manuel du contrat cadre : aucun consultant, aucun
    positionnement. Le mode de collecte des documents est choisi ici, dès la
    création, et non plus lors d'une étape de validation séparée.
    """

    third_party_type: str = Field(
        ..., pattern=r"^(freelance|sous_traitant|salarie|portage_salarial)$"
    )
    contact_email: EmailStr = Field(..., description="Contact contractualisation du fournisseur")
    company_id: UUID | None = Field(None, description="Société émettrice du contrat")
    siret: str | None = Field(
        None,
        max_length=20,
        description="SIRET du fournisseur — sert à retrouver une fiche existante",
    )
    reuse_third_party_id: UUID | None = Field(
        None, description="Rattacher explicitement à une fiche fournisseur existante"
    )
    notify_third_party: bool = Field(
        True,
        description="False = saisie en personne : aucun lien de collecte n'est envoyé au fournisseur",
    )
    skip_documents: bool = Field(
        False,
        description="True = aucune vigilance documentaire dans Bobby (dérogation tracée)",
    )

    @model_validator(mode="after")
    def _skip_requires_manual_entry(self) -> "SupplierDossierCreate":
        """Ignorer le dépôt n'a de sens que si le fournisseur n'est pas sollicité."""
        if self.skip_documents and self.notify_third_party:
            raise ValueError(
                "skip_documents ne peut être utilisé qu'avec notify_third_party=false "
                "(saisie en personne)."
            )
        return self


class SupplierFrameworkSummary(BaseModel):
    """Un contrat cadre signé d'un fournisseur, avec la société qui l'a émis."""

    contract_request_id: UUID
    reference: str
    status: str
    issuer_company_id: UUID | None = None
    issuer_company_name: str | None = None


class SupplierLookupResponse(BaseModel):
    """Résultat de la recherche d'un fournisseur par SIRET.

    Un contrat cadre lie le fournisseur à **une** société émettrice : les
    champs `has_framework_contract` et `framework_contract_*` répondent pour la
    société interrogée, tandis que `framework_contracts` liste tous ses cadres,
    toutes sociétés du groupe confondues.
    """

    exists: bool
    third_party_id: UUID | None = None
    company_name: str | None = None
    siren: str | None = None
    compliance_status: str | None = None
    has_framework_contract: bool = False
    framework_contract_id: UUID | None = None
    framework_contract_reference: str | None = None
    framework_contracts: list[SupplierFrameworkSummary] = []
    open_contract_request_id: UUID | None = None
    open_contract_request_status: str | None = None


class ContractConfigRequest(BaseModel):
    """Request to configure a contract.

    payment_terms values: "immediate" (comptant), "net_30" (30 jours), "net_45_eom" (45 jours fin de mois)
    invoice_submission_method values: "email" (factures@geminiconsulting.fr), "boondmanager"
    """

    company_id: UUID | None = None
    mission_description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    daily_rate: Decimal = Decimal("0")
    estimated_days: int | None = None
    payment_terms: str = "net_30"
    invoice_submission_method: str = "email"
    invoice_email: str = ""
    tacit_renewal_months: int | None = Field(
        None, ge=1, le=24, description="Nombre de mois pour la tacite reconduction (annexe)"
    )
    excluded_optional_article_keys: list[str] = Field(
        default_factory=list, description="Clés des articles optionnels à exclure du contrat"
    )
    special_conditions: str = ""


# ── Contract companies ────────────────────────────────────────────────────────


class ContractCompanyRequest(BaseModel):
    """Create or update an issuing company."""

    name: str = Field(..., max_length=255)
    code: str = Field(
        ...,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z0-9]{3}$",
        description="3-letter code used in contract references (e.g. GEM, GCI)",
    )
    legal_form: str = Field(..., max_length=50)
    capital: str = Field(..., max_length=100)
    head_office: str = Field(..., max_length=500)
    rcs_city: str = Field(..., max_length=100)
    rcs_number: str = Field(..., max_length=50)
    representative_is_entity: bool = False
    representative_name: str = Field(..., max_length=255)
    representative_quality: str = Field(..., max_length=255)
    representative_sub_name: str | None = Field(None, max_length=255)
    representative_sub_quality: str | None = Field(None, max_length=255)
    signatory_name: str = Field(..., max_length=255)
    invoices_company_mail: str | None = Field(None, max_length=255)
    email_from: str | None = Field(
        None, max_length=255, description="Email expediteur (ex: noreply@geminiconsulting.fr)"
    )
    color_code: str = Field("#4BBEA8", pattern=r"^#[0-9A-Fa-f]{6}$")
    boond_agency_id: int | None = Field(
        None, description="ID de l'agence Boond associée à cette société émettrice"
    )
    is_default: bool = False
    is_active: bool = True


class ContractCompanyResponse(BaseModel):
    """Issuing company response."""

    id: UUID
    name: str
    code: str
    legal_form: str
    capital: str
    head_office: str
    rcs_city: str
    rcs_number: str
    representative_is_entity: bool
    representative_name: str
    representative_quality: str
    representative_sub_name: str | None = None
    representative_sub_quality: str | None = None
    signatory_name: str
    invoices_company_mail: str | None = None
    email_from: str | None = None
    color_code: str
    boond_agency_id: int | None = None
    has_logo: bool
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ComplianceOverrideRequest(BaseModel):
    """Request to override compliance check."""

    reason: str = Field(..., min_length=10, max_length=500)


class SkipDocumentsRequest(BaseModel):
    """Request to skip (or restore) the vigilance document collection."""

    reason: str | None = Field(
        None,
        max_length=500,
        description=("Justification tracée du saut de collecte. Ignorée quand restore=True."),
    )
    restore: bool = Field(
        False,
        description="True pour rétablir le dépôt des documents précédemment ignoré.",
    )


class CustomArticleItem(BaseModel):
    """A custom article added to a specific contract."""

    key: str = Field(..., max_length=50, pattern=r"^custom_[a-z0-9_]+$")
    title: str = Field(..., max_length=200)
    content: str = ""


class CustomAnnexItem(BaseModel):
    """A custom annex added to a specific contract."""

    key: str = Field(..., max_length=50, pattern=r"^custom_[a-z0-9_]+$")
    title: str = Field(..., max_length=200)
    content: str = ""


class ArticleOverridesRequest(BaseModel):
    """Per-contract article/annex content overrides, custom items, and ordering.

    Keys are article_key / annexe_key; values are the overridden HTML content.
    Pass an empty string to reset an override (restores template default).
    deleted_article_keys / deleted_annex_keys: keys to exclude from the PDF.
    Pass an empty list to clear all deletions for that type.
    custom_articles / custom_annexes: extra articles/annexes for this contract only.
    article_order / annex_order: ordered list of keys defining display order.
    """

    article_overrides: dict[str, str] = Field(default_factory=dict)
    annex_overrides: dict[str, str] = Field(default_factory=dict)
    deleted_article_keys: list[str] | None = None
    deleted_annex_keys: list[str] | None = None
    custom_articles: list[CustomArticleItem] | None = None
    custom_annexes: list[CustomAnnexItem] | None = None
    article_order: list[str] | None = None
    annex_order: list[str] | None = None


class PartnerReviewRequest(BaseModel):
    """Request from partner reviewing a contract draft."""

    approved: bool
    comments: str | None = Field(None, max_length=2000)


class ContractResponse(BaseModel):
    """Contract document response."""

    id: UUID
    contract_request_id: UUID
    reference: str
    version: int
    s3_key_draft: str
    s3_key_signed: str | None = None
    yousign_status: str | None = None
    partner_comments: str | None = None
    created_at: datetime
    signed_at: datetime | None = None


class WebhookResponse(BaseModel):
    """Standard webhook response (always 200 OK)."""

    status: str = "ok"
    message: str = ""
