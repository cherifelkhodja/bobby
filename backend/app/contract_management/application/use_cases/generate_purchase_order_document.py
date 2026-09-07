"""Use case: Generate the purchase order document (PDF)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import structlog

from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    InvalidPurchaseOrderStatusError,
    PurchaseOrderIncompleteError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)

logger = structlog.get_logger()

TEMPLATE_NAME = "bon_de_commande.html"

# Taux de TVA appliqué aux prestations de services intérieures.
VAT_RATE = Decimal("20")

# Libellés des conditions de paiement, repris du contrat cadre quand il en
# porte une : le bon de commande n'invente pas ses propres délais.
PAYMENT_TERMS_LABELS = {
    "immediate": "comptant",
    "net_30": "à 30 jours",
    "net_45_eom": "à 45 jours fin de mois",
}

# Sociétés émettrices qui ne contresignent pas leurs bons de commande : le
# document n'attend alors que la signature du fournisseur. Reconnues par un
# fragment de leur nom, comme la charte graphique (`BRAND_THEMES`).
ISSUERS_WITHOUT_SIGNATURE: tuple[str, ...] = ("leonum",)


def issuer_signs_purchase_orders(company) -> bool:
    """Le bon de commande porte-t-il une carte de signature pour l'émetteur ?

    Sans société connue, le document reste bilatéral.
    """
    name = (getattr(company, "name", None) or "").lower()
    return not any(fragment in name for fragment in ISSUERS_WITHOUT_SIGNATURE)


class GeneratePurchaseOrderDocumentUseCase:
    """Génère le PDF du bon de commande et le dépose sur S3.

    Le document ne porte que le CJM d'achat : le TJM de vente au client n'entre
    jamais dans le contexte du gabarit.
    """

    def __init__(
        self,
        purchase_order_repository,
        contract_request_repository,
        third_party_repository,
        s3_service,
        db=None,
    ) -> None:
        self._po_repo = purchase_order_repository
        self._cr_repo = contract_request_repository
        self._tp_repo = third_party_repository
        self._s3 = s3_service
        self._db = db

    async def execute(self, purchase_order_id: UUID) -> PurchaseOrder:
        """Execute the use case.

        Returns:
            The purchase order, now GENERATED, with its document key set.

        Raises:
            PurchaseOrderNotFoundError: If the purchase order does not exist.
            PurchaseOrderIncompleteError: If mission data is still missing.
            InvalidPurchaseOrderStatusError: If the status forbids generation.
        """
        po = await self._po_repo.get_by_id(purchase_order_id)
        if not po:
            raise PurchaseOrderNotFoundError(str(purchase_order_id))

        # Gardes précoces : refuser une transition illégale ou un dossier
        # incomplet AVANT de produire le PDF et de le déposer sur S3, sinon un
        # fichier orphelin subsiste. `mark_generated` refera ces contrôles.
        if not po.status.can_transition_to(PurchaseOrderStatus.GENERATED):
            raise InvalidPurchaseOrderStatusError(
                po.status.value, PurchaseOrderStatus.GENERATED.value
            )
        if not po.is_complete:
            raise PurchaseOrderIncompleteError(po.display_reference, po.missing_fields)

        # C'est ici que le bon de commande prend son rang dans la séquence de
        # sa société émettrice : le numéro va s'imprimer, il devient définitif.
        # Une régénération ne renumérote pas (`assign_reference` ne joue qu'une
        # fois), le numéro ayant pu être communiqué au fournisseur.
        if po.reference is None:
            company_code = None
            if po.company_id:
                company_code = await self._cr_repo.get_company_code(po.company_id)
            po.assign_reference(await self._po_repo.get_next_reference(company_code))

        third_party = (
            await self._tp_repo.get_by_id(po.third_party_id) if po.third_party_id else None
        )
        framework = (
            await self._cr_repo.get_by_id(po.contract_request_id)
            if po.contract_request_id
            else None
        )
        company = await self._load_company(po.company_id)

        context = self._build_context(po, third_party, framework, company)
        logo = await self._load_company_logo(company)
        if logo:
            context["logo_b64"], context["logo_mime"] = logo

        from app.contract_management.infrastructure.adapters.pdf_rendering import render_pdf

        pdf_content = render_pdf(TEMPLATE_NAME, context)

        version = 1 + sum(
            1 for entry in po.status_history if entry.get("status") == PurchaseOrderStatus.GENERATED
        )
        s3_key = f"purchase-orders/{po.display_reference}/bon_de_commande_v{version}.pdf"
        await self._s3.upload_file(
            key=s3_key,
            content=pdf_content,
            content_type="application/pdf",
        )

        po.mark_generated(s3_key)
        saved = await self._po_repo.save(po)

        logger.info(
            "purchase_order_document_generated",
            purchase_order_id=str(saved.id),
            reference=saved.display_reference,
            version=version,
            s3_key=s3_key,
        )
        return saved

    def _build_context(self, po: PurchaseOrder, third_party, framework, company) -> dict:
        """Construit le contexte du gabarit, sans jamais y mettre le TJM."""
        # Délai de paiement et protocole de facturation viennent tous deux du
        # contrat cadre : ce sont ceux que le fournisseur a acceptés en le
        # signant, et le bon de commande n'en invente pas d'autres. À défaut de
        # configuration, l'adresse de facturation de la société émettrice sert
        # de repli — c'est celle qu'imprime aussi le contrat.
        framework_config = (framework.contract_config or {}) if framework else {}
        payment_terms = framework_config.get("payment_terms")
        invoice_method = framework_config.get("invoice_submission_method") or "email"
        invoice_address = framework_config.get("invoice_email") or (
            (company.invoices_company_mail or "") if company else ""
        )

        # Tous les fournisseurs ne facturent pas la TVA : franchise en base,
        # autoliquidation. Le tiers porte cet assujettissement ; le taux, lui,
        # n'est pas une donnée du bon de commande — c'est le taux normal, seul
        # applicable à une prestation de services intérieure.
        vat_liable = getattr(third_party, "vat_liable", True) if third_party else True
        vat_amount = (
            (po.total_amount * VAT_RATE / Decimal("100")).quantize(Decimal("0.01"))
            if vat_liable
            else Decimal("0")
        )

        context: dict = {
            "reference": po.display_reference,
            "order_date": datetime.now(UTC).strftime("%d/%m/%Y"),
            "framework_reference": framework.display_reference if framework else "",
            "framework_signed_date": self._framework_signed_date(framework),
            # Mission
            "client_name": po.client_name or "",
            "mission_title": po.mission_title or "Mission de prestation",
            "mission_description": po.mission_description or "",
            "mission_place": self._mission_place(po),
            "start_date": _fmt_date(po.start_date),
            "end_date": _fmt_date(po.end_date),
            # Consultant
            "consultant_civility": po.consultant_civility or "",
            "consultant_name": po.consultant_name,
            "consultant_email": po.consultant_email or "",
            "consultant_phone": po.consultant_phone or "",
            # Conditions financières — CJM uniquement
            "purchase_daily_rate": _fmt_amount(po.purchase_daily_rate),
            "days_sold": _fmt_quantity(po.days_sold),
            "free_days": _fmt_quantity(po.free_days),
            "billable_days": _fmt_quantity(po.billable_days),
            "total_amount": _fmt_amount(po.total_amount),
            "vat_liable": vat_liable,
            "vat_rate": _fmt_quantity(VAT_RATE),
            "vat_amount": _fmt_amount(vat_amount),
            "total_amount_ttc": _fmt_amount(po.total_amount + vat_amount),
            "payment_terms_label": PAYMENT_TERMS_LABELS.get(payment_terms or "", ""),
            "invoice_submission_method": invoice_method,
            "invoice_address": invoice_address,
            # Interlocuteurs
            "commercial_email": po.commercial_email or "",
            # Signatures : Leonum ne contresigne pas, seul le fournisseur signe.
            "issuer_signs": issuer_signs_purchase_orders(company),
        }

        if company:
            context.update(
                {
                    "issuer_company_name": company.name,
                    "issuer_legal_form": company.legal_form,
                    "issuer_capital": company.capital,
                    "issuer_head_office": company.head_office,
                    "issuer_rcs_city": company.rcs_city,
                    "issuer_rcs_number": company.rcs_number,
                    "issuer_representative_is_entity": company.representative_is_entity,
                    "issuer_representative_name": company.representative_name,
                    "issuer_representative_quality": company.representative_quality,
                    "issuer_representative_sub_quality": (company.representative_sub_quality or ""),
                    "issuer_signatory_name": company.signatory_name,
                    "issuer_color_code": company.color_code,
                    "issuer_tva_number": company.tva_number or "",
                    "invoices_company_mail": company.invoices_company_mail or "",
                }
            )

        if third_party:
            context.update(
                {
                    "partner_company_name": third_party.company_name or "",
                    "partner_head_office": third_party.head_office_address or "",
                    "partner_siren": third_party.siren or "",
                    "partner_representative_civility": third_party.representative_civility or "",
                    "partner_representative_name": third_party.representative_name or "",
                    "partner_representative_title": third_party.representative_title or "",
                    "partner_signatory_name": _signatory_name(third_party),
                    "partner_contact_name": _adv_contact_name(third_party),
                    "partner_contact_email": (
                        getattr(third_party, "adv_contact_email", None)
                        or getattr(third_party, "contact_email", None)
                        or ""
                    ),
                }
            )

        return context

    @staticmethod
    def _framework_signed_date(framework) -> str:
        """Date de passage à l'état signé du contrat cadre, si connue."""
        if not framework:
            return ""
        for entry in reversed(framework.status_history or []):
            if entry.get("status") == ContractRequestStatus.SIGNED.value:
                raw = entry.get("entered_at", "")
                try:
                    return datetime.fromisoformat(raw).strftime("%d/%m/%Y")
                except (TypeError, ValueError):
                    return ""
        return ""

    @staticmethod
    def _mission_place(po: PurchaseOrder) -> str:
        """Lieu d'exécution sur une ligne, sans séparateurs orphelins."""
        street = ", ".join(p for p in (po.mission_site_name, po.mission_address) if p)
        town = " ".join(p for p in (po.mission_postal_code, po.mission_city) if p)
        return ", ".join(p for p in (street, town) if p)

    async def _load_company(self, company_id):
        """Charge la société émettrice, ou la société par défaut à défaut."""
        if self._db is None:
            return None
        from sqlalchemy import select

        from app.contract_management.infrastructure.models import ContractCompanyModel

        if company_id:
            result = await self._db.execute(
                select(ContractCompanyModel).where(ContractCompanyModel.id == company_id)
            )
        else:
            result = await self._db.execute(
                select(ContractCompanyModel)
                .where(
                    ContractCompanyModel.is_default.is_(True),
                    ContractCompanyModel.is_active.is_(True),
                )
                .limit(1)
            )
        return result.scalar_one_or_none()

    async def _load_company_logo(self, company) -> tuple[str, str] | None:
        """Charge le logo de la société émettrice depuis S3, en base64."""
        if not company or not company.logo_s3_key or not self._s3:
            return None
        try:
            import base64

            content = await self._s3.download_file(company.logo_s3_key)
            mime = "image/png"
            if company.logo_s3_key.lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            return base64.b64encode(content).decode("ascii"), mime
        except Exception as exc:
            logger.warning("purchase_order_logo_load_failed", error=str(exc))
            return None


def _signatory_name(third_party) -> str:
    """Nom du signataire du fournisseur, à défaut son représentant."""
    first = getattr(third_party, "signatory_first_name", None)
    last = getattr(third_party, "signatory_last_name", None)
    name = " ".join(p for p in (first, last) if p).strip()
    return name or (third_party.representative_name or "")


def _adv_contact_name(third_party) -> str:
    """Correspondant administratif du fournisseur, à défaut son signataire."""
    first = getattr(third_party, "adv_contact_first_name", None)
    last = getattr(third_party, "adv_contact_last_name", None)
    civility = getattr(third_party, "adv_contact_civility", None)
    name = " ".join(p for p in (civility, first, last) if p).strip()
    return name or _signatory_name(third_party)


def _fmt_date(value: date | None) -> str:
    """Date au format français, chaîne vide si absente."""
    return value.strftime("%d/%m/%Y") if isinstance(value, date) else ""


def _fmt_amount(value: Decimal | None) -> str:
    """Montant avec séparateur de milliers, sans décimales inutiles."""
    if value is None:
        return ""
    quantized = value.quantize(Decimal("0.01"))
    entier, _, decimales = f"{quantized:.2f}".partition(".")
    entier = f"{int(entier):,}".replace(",", " ")
    return entier if decimales == "00" else f"{entier},{decimales}"


def _fmt_quantity(value: Decimal | None) -> str:
    """Quantité de jours : demi-journées conservées, .00 supprimé."""
    if value is None:
        return "0"
    text = f"{value.normalize():f}"
    return text.replace(".", ",")
