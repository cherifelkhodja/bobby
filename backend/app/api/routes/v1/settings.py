"""Settings API routes for managing external service configurations."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import httpx

from app.api.dependencies import AdminUser
from app.config import settings

router = APIRouter()


class ApiKeyTest(BaseModel):
    """Request model for testing an API key."""
    service: str  # turnoverit, s3, gemini
    api_key: Optional[str] = None
    # S3 specific
    endpoint_url: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    bucket_name: Optional[str] = None
    region: Optional[str] = None


class ApiKeyTestResult(BaseModel):
    """Response model for API key test."""
    success: bool
    message: str
    details: Optional[dict] = None


class ServiceStatus(BaseModel):
    """Status of a configured service."""
    service: str
    configured: bool
    masked_key: Optional[str] = None


class ServicesStatusResponse(BaseModel):
    """Response with all services status."""
    services: list[ServiceStatus]
    secrets_source: str = "environment"  # "environment" or "aws"
    aws_secrets_enabled: bool = False


def mask_key(key: Optional[str]) -> Optional[str]:
    """Mask an API key for display, showing only first 4 and last 4 chars."""
    if not key or len(key) < 12:
        return "****" if key else None
    return f"{key[:4]}...{key[-4:]}"


@router.get("/status", response_model=ServicesStatusResponse)
async def get_services_status(
    current_user_id: AdminUser,
) -> ServicesStatusResponse:
    """Get status of all configured external services."""
    services = [
        ServiceStatus(
            service="turnoverit",
            configured=bool(settings.TURNOVERIT_API_KEY),
            masked_key=mask_key(settings.TURNOVERIT_API_KEY),
        ),
        ServiceStatus(
            service="s3",
            configured=bool(settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY),
            masked_key=mask_key(settings.S3_ACCESS_KEY),
        ),
        ServiceStatus(
            service="gemini",
            configured=bool(settings.GEMINI_API_KEY),
            masked_key=mask_key(settings.GEMINI_API_KEY),
        ),
        ServiceStatus(
            service="boond",
            configured=bool(settings.BOOND_USERNAME and settings.BOOND_PASSWORD),
            masked_key=mask_key(settings.BOOND_USERNAME),
        ),
        ServiceStatus(
            service="resend",
            configured=bool(settings.RESEND_API_KEY),
            masked_key=mask_key(settings.RESEND_API_KEY),
        ),
    ]

    # Get secrets source info
    secrets_source = getattr(settings, "_secrets_source", "environment")
    aws_enabled = settings.AWS_SECRETS_ENABLED

    return ServicesStatusResponse(
        services=services,
        secrets_source=secrets_source,
        aws_secrets_enabled=aws_enabled,
    )


@router.post("/test", response_model=ApiKeyTestResult)
async def test_api_key(
    request: ApiKeyTest,
    current_user_id: AdminUser,
) -> ApiKeyTestResult:
    """Test an API key for a specific service."""

    if request.service == "turnoverit":
        return await _test_turnoverit(request.api_key or settings.TURNOVERIT_API_KEY)

    elif request.service == "s3":
        return await _test_s3(
            endpoint_url=request.endpoint_url or settings.S3_ENDPOINT_URL,
            access_key=request.access_key or settings.S3_ACCESS_KEY,
            secret_key=request.secret_key or settings.S3_SECRET_KEY,
            bucket_name=request.bucket_name or settings.S3_BUCKET_NAME,
            region=request.region or settings.S3_REGION,
        )

    elif request.service == "gemini":
        return await _test_gemini(request.api_key or settings.GEMINI_API_KEY)

    elif request.service == "boond":
        return await _test_boond()

    elif request.service == "resend":
        return await _test_resend(request.api_key or settings.RESEND_API_KEY)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service inconnu: {request.service}",
        )


async def _test_turnoverit(api_key: Optional[str]) -> ApiKeyTestResult:
    """Test Turnover-IT API connection."""
    if not api_key:
        return ApiKeyTestResult(
            success=False,
            message="Clé API Turnover-IT non configurée",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.turnover-it.com/v2/jobs",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                params={"limit": 1},
            )

            if response.status_code == 200:
                return ApiKeyTestResult(
                    success=True,
                    message="Connexion Turnover-IT réussie",
                    details={"status_code": 200},
                )
            elif response.status_code == 401:
                return ApiKeyTestResult(
                    success=False,
                    message="Clé API Turnover-IT invalide",
                    details={"status_code": 401},
                )
            else:
                return ApiKeyTestResult(
                    success=False,
                    message=f"Erreur Turnover-IT: {response.status_code}",
                    details={"status_code": response.status_code},
                )
    except httpx.TimeoutException:
        return ApiKeyTestResult(
            success=False,
            message="Timeout lors de la connexion à Turnover-IT",
        )
    except Exception as e:
        return ApiKeyTestResult(
            success=False,
            message=f"Erreur de connexion: {str(e)}",
        )


async def _test_s3(
    endpoint_url: Optional[str],
    access_key: Optional[str],
    secret_key: Optional[str],
    bucket_name: Optional[str],
    region: Optional[str],
) -> ApiKeyTestResult:
    """Test S3 storage connection."""
    if not all([endpoint_url, access_key, secret_key, bucket_name]):
        return ApiKeyTestResult(
            success=False,
            message="Configuration S3 incomplète",
        )

    try:
        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region or "fr-par",
        ) as s3:
            # Test listing bucket
            await s3.head_bucket(Bucket=bucket_name)

            return ApiKeyTestResult(
                success=True,
                message=f"Connexion S3 réussie (bucket: {bucket_name})",
                details={"bucket": bucket_name, "endpoint": endpoint_url},
            )
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "NoSuchBucket" in error_msg:
            return ApiKeyTestResult(
                success=False,
                message=f"Bucket '{bucket_name}' non trouvé",
            )
        elif "403" in error_msg or "AccessDenied" in error_msg:
            return ApiKeyTestResult(
                success=False,
                message="Accès refusé - vérifiez les credentials S3",
            )
        return ApiKeyTestResult(
            success=False,
            message=f"Erreur S3: {error_msg}",
        )


async def _test_gemini(api_key: Optional[str]) -> ApiKeyTestResult:
    """Test Google Gemini API connection."""
    if not api_key:
        return ApiKeyTestResult(
            success=False,
            message="Clé API Gemini non configurée",
        )

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        # Simple test prompt
        response = model.generate_content("Réponds uniquement 'OK'")

        if response and response.text:
            return ApiKeyTestResult(
                success=True,
                message="Connexion Gemini réussie",
                details={"model": "gemini-2.5-flash-lite"},
            )
        else:
            return ApiKeyTestResult(
                success=False,
                message="Réponse Gemini vide",
            )
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "401" in error_msg:
            return ApiKeyTestResult(
                success=False,
                message="Clé API Gemini invalide",
            )
        return ApiKeyTestResult(
            success=False,
            message=f"Erreur Gemini: {error_msg}",
        )


async def _test_boond() -> ApiKeyTestResult:
    """Test BoondManager API connection."""
    if not settings.BOOND_USERNAME or not settings.BOOND_PASSWORD:
        return ApiKeyTestResult(
            success=False,
            message="Credentials BoondManager non configurés",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.BOOND_API_URL}/application",
                auth=(settings.BOOND_USERNAME, settings.BOOND_PASSWORD),
                headers={"Accept": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                app_name = data.get("data", {}).get("attributes", {}).get("name", "BoondManager")
                return ApiKeyTestResult(
                    success=True,
                    message=f"Connexion BoondManager réussie ({app_name})",
                    details={"app_name": app_name},
                )
            elif response.status_code == 401:
                return ApiKeyTestResult(
                    success=False,
                    message="Credentials BoondManager invalides",
                )
            else:
                return ApiKeyTestResult(
                    success=False,
                    message=f"Erreur BoondManager: {response.status_code}",
                )
    except Exception as e:
        return ApiKeyTestResult(
            success=False,
            message=f"Erreur de connexion: {str(e)}",
        )


async def _test_resend(api_key: Optional[str]) -> ApiKeyTestResult:
    """Test Resend API connection."""
    if not api_key:
        return ApiKeyTestResult(
            success=False,
            message="Clé API Resend non configurée",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.resend.com/domains",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
            )

            if response.status_code == 200:
                data = response.json()
                domains = data.get("data", [])
                domain_count = len(domains)
                return ApiKeyTestResult(
                    success=True,
                    message=f"Connexion Resend réussie ({domain_count} domaine(s))",
                    details={"domain_count": domain_count},
                )
            elif response.status_code == 401:
                return ApiKeyTestResult(
                    success=False,
                    message="Clé API Resend invalide",
                )
            else:
                return ApiKeyTestResult(
                    success=False,
                    message=f"Erreur Resend: {response.status_code}",
                )
    except Exception as e:
        return ApiKeyTestResult(
            success=False,
            message=f"Erreur de connexion: {str(e)}",
        )
