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
    get_batch_storage,
)
from app.quotation_generator.infrastructure.adapters import RedisStorageAdapter
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
    UpdateContactRequest,
    UpdateContactResponse,
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
            user_id=current_user,  # AdminUser is already a UUID
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
    batches = await use_case.execute(current_user, limit)  # AdminUser is already a UUID
    return UserBatchesResponse(batches=batches)


@router.get(
    "/batches/{batch_id}/download",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF file with merged quotations (BoondManager + Template)",
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
    """Download generated quotations as PDF.

    Returns a single PDF file containing all quotations:
    - BoondManager quotation PDF
    - Filled template PDF
    All merged together.
    """
    try:
        pdf_path = await use_case.execute(batch_id)

        return FileResponse(
            path=pdf_path,
            filename=pdf_path.name,
            media_type="application/pdf",
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


@router.get(
    "/batches/{batch_id}/download/zip",
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "ZIP archive with individual quotation PDFs",
        },
        404: {"model": ErrorResponse, "description": "Batch not found"},
        409: {"model": ErrorResponse, "description": "Download not ready"},
    },
)
async def download_batch_zip(
    batch_id: UUID,
    current_user: AdminUser,
    use_case: DownloadBatchUseCase = Depends(get_download_batch_use_case),
) -> FileResponse:
    """Download all quotations as a ZIP archive.

    Returns a ZIP file containing individual PDF files for each quotation.
    """
    try:
        zip_path = await use_case.execute_zip(batch_id)

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


@router.get(
    "/batches/{batch_id}/quotations/{row_index}/download",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Individual quotation PDF (BoondManager + Template)",
        },
        404: {"model": ErrorResponse, "description": "Batch or quotation not found"},
        409: {"model": ErrorResponse, "description": "Download not ready"},
    },
)
async def download_individual_quotation(
    batch_id: UUID,
    row_index: int,
    current_user: AdminUser,
    use_case: DownloadBatchUseCase = Depends(get_download_batch_use_case),
) -> FileResponse:
    """Download an individual quotation PDF.

    Returns the merged PDF for a specific quotation (BoondManager quotation + filled template).
    """
    try:
        pdf_path = await use_case.execute_individual(batch_id, row_index)

        return FileResponse(
            path=pdf_path,
            filename=pdf_path.name,
            media_type="application/pdf",
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

# SIMPLIFIED CSV format - IDs are auto-fetched from BoondManager via firstName/lastName
# max_price is auto-filled for 124-Data domain based on activity and complexity
EXAMPLE_CSV_CONTENT = """firstName;lastName;po_start_date;po_end_date;amount_ht_unit;total_uo;C22_domain;C22_activity;complexity;max_price;sow_reference;object_of_need;additional_comments
Raphael;COLLARD;2026-01-01;2026-03-31;725;63;124-Data;9-Data Engineer  - Talend (ETL);Complex;;Talend Technical Expert;Talend Technical Expert;
Jean;DUPONT;2026-02-01;2026-04-30;650;60;124-Data;1-Data Analyst;Medium;;Data Analysis Q1;Analyse de données;
Pierre;DURAND;2026-03-01;2026-05-31;690;55;124-Data;2-Data Architect;Complex;;Architecture Data;Conception architecture data;
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


@router.patch(
    "/batches/{batch_id}/quotations/{row_index}/contact",
    response_model=UpdateContactResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Batch or quotation not found"},
    },
)
async def update_quotation_contact(
    batch_id: UUID,
    row_index: int,
    request: UpdateContactRequest,
    current_user: AdminUser,
    batch_storage: RedisStorageAdapter = Depends(get_batch_storage),
) -> UpdateContactResponse:
    """Update the contact for a specific quotation in a batch.

    This allows changing the contact before generating quotations.
    """
    try:
        # Get batch from storage
        batch = await batch_storage.get_batch(batch_id)
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found",
            )

        # Find quotation by row_index
        quotation = None
        for q in batch.quotations:
            if q.row_index == row_index:
                quotation = q
                break

        if not quotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quotation with row_index {row_index} not found in batch",
            )

        # Update contact
        quotation.contact_id = request.contact_id
        quotation.contact_name = request.contact_name

        # Save batch back to storage
        await batch_storage.save_batch(batch, ttl_seconds=3600)

        logger.info(
            f"Updated contact for batch {batch_id}, quotation {row_index}: "
            f"{request.contact_id} ({request.contact_name})"
        )

        return UpdateContactResponse(
            success=True,
            contact_id=request.contact_id,
            contact_name=request.contact_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating contact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update contact: {str(e)}",
        )


@router.delete(
    "/batches/{batch_id}/quotations/{row_index}",
    response_model=PreviewResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Batch or quotation not found"},
    },
)
async def delete_quotation(
    batch_id: UUID,
    row_index: int,
    current_user: AdminUser,
    batch_storage: RedisStorageAdapter = Depends(get_batch_storage),
) -> PreviewResponse:
    """Delete a quotation from the batch.

    This removes a quotation before generation. Returns updated preview data.
    """
    try:
        # Get batch from storage
        batch = await batch_storage.get_batch(batch_id)
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found",
            )

        # Find and remove quotation by row_index
        original_count = len(batch.quotations)
        batch.quotations = [q for q in batch.quotations if q.row_index != row_index]

        if len(batch.quotations) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quotation with row_index {row_index} not found in batch",
            )

        # Reindex remaining quotations
        for i, q in enumerate(batch.quotations):
            q.row_index = i

        # Save batch back to storage
        await batch_storage.save_batch(batch, ttl_seconds=3600)

        logger.info(f"Deleted quotation {row_index} from batch {batch_id}")

        # Return updated preview
        preview_data = batch.to_preview_dict()
        valid_count = sum(1 for q in batch.quotations if q.is_valid)
        invalid_count = len(batch.quotations) - valid_count

        return PreviewResponse(
            batch_id=str(batch.id),
            quotations=preview_data["quotations"],
            valid_count=valid_count,
            invalid_count=invalid_count,
            total_quotations=len(batch.quotations),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting quotation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete quotation: {str(e)}",
        )
