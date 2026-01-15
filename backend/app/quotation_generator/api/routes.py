"""API routes for quotation generator."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies import AdminUser
from app.quotation_generator.api.dependencies import (
    get_preview_batch_use_case,
    get_start_generation_use_case,
    get_progress_use_case,
    get_batch_details_use_case,
    get_list_user_batches_use_case,
    get_download_batch_use_case,
    get_upload_template_use_case,
    get_list_templates_use_case,
)
from app.quotation_generator.api.schemas import (
    PreviewBatchResponse,
    StartGenerationRequest,
    StartGenerationResponse,
    BatchProgressResponse,
    BatchDetailsResponse,
    DownloadInfoResponse,
    TemplateListResponse,
    UploadTemplateResponse,
    UserBatchesResponse,
    ErrorResponse,
)
from app.quotation_generator.application.use_cases import (
    PreviewBatchUseCase,
    DownloadBatchUseCase,
    UploadTemplateUseCase,
    ListTemplatesUseCase,
)
from app.quotation_generator.application.use_cases.generate_batch import (
    StartGenerationUseCase,
)
from app.quotation_generator.application.use_cases.get_progress import (
    GetBatchProgressUseCase,
    GetBatchDetailsUseCase,
    ListUserBatchesUseCase,
)
from app.quotation_generator.domain.exceptions import (
    BatchNotFoundError,
    CSVParsingError,
    DownloadNotReadyError,
    MissingColumnsError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotation-generator", tags=["quotation-generator"])


@router.post(
    "/preview",
    response_model=PreviewBatchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid CSV file"},
        422: {"model": ErrorResponse, "description": "Missing required columns"},
    },
)
async def preview_batch(
    current_user: AdminUser,
    file: UploadFile = File(..., description="CSV file with quotation data"),
    use_case: PreviewBatchUseCase = Depends(get_preview_batch_use_case),
) -> PreviewBatchResponse:
    """Upload CSV and preview quotations.

    This endpoint:
    1. Parses the uploaded CSV file
    2. Validates all quotations
    3. Returns a preview with validation results
    4. Stores the batch for later confirmation

    The batch is stored for 1 hour. After that, you need to upload again.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    try:
        result = await use_case.execute(
            file=file.file,
            user_id=current_user.id,
        )

        return PreviewBatchResponse(
            batch_id=result.batch_id,
            total_quotations=result.total_quotations,
            valid_count=result.valid_count,
            invalid_count=result.invalid_count,
            quotations=result.quotations,
            validation_errors={str(k): v for k, v in result.validation_errors.items()},
        )

    except MissingColumnsError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )
    except CSVParsingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post(
    "/generate",
    response_model=StartGenerationResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Batch not found"},
    },
)
async def start_generation(
    current_user: AdminUser,
    request: StartGenerationRequest,
    use_case: StartGenerationUseCase = Depends(get_start_generation_use_case),
) -> StartGenerationResponse:
    """Start batch generation.

    This endpoint starts the asynchronous generation process:
    1. Creates quotations in BoondManager
    2. Fills Excel templates
    3. Converts to PDF
    4. Creates ZIP archive

    Use the progress endpoint to monitor status.
    """
    try:
        result = await use_case.execute(
            batch_id=request.batch_id,
            template_name=request.template_name,
        )

        return StartGenerationResponse(
            batch_id=request.batch_id,
            status=result["status"],
            total_quotations=result["total_quotations"],
        )

    except BatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "/batches/{batch_id}/progress",
    response_model=BatchProgressResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Batch not found"},
    },
)
async def get_batch_progress(
    batch_id: UUID,
    current_user: AdminUser,
    use_case: GetBatchProgressUseCase = Depends(get_progress_use_case),
) -> BatchProgressResponse:
    """Get batch generation progress.

    Returns current status and progress percentage.
    """
    try:
        result = await use_case.execute(batch_id)
        return BatchProgressResponse(**result)

    except BatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "/batches/{batch_id}",
    response_model=BatchDetailsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Batch not found"},
    },
)
async def get_batch_details(
    batch_id: UUID,
    current_user: AdminUser,
    use_case: GetBatchDetailsUseCase = Depends(get_batch_details_use_case),
) -> BatchDetailsResponse:
    """Get detailed batch information.

    Returns full batch details including individual quotation statuses.
    """
    try:
        result = await use_case.execute(batch_id)
        return BatchDetailsResponse(**result)

    except BatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "/batches",
    response_model=UserBatchesResponse,
)
async def list_user_batches(
    current_user: AdminUser,
    limit: int = 10,
    use_case: ListUserBatchesUseCase = Depends(get_list_user_batches_use_case),
) -> UserBatchesResponse:
    """List recent batches for the current user."""
    batches = await use_case.execute(current_user.id, limit)
    return UserBatchesResponse(batches=batches)


@router.get(
    "/batches/{batch_id}/download",
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "ZIP file with generated quotations",
        },
        404: {"model": ErrorResponse, "description": "Batch not found"},
        409: {"model": ErrorResponse, "description": "Download not ready"},
    },
)
async def download_batch(
    batch_id: UUID,
    current_user: AdminUser,
    use_case: DownloadBatchUseCase = Depends(get_download_batch_use_case),
) -> FileResponse:
    """Download generated quotations as ZIP.

    Returns a ZIP file containing all generated PDF quotations.
    """
    try:
        zip_path = await use_case.execute(batch_id)

        return FileResponse(
            path=zip_path,
            filename=zip_path.name,
            media_type="application/zip",
        )

    except BatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except DownloadNotReadyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


# Template management endpoints


@router.get(
    "/templates",
    response_model=TemplateListResponse,
)
async def list_templates(
    current_user: AdminUser,
    use_case: ListTemplatesUseCase = Depends(get_list_templates_use_case),
) -> TemplateListResponse:
    """List available quotation templates."""
    templates = await use_case.execute()
    return TemplateListResponse(templates=templates)


@router.post(
    "/templates/{name}",
    response_model=UploadTemplateResponse,
)
async def upload_template(
    name: str,
    current_user: AdminUser,
    file: UploadFile = File(..., description="Excel template file (.xlsx)"),
    display_name: str = Form(..., description="Human-readable template name"),
    description: str = Form(None, description="Template description"),
    validate_variables: bool = Form(True, description="Validate required variables"),
    use_case: UploadTemplateUseCase = Depends(get_upload_template_use_case),
) -> UploadTemplateResponse:
    """Upload or update a quotation template.

    The template should be an Excel file (.xlsx) with placeholders
    in the format {{ variable_name }}.
    """
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx)",
        )

    content = await file.read()

    result = await use_case.execute(
        name=name,
        content=content,
        display_name=display_name,
        description=description,
        validate_variables=validate_variables,
    )

    return UploadTemplateResponse(**result)


# Example CSV endpoint

# Example CSV with region column - max_price is auto-filled for 124-DATA domain
EXAMPLE_CSV_CONTENT = """resource_id,resource_name,trigramme,opportunity_id,company_id,company_name,contact_id,contact_name,start_date,end_date,tjm,quantity,sow_reference,object_of_need,c22_domain,c22_activity,region,complexity,max_price,start_project,comments
12345,Jean DUPONT,JDU,98765,11111,THALES SIX GTS,22222,Marie MARTIN,2025-02-01,2025-04-30,550,60,SOW-2025-001,Développement application web,124-DATA,Data Analyst,IDF,Medium,,2025-02-01,Max GFA auto-calculé depuis grille
12346,Pierre DURAND,PDU,98766,11111,THALES SIX GTS,22222,Marie MARTIN,2025-03-01,2025-05-31,600,65,SOW-2025-002,Architecture microservices,124-DATA,AI/ML Engineer,Région,Expert,,2025-03-01,
12347,Sophie MARTIN,SMA,98767,11111,THALES SIX GTS,22222,Marie MARTIN,2025-04-01,2025-06-30,500,45,SOW-2025-003,Support technique,Autre,Support,IDF,Simple,600,2025-04-01,Domaine hors grille - max_price requis
"""


@router.get(
    "/example-csv",
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Example CSV file",
        },
    },
)
async def download_example_csv(
    current_user: AdminUser,
) -> FileResponse:
    """Download an example CSV file.

    Returns a CSV file with the expected format and example data.
    """
    import tempfile
    import os

    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
            f.write(EXAMPLE_CSV_CONTENT.strip())

        return FileResponse(
            path=path,
            filename="exemple_devis_thales.csv",
            media_type="text/csv",
            background=None,  # Don't delete file before sending
        )
    except Exception:
        os.unlink(path)
        raise
