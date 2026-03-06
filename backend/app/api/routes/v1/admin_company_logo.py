"""Admin endpoints for contract company logo management."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser
from app.contract_management.infrastructure.models import ContractCompanyModel
from app.dependencies import get_db

router = APIRouter()


@router.post(
    "/contract-companies/{company_id}/logo",
    summary="Upload company logo",
)
async def upload_company_logo(
    company_id: UUID,
    admin_id: AdminUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(..., description="Logo image (PNG, JPEG, SVG, max 2 Mo)"),
):
    """Upload or replace the logo for a company. Admin only."""
    from datetime import datetime as _dt

    from app.config import get_settings as _get_settings
    from app.infrastructure.storage.s3_client import S3StorageClient

    allowed = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Format non supporté. Utilisez PNG, JPEG, SVG ou WebP.",
        )
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo trop volumineux (max 2 Mo).")

    result = await db.execute(select(ContractCompanyModel).where(ContractCompanyModel.id == company_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Société introuvable")

    settings = _get_settings()
    s3 = S3StorageClient(settings)

    if m.logo_s3_key:
        await s3.delete_file(m.logo_s3_key)

    ext = (file.filename or "logo").rsplit(".", 1)[-1].lower() if file.filename else "png"
    s3_key = f"contract-companies/{company_id}/logo.{ext}"
    await s3.upload_file(key=s3_key, content=content, content_type=file.content_type or "image/png")

    m.logo_s3_key = s3_key
    m.updated_at = _dt.utcnow()
    await db.commit()
    return {"logo_s3_key": s3_key}


@router.get(
    "/contract-companies/{company_id}/logo",
    summary="Get company logo presigned URL",
)
async def get_company_logo_url(
    company_id: UUID,
    admin_id: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Return a short-lived presigned URL to view the company logo. Admin only."""
    from app.config import get_settings as _get_settings
    from app.infrastructure.storage.s3_client import S3StorageClient

    result = await db.execute(select(ContractCompanyModel).where(ContractCompanyModel.id == company_id))
    m = result.scalar_one_or_none()
    if not m or not m.logo_s3_key:
        raise HTTPException(status_code=404, detail="Aucun logo pour cette société")

    settings = _get_settings()
    s3 = S3StorageClient(settings)
    url = await s3.get_presigned_url(m.logo_s3_key, expires_in=300)
    return {"url": url}


@router.delete(
    "/contract-companies/{company_id}/logo",
    status_code=204,
    summary="Delete company logo",
)
async def delete_company_logo(
    company_id: UUID,
    admin_id: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Remove the logo for a company. Admin only."""
    from datetime import datetime as _dt

    from app.config import get_settings as _get_settings
    from app.infrastructure.storage.s3_client import S3StorageClient

    result = await db.execute(select(ContractCompanyModel).where(ContractCompanyModel.id == company_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Société introuvable")
    if m.logo_s3_key:
        settings = _get_settings()
        s3 = S3StorageClient(settings)
        await s3.delete_file(m.logo_s3_key)
        m.logo_s3_key = None
        m.updated_at = _dt.utcnow()
        await db.commit()
