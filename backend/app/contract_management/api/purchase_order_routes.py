"""Purchase order (bon de commande) API routes."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdvOrAdminUser, ContractAccessUser
from app.config import get_settings
from app.contract_management.api.purchase_order_schemas import (
    PurchaseOrderCreate,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
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
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
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
from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger
from app.third_party.infrastructure.models import ThirdPartyModel

logger = structlog.get_logger()

router = APIRouter(tags=["Purchase Orders"])

# Un cadre est en vigueur dès qu'il a été signé — ARCHIVED compris, un dossier
# archivé par le CRON restant un contrat bel et bien signé.
_SIGNED_FRAMEWORK_STATUSES = frozenset(
    {
        ContractRequestStatus.SIGNED,
        ContractRequestStatus.ACTIVE,
        ContractRequestStatus.ARCHIVED,
    }
)


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
    framework=None,
) -> PurchaseOrderResponse:
    """Convert a PurchaseOrder entity to its API response."""
    framework_signed = bool(framework and framework.status in _SIGNED_FRAMEWORK_STATUSES)
    return PurchaseOrderResponse(
        id=po.id,
        reference=po.reference,
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
    """Nom des fournisseurs, en une requête pour toute une liste."""
    if not ids:
        return {}
    result = await db.execute(
        select(ThirdPartyModel.id, ThirdPartyModel.company_name).where(ThirdPartyModel.id.in_(ids))
    )
    return {row[0]: row[1] for row in result.all() if row[1]}


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
    """Réponse complète d'un bon de commande : nom du fournisseur et cadre."""
    names = await _third_party_names(db, [po.third_party_id] if po.third_party_id else [])
    return _po_to_response(
        po,
        third_party_name=names.get(po.third_party_id),
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
            "reference": po.reference,
            "positioning_id": body.boond_positioning_id,
        },
    )
    return _po_to_response(po)


@router.get(
    "",
    response_model=PurchaseOrderListResponse,
    summary="Lister les bons de commande",
)
async def list_purchase_orders(
    auth: ContractAccessUser,
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    third_party_id: UUID | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Liste les bons de commande, filtrables par statut, fournisseur ou texte."""
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

    items = await po_repo.list_all(
        skip=skip,
        limit=limit,
        status=status_obj,
        third_party_id=third_party_id,
        search=search,
    )
    total = await po_repo.count(status=status_obj, third_party_id=third_party_id, search=search)

    # Le commercial ne voit que les missions dont il est le commercial : le
    # filtre est appliqué après coup, la pagination restant portée par l'ADV.
    if role == "commercial":
        items = [po for po in items if (po.commercial_email or "").lower() == email.lower()]

    names = await _third_party_names(db, [po.third_party_id for po in items if po.third_party_id])
    frameworks = {}
    for po in items:
        if po.contract_request_id and po.contract_request_id not in frameworks:
            frameworks[po.contract_request_id] = await cr_repo.get_by_id(po.contract_request_id)

    return PurchaseOrderListResponse(
        items=[
            _po_to_response(
                po,
                third_party_name=names.get(po.third_party_id),
                framework=frameworks.get(po.contract_request_id),
            )
            for po in items
        ],
        total=total,
        skip=skip,
        limit=limit,
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

    names = await _third_party_names(db, [po.third_party_id] if po.third_party_id else [])
    return _po_to_response(
        po,
        third_party_name=names.get(po.third_party_id),
        framework=await _load_framework(cr_repo, po),
    )


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

    names = await _third_party_names(db, [po.third_party_id] if po.third_party_id else [])
    return _po_to_response(
        po,
        third_party_name=names.get(po.third_party_id),
        framework=await _load_framework(cr_repo, po),
    )


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
        details={"kind": "purchase_order", "reference": saved.reference},
    )

    names = await _third_party_names(db, [saved.third_party_id] if saved.third_party_id else [])
    return _po_to_response(
        saved,
        third_party_name=names.get(saved.third_party_id),
        framework=await _load_framework(cr_repo, saved),
    )


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
    return {"url": url, "reference": po.reference, "signed": signed}


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
    framework_signed = bool(framework and framework.status in _SIGNED_FRAMEWORK_STATUSES)

    try:
        po.send_for_signature(framework_contract_signed=framework_signed)
    except FrameworkContractNotSignedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidPurchaseOrderStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    saved = await po_repo.save(po)
    await db.commit()

    logger.info(
        "purchase_order_sent_for_signature",
        purchase_order_id=str(saved.id),
        reference=saved.reference,
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

    s3_key = f"purchase-orders/{po.reference}/signe.{extension}"
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
        details={"kind": "purchase_order", "reference": saved.reference},
    )
    return await _respond(db, cr_repo, saved)


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
            "reference": po.reference,
            "boond_contract_id": po.boond_contract_id,
            "boond_purchase_order_id": po.boond_purchase_order_id,
        },
    )
    return await _respond(db, cr_repo, po)
