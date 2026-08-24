"""Purchase order (bon de commande) API routes."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdvOrAdminUser, ContractAccessUser
from app.config import get_settings
from app.contract_management.api.purchase_order_schemas import (
    BoondDeletionResponse,
    PanelSupplierListResponse,
    PanelSupplierResponse,
    PurchaseOrderAttachDelivery,
    PurchaseOrderCreate,
    PurchaseOrderListResponse,
    PurchaseOrderRenew,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.contract_management.application.panel_suppliers import (
    PanelSupplier,
    select_panel_suppliers,
)
from app.contract_management.application.use_cases.create_purchase_order import (
    CreatePurchaseOrderFromPositioningUseCase,
)
from app.contract_management.application.use_cases.update_purchase_order import (
    UpdatePurchaseOrderCommand,
    UpdatePurchaseOrderUseCase,
)
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    FrameworkContractNotSignedError,
    InvalidPurchaseOrderDataError,
    InvalidPurchaseOrderStatusError,
    PositioningNotFoundError,
    PositioningStateMismatchError,
    PurchaseOrderAlreadyExistsError,
    PurchaseOrderBoondSyncError,
    PurchaseOrderIncompleteError,
    PurchaseOrderNotEditableError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)
from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
    ContractRequestRepository,
)
from app.contract_management.infrastructure.adapters.postgres_purchase_order_repo import (
    PurchaseOrderRepository,
)
from app.contract_management.infrastructure.models import (
    ContractCompanyModel,
    ContractRequestModel,
)
from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger
from app.third_party.domain.entities.third_party import supplier_label
from app.third_party.infrastructure.models import ThirdPartyModel

logger = structlog.get_logger()

router = APIRouter(tags=["Purchase Orders"])

# Dépôt du document signé : mêmes garde-fous que le portail tiers.
ALLOWED_SIGNED_EXTENSIONS = frozenset({"pdf", "png", "jpg", "jpeg"})
MAX_SIGNED_DOCUMENT_BYTES = 16 * 1024 * 1024


def _to_float(value) -> float | None:
    """Decimal → float pour la sérialisation JSON, en préservant None."""
    return float(value) if value is not None else None


def _po_to_response(
    po: PurchaseOrder,
    *,
    third_party_name: str | None = None,
    company_name: str | None = None,
    framework=None,
) -> PurchaseOrderResponse:
    """Convert a PurchaseOrder entity to its API response."""
    framework_signed = po.is_covered_by(framework)
    return PurchaseOrderResponse(
        id=po.id,
        provisional_reference=po.provisional_reference,
        reference=po.reference,
        display_reference=po.display_reference,
        status=po.status.value,
        status_display=po.status.display_name,
        is_editable=po.status.is_editable,
        third_party_id=po.third_party_id,
        third_party_name=third_party_name,
        needs_third_party=po.needs_third_party,
        contract_request_id=po.contract_request_id,
        framework_contract_reference=framework.display_reference if framework else None,
        framework_contract_status=framework.status.value if framework else None,
        framework_contract_signed=framework_signed,
        # L'envoi en signature suppose un document généré et un cadre signé :
        # c'est la même règle que celle appliquée par l'entité.
        can_send_for_signature=(
            po.status == PurchaseOrderStatus.GENERATED and framework_signed and po.is_complete
        ),
        company_id=po.company_id,
        company_name=company_name,
        boond_consultant_id=po.boond_consultant_id,
        boond_consultant_type=po.boond_consultant_type,
        consultant_civility=po.consultant_civility,
        consultant_first_name=po.consultant_first_name,
        consultant_last_name=po.consultant_last_name,
        consultant_name=po.consultant_name or None,
        consultant_email=po.consultant_email,
        consultant_phone=po.consultant_phone,
        boond_positioning_id=po.boond_positioning_id,
        boond_need_id=po.boond_need_id,
        boond_delivery_id=po.boond_delivery_id,
        boond_project_id=po.boond_project_id,
        client_name=po.client_name,
        mission_title=po.mission_title,
        mission_description=po.mission_description,
        mission_site_name=po.mission_site_name,
        mission_address=po.mission_address,
        mission_postal_code=po.mission_postal_code,
        mission_city=po.mission_city,
        sale_daily_rate=_to_float(po.sale_daily_rate),
        purchase_daily_rate=_to_float(po.purchase_daily_rate),
        days_sold=_to_float(po.days_sold),
        free_days=float(po.free_days or 0),
        billable_days=float(po.billable_days),
        total_amount=float(po.total_amount),
        estimated_margin=_to_float(po.estimated_margin),
        start_date=po.start_date,
        end_date=po.end_date,
        has_draft=po.s3_key_draft is not None,
        has_signed_document=po.s3_key_signed is not None,
        sent_for_signature_at=po.sent_for_signature_at,
        signed_at=po.signed_at,
        boond_contract_id=po.boond_contract_id,
        boond_purchase_order_id=po.boond_purchase_order_id,
        boond_sync_error=po.boond_sync_error,
        parent_purchase_order_id=po.parent_purchase_order_id,
        commercial_email=po.commercial_email,
        missing_fields=po.missing_fields,
        status_history=po.status_history or [],
        created_at=po.created_at,
        updated_at=po.updated_at,
    )


async def _third_party_names(db: AsyncSession, ids: list[UUID]) -> dict[UUID, str]:
    """Nom des fournisseurs, en une requête pour toute une liste.

    Un dossier dont la raison sociale n'est pas encore saisie garde un nom
    lisible — son signataire, à défaut son adresse de contact. Sans cela, le
    bon de commande afficherait « — » quel que soit le fournisseur rattaché.
    """
    if not ids:
        return {}
    result = await db.execute(
        select(
            ThirdPartyModel.id,
            ThirdPartyModel.company_name,
            ThirdPartyModel.signatory_first_name,
            ThirdPartyModel.signatory_last_name,
            ThirdPartyModel.contact_email,
        ).where(ThirdPartyModel.id.in_(ids))
    )
    return {
        row[0]: supplier_label(
            company_name=row[1],
            signatory_first_name=row[2],
            signatory_last_name=row[3],
            contact_email=row[4],
        )
        for row in result.all()
    }


async def _company_names(db: AsyncSession, ids: list[UUID]) -> dict[UUID, str]:
    """Nom des sociétés émettrices, en une requête pour toute une liste."""
    wanted = [i for i in ids if i]
    if not wanted:
        return {}
    result = await db.execute(
        select(ContractCompanyModel.id, ContractCompanyModel.name).where(
            ContractCompanyModel.id.in_(wanted)
        )
    )
    return {row[0]: row[1] for row in result.all()}


async def _load_framework(cr_repo: ContractRequestRepository, po: PurchaseOrder):
    """Charge le dossier cadre rattaché au bon de commande, s'il y en a un."""
    if not po.contract_request_id:
        return None
    return await cr_repo.get_by_id(po.contract_request_id)


async def _respond(
    db: AsyncSession,
    cr_repo: ContractRequestRepository,
    po: PurchaseOrder,
) -> PurchaseOrderResponse:
    """Réponse complète : fournisseur, société émettrice et contrat cadre."""
    names = await _third_party_names(db, [po.third_party_id] if po.third_party_id else [])
    companies = await _company_names(db, [po.company_id] if po.company_id else [])
    return _po_to_response(
        po,
        third_party_name=names.get(po.third_party_id),
        company_name=companies.get(po.company_id),
        framework=await _load_framework(cr_repo, po),
    )


@router.post(
    "",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un bon de commande depuis un positionnement Boond",
)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Ouvre le bon de commande d'une mission à partir de son positionnement.

    Même chemin que le webhook positionnement, déclenché à la main : le
    positionnement est lu dans Boond, son état contrôlé, et le bon de commande
    créé en brouillon, sans fournisseur. ADV/admin uniquement.
    """
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.database.repositories.user_repository import UserRepository
    from app.infrastructure.settings.app_settings_service import AppSettingsService

    settings = get_settings()
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    use_case = CreatePurchaseOrderFromPositioningUseCase(
        purchase_order_repository=po_repo,
        crm_service=BoondCrmAdapter(BoondClient(settings)),
        company_repository=cr_repo,
        user_repository=UserRepository(db),
        settings_service=AppSettingsService(db),
    )

    try:
        po = await use_case.execute(body.boond_positioning_id, created_by=user_id)
    except PositioningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (PositioningStateMismatchError, PurchaseOrderAlreadyExistsError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        logger.error(
            "purchase_order_creation_failed",
            positioning_id=body.boond_positioning_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La création du bon de commande a échoué.",
        )

    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_REQUEST_CREATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(po.id),
        details={
            "kind": "purchase_order",
            "source": "manual",
            "reference": po.display_reference,
            "positioning_id": body.boond_positioning_id,
        },
    )
    return _po_to_response(po)


@router.get(
    "",
    response_model=PurchaseOrderListResponse,
    summary="Lister les bons de commande",
)
async def list_purchase_orders(  # noqa: PLR0913
    auth: ContractAccessUser,
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    third_party_id: UUID | None = None,
    company_id: UUID | None = None,
    contract_request_id: UUID | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Liste les bons de commande, filtrables par statut, fournisseur ou texte.

    `company_id` et `contract_request_id` isolent les missions d'une société
    émettrice : un fournisseur travaillant avec plusieurs sociétés du groupe a
    des missions distinctes pour chacune, sous des contrats cadres différents.
    """
    _user_id, role, email = auth
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    status_obj = None
    if status_filter:
        try:
            status_obj = PurchaseOrderStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Statut invalide : {status_filter}",
            )

    filters = {
        "status": status_obj,
        "third_party_id": third_party_id,
        "company_id": company_id,
        "contract_request_id": contract_request_id,
        "search": search,
    }
    items = await po_repo.list_all(skip=skip, limit=limit, **filters)
    total = await po_repo.count(**filters)

    # Le commercial ne voit que les missions dont il est le commercial : le
    # filtre est appliqué après coup, la pagination restant portée par l'ADV.
    if role == "commercial":
        items = [po for po in items if (po.commercial_email or "").lower() == email.lower()]

    names = await _third_party_names(db, [po.third_party_id for po in items if po.third_party_id])
    companies = await _company_names(db, [po.company_id for po in items])
    frameworks = {}
    for po in items:
        if po.contract_request_id and po.contract_request_id not in frameworks:
            frameworks[po.contract_request_id] = await cr_repo.get_by_id(po.contract_request_id)

    return PurchaseOrderListResponse(
        items=[
            _po_to_response(
                po,
                third_party_name=names.get(po.third_party_id),
                company_name=companies.get(po.company_id),
                framework=frameworks.get(po.contract_request_id),
            )
            for po in items
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/suppliers",
    response_model=PanelSupplierListResponse,
    summary="Fournisseurs du panel d'une société émettrice",
)
async def list_panel_suppliers(
    _auth: ContractAccessUser,
    company_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Liste les fournisseurs rattachables à un bon de commande.

    Ce ne sont pas tous les tiers connus de Bobby : seulement ceux avec qui la
    société émettrice a un contrat cadre, signé ou en cours. Chaque fournisseur
    est présenté avec la référence de ce cadre — l'information utile à l'ADV,
    là où le SIREN ne dit rien du droit à commander.
    """
    result = await db.execute(
        select(
            ContractRequestModel.id,
            ContractRequestModel.status,
            ContractRequestModel.reference,
            ContractRequestModel.provisional_reference,
            ContractRequestModel.company_id,
            ThirdPartyModel.id,
            ThirdPartyModel.company_name,
            ThirdPartyModel.type,
            ThirdPartyModel.signatory_first_name,
            ThirdPartyModel.signatory_last_name,
            ThirdPartyModel.contact_email,
        )
        .join(ThirdPartyModel, ThirdPartyModel.id == ContractRequestModel.third_party_id)
        .order_by(ContractRequestModel.created_at.desc())
    )

    candidates = [
        PanelSupplier(
            third_party_id=tp_id,
            company_name=company_name,
            third_party_type=tp_type,
            contract_request_id=cr_id,
            framework_reference=reference or provisional_reference,
            framework_status=cr_status,
            framework_company_id=cr_company_id,
            signatory_first_name=signatory_first_name,
            signatory_last_name=signatory_last_name,
            contact_email=contact_email,
        )
        for (
            cr_id,
            cr_status,
            reference,
            provisional_reference,
            cr_company_id,
            tp_id,
            company_name,
            tp_type,
            signatory_first_name,
            signatory_last_name,
            contact_email,
        ) in result.all()
    ]

    suppliers = select_panel_suppliers(candidates, company_id)

    return PanelSupplierListResponse(
        items=[
            PanelSupplierResponse(
                third_party_id=supplier.third_party_id,
                label=supplier.label,
                company_name=supplier.company_name,
                third_party_type=supplier.third_party_type,
                contract_request_id=supplier.contract_request_id,
                framework_reference=supplier.framework_reference,
                framework_status=supplier.framework_status,
                framework_signed=supplier.framework_signed,
            )
            for supplier in suppliers
        ],
        total=len(suppliers),
    )


@router.get(
    "/{purchase_order_id}",
    response_model=PurchaseOrderResponse,
    summary="Détail d'un bon de commande",
)
async def get_purchase_order(
    purchase_order_id: UUID,
    auth: ContractAccessUser,
    db: AsyncSession = Depends(get_db),
):
    """Retourne un bon de commande et l'état de son contrat cadre."""
    _user_id, role, email = auth
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    po = await po_repo.get_by_id(purchase_order_id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bon de commande non trouvé."
        )

    if role == "commercial" and (po.commercial_email or "").lower() != email.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé.")

    return await _respond(db, cr_repo, po)


@router.patch(
    "/{purchase_order_id}",
    response_model=PurchaseOrderResponse,
    summary="Compléter ou corriger un bon de commande",
)
async def update_purchase_order(
    purchase_order_id: UUID,
    body: PurchaseOrderUpdate,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Complète le bon de commande : fournisseur, mission, conditions.

    Seuls les champs transmis sont appliqués. ADV/admin uniquement.
    """
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun champ à mettre à jour.",
        )

    use_case = UpdatePurchaseOrderUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
    )

    try:
        po = await use_case.execute(
            UpdatePurchaseOrderCommand(purchase_order_id=purchase_order_id, fields=fields)
        )
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PurchaseOrderNotEditableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidPurchaseOrderDataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await db.commit()

    return await _respond(db, cr_repo, po)


@router.post(
    "/{purchase_order_id}/cancel",
    response_model=PurchaseOrderResponse,
    summary="Annuler un bon de commande",
)
async def cancel_purchase_order(
    purchase_order_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Annule un bon de commande non signé.

    L'annulation libère le positionnement : un nouveau bon de commande pourra
    être créé pour la même mission. ADV/admin uniquement.
    """
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    po = await po_repo.get_by_id(purchase_order_id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bon de commande non trouvé."
        )

    try:
        po.cancel()
    except InvalidPurchaseOrderStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    saved = await po_repo.save(po)
    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_REQUEST_CANCELLED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(saved.id),
        details={"kind": "purchase_order", "reference": saved.display_reference},
    )

    return await _respond(db, cr_repo, saved)


@router.post(
    "/{purchase_order_id}/generate",
    response_model=PurchaseOrderResponse,
    summary="Générer le document du bon de commande",
)
async def generate_purchase_order_document(
    purchase_order_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Produit le PDF du bon de commande et le dépose sur S3. ADV/admin uniquement."""
    from app.contract_management.application.use_cases.generate_purchase_order_document import (
        GeneratePurchaseOrderDocumentUseCase,
    )
    from app.infrastructure.storage.s3_client import S3StorageClient
    from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
        ThirdPartyRepository,
    )

    settings = get_settings()
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    use_case = GeneratePurchaseOrderDocumentUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
        third_party_repository=ThirdPartyRepository(db),
        s3_service=S3StorageClient(settings),
        db=db,
    )

    try:
        po = await use_case.execute(purchase_order_id)
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PurchaseOrderIncompleteError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except InvalidPurchaseOrderStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        logger.error(
            "purchase_order_generation_failed",
            purchase_order_id=str(purchase_order_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La génération du bon de commande a échoué.",
        )

    await db.commit()
    return await _respond(db, cr_repo, po)


@router.get(
    "/{purchase_order_id}/document",
    summary="Lien de téléchargement du bon de commande",
)
async def get_purchase_order_document(
    purchase_order_id: UUID,
    auth: ContractAccessUser,
    signed: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Retourne une URL signée vers le document, généré ou signé."""
    from app.infrastructure.storage.s3_client import S3StorageClient

    _user_id, role, email = auth
    po = await PurchaseOrderRepository(db).get_by_id(purchase_order_id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bon de commande non trouvé."
        )
    if role == "commercial" and (po.commercial_email or "").lower() != email.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé.")

    s3_key = po.s3_key_signed if signed else po.s3_key_draft
    if not s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document signé indisponible."
            if signed
            else "Le bon de commande n'a pas encore été généré.",
        )

    url = await S3StorageClient(get_settings()).get_presigned_url(s3_key)
    return {"url": url, "reference": po.display_reference, "signed": signed}


@router.post(
    "/{purchase_order_id}/send-for-signature",
    response_model=PurchaseOrderResponse,
    summary="Marquer le bon de commande comme envoyé en signature",
)
async def send_purchase_order_for_signature(
    purchase_order_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Envoie le bon de commande en signature au fournisseur.

    Le contrat cadre doit être signé : un bon de commande n'a de valeur que
    sous un cadre en vigueur, qui en porte les conditions juridiques. Le
    circuit de signature reste manuel, comme pour le contrat cadre — le
    document est téléchargé, transmis, puis redéposé signé. ADV/admin.
    """
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    po = await po_repo.get_by_id(purchase_order_id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bon de commande non trouvé."
        )

    framework = await _load_framework(cr_repo, po)

    try:
        po.send_for_signature(framework_contract_signed=po.is_covered_by(framework))
    except FrameworkContractNotSignedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidPurchaseOrderStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    saved = await po_repo.save(po)
    await db.commit()

    logger.info(
        "purchase_order_sent_for_signature",
        purchase_order_id=str(saved.id),
        reference=saved.display_reference,
    )
    return await _respond(db, cr_repo, saved)


@router.post(
    "/{purchase_order_id}/mark-as-signed",
    response_model=PurchaseOrderResponse,
    summary="Déposer le bon de commande signé",
)
async def mark_purchase_order_as_signed(
    purchase_order_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Enregistre le document signé par le fournisseur et acte la signature.

    La synchronisation BoondManager n'est pas déclenchée ici : elle est
    lancée juste après, et reste relançable si Boond répond mal. ADV/admin.
    """
    from app.infrastructure.storage.s3_client import S3StorageClient

    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    po = await po_repo.get_by_id(purchase_order_id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bon de commande non trouvé."
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")

    extension = (
        file.filename.rsplit(".", 1)[-1].lower()
        if file.filename and "." in file.filename
        else "pdf"
    )
    if extension not in ALLOWED_SIGNED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format non accepté : {extension}. Attendu : "
            f"{', '.join(sorted(ALLOWED_SIGNED_EXTENSIONS))}.",
        )
    if len(content) > MAX_SIGNED_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document trop volumineux (16 Mo maximum).",
        )

    s3_key = f"purchase-orders/{po.display_reference}/signe.{extension}"
    await S3StorageClient(get_settings()).upload_file(
        key=s3_key,
        content=content,
        content_type=file.content_type or "application/pdf",
    )

    try:
        po.mark_signed(s3_key)
    except InvalidPurchaseOrderStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    saved = await po_repo.save(po)
    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_SIGNED,
        AuditResource.CONTRACT,
        user_id=user_id,
        resource_id=str(saved.id),
        details={"kind": "purchase_order", "reference": saved.display_reference},
    )
    return await _respond(db, cr_repo, saved)


@router.post(
    "/{purchase_order_id}/attach-delivery",
    response_model=PurchaseOrderResponse,
    summary="Rattacher à la main la prestation BoondManager de la mission",
)
async def attach_delivery_to_purchase_order(
    purchase_order_id: UUID,
    body: PurchaseOrderAttachDelivery,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Retient la prestation Boond que le report n'a pas su retrouver.

    L'achat fournisseur se rattache à la prestation : sans elle, le report
    s'arrête là. La prestation est relue dans le CRM avant d'être retenue — un
    achat posé sur la mauvaise ne se corrige qu'en le supprimant. Possible quel
    que soit l'état du bon de commande, le report ayant lieu après la
    signature. ADV/admin uniquement.
    """
    from app.contract_management.application.use_cases.attach_delivery_to_purchase_order import (
        AttachDeliveryToPurchaseOrderUseCase,
    )
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient

    cr_repo = ContractRequestRepository(db)
    use_case = AttachDeliveryToPurchaseOrderUseCase(
        purchase_order_repository=PurchaseOrderRepository(db),
        crm_service=BoondCrmAdapter(BoondClient(get_settings())),
    )

    try:
        po = await use_case.execute(purchase_order_id, body.delivery_id)
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidPurchaseOrderDataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await db.commit()

    audit_logger.log(
        AuditAction.PURCHASE_ORDER_DELIVERY_ATTACHED,
        AuditResource.CONTRACT,
        user_id=user_id,
        resource_id=str(po.id),
        details={
            "kind": "purchase_order",
            "reference": po.display_reference,
            "boond_delivery_id": po.boond_delivery_id,
        },
    )
    return await _respond(db, cr_repo, po)


@router.post(
    "/{purchase_order_id}/push-to-boond",
    response_model=PurchaseOrderResponse,
    summary="Reporter le bon de commande signé dans BoondManager",
)
async def push_purchase_order_to_boond(
    purchase_order_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Crée la ressource, le contrat et le bon de commande côté Boond.

    Chaque étape est idempotente : relancer après un échec ne recrée pas ce qui
    est déjà passé. ADV/admin uniquement.
    """
    from app.contract_management.application.use_cases.sync_purchase_order_to_boond import (
        SyncPurchaseOrderToBoondUseCase,
    )
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.settings.app_settings_service import AppSettingsService
    from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
        ThirdPartyRepository,
    )

    settings = get_settings()
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    use_case = SyncPurchaseOrderToBoondUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
        third_party_repository=ThirdPartyRepository(db),
        crm_service=BoondCrmAdapter(BoondClient(settings)),
        db=db,
        settings_service=AppSettingsService(db),
    )

    try:
        po = await use_case.execute(purchase_order_id)
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PurchaseOrderBoondSyncError as exc:
        # L'erreur est déjà consignée sur le bon de commande : on committe pour
        # que l'ADV la voie dans l'écran, puis on la remonte.
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_PUSHED_TO_CRM,
        AuditResource.CONTRACT,
        user_id=user_id,
        resource_id=str(po.id),
        details={
            "kind": "purchase_order",
            "reference": po.display_reference,
            "boond_contract_id": po.boond_contract_id,
            "boond_purchase_order_id": po.boond_purchase_order_id,
        },
    )
    return await _respond(db, cr_repo, po)


@router.post(
    "/{purchase_order_id}/delete-from-boond",
    response_model=BoondDeletionResponse,
    summary="[Test] Supprimer dans BoondManager ce que le report y a créé",
)
async def delete_purchase_order_from_boond(
    purchase_order_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Défait le report : achat, contrat, prestation, et positionnement remis en attente.

    Outil de test, pour rejouer un report sans laisser d'objets fantômes dans
    le CRM. La conversion du candidat en ressource n'est pas défaite —
    BoondManager ne sait pas revenir en arrière — ni la société fournisseur,
    qui appartient au contrat cadre. ADV/admin uniquement.
    """
    from app.contract_management.application.use_cases.delete_purchase_order_from_boond import (
        DeletePurchaseOrderFromBoondUseCase,
    )
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient

    settings = get_settings()
    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    use_case = DeletePurchaseOrderFromBoondUseCase(
        purchase_order_repository=po_repo,
        crm_service=BoondCrmAdapter(BoondClient(settings)),
    )

    try:
        po, report = await use_case.execute(purchase_order_id)
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_PUSHED_TO_CRM,
        AuditResource.CONTRACT,
        user_id=user_id,
        resource_id=str(po.id),
        details={
            "kind": "purchase_order",
            "action": "delete_from_boond",
            "reference": po.display_reference,
            "report": report,
        },
    )
    return BoondDeletionResponse(purchase_order=await _respond(db, cr_repo, po), report=report)


@router.post(
    "/{purchase_order_id}/renew",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reconduire la mission par un nouveau bon de commande",
)
async def renew_purchase_order(
    purchase_order_id: UUID,
    body: PurchaseOrderRenew,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Ouvre le bon de commande suivant d'une mission qui se poursuit.

    Pas de tacite reconduction : chaque prolongation est un document distinct,
    numéroté à la suite et signé pour lui-même. Le positionnement Boond
    d'origine est conservé. ADV/admin uniquement.
    """
    from app.contract_management.application.use_cases.renew_purchase_order import (
        RenewPurchaseOrderCommand,
        RenewPurchaseOrderUseCase,
    )

    po_repo = PurchaseOrderRepository(db)
    cr_repo = ContractRequestRepository(db)

    use_case = RenewPurchaseOrderUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
    )

    try:
        renewal = await use_case.execute(
            RenewPurchaseOrderCommand(
                purchase_order_id=purchase_order_id,
                start_date=body.start_date,
                end_date=body.end_date,
                days_sold=body.days_sold,
                free_days=body.free_days,
                purchase_daily_rate=body.purchase_daily_rate,
                sale_daily_rate=body.sale_daily_rate,
                created_by=user_id,
            )
        )
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidPurchaseOrderDataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_REQUEST_CREATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(renewal.id),
        details={
            "kind": "purchase_order",
            "source": "renewal",
            "reference": renewal.display_reference,
            "parent_id": str(purchase_order_id),
        },
    )
    return await _respond(db, cr_repo, renewal)
