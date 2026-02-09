"""S3/MinIO storage client for CV file storage.

Compatible with:
- AWS S3
- Scaleway Object Storage
- MinIO
- Any S3-compatible storage
"""

import logging

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import Settings
from app.domain.exceptions import S3StorageError

logger = logging.getLogger(__name__)


class S3StorageClient:
    """Async S3-compatible storage client.

    This client handles file upload, download, and URL generation
    for storing CVs in S3-compatible object storage.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize S3 storage client.

        Args:
            settings: Application settings containing S3 credentials.
        """
        self.endpoint_url = settings.S3_ENDPOINT_URL or None  # Empty string → None
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY

        self._session = aioboto3.Session()
        self._config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # Required for some S3-compatible services
        )

    def _is_configured(self) -> bool:
        """Check if client is properly configured."""
        return bool(self.access_key and self.secret_key and self.bucket_name)

    def _get_client_kwargs(self) -> dict:
        """Get kwargs for S3 client creation."""
        kwargs = {
            "region_name": self.region,
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "config": self._config,
        }
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        return kwargs

    async def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Upload a file to S3 storage.

        Args:
            key: Storage key/path for the file (e.g., "applications/uuid/cv.pdf").
            content: File content as bytes.
            content_type: MIME type of the file.

        Returns:
            The storage key of the uploaded file.

        Raises:
            S3StorageError: If upload fails or client not configured.
        """
        if not self._is_configured():
            raise S3StorageError("S3 storage not configured")

        logger.info(f"Uploading file to S3: {key}")

        try:
            async with self._session.client("s3", **self._get_client_kwargs()) as s3:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content,
                    ContentType=content_type,
                )
                logger.info(f"Successfully uploaded file: {key}")
                return key

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"S3 upload failed for {key}: {error_code} - {error_msg}")
            raise S3StorageError(f"Upload échoué: {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error uploading {key}: {e}")
            raise S3StorageError(f"Erreur inattendue: {str(e)}")

    async def download_file(self, key: str) -> bytes:
        """Download a file from S3 storage.

        Args:
            key: Storage key/path of the file.

        Returns:
            File content as bytes.

        Raises:
            S3StorageError: If download fails.
        """
        if not self._is_configured():
            raise S3StorageError("S3 storage not configured")

        logger.info(f"Downloading file from S3: {key}")

        try:
            async with self._session.client("s3", **self._get_client_kwargs()) as s3:
                response = await s3.get_object(
                    Bucket=self.bucket_name,
                    Key=key,
                )
                content = await response["Body"].read()
                logger.info(f"Successfully downloaded file: {key}")
                return content

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                logger.warning(f"File not found in S3: {key}")
                raise S3StorageError("Fichier non trouvé")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"S3 download failed for {key}: {error_code} - {error_msg}")
            raise S3StorageError(f"Téléchargement échoué: {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error downloading {key}: {e}")
            raise S3StorageError(f"Erreur inattendue: {str(e)}")

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for file download.

        Args:
            key: Storage key/path of the file.
            expires_in: URL expiration time in seconds (default 1 hour).

        Returns:
            Presigned URL for direct download.

        Raises:
            S3StorageError: If URL generation fails.
        """
        if not self._is_configured():
            raise S3StorageError("S3 storage not configured")

        try:
            async with self._session.client("s3", **self._get_client_kwargs()) as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": key,
                    },
                    ExpiresIn=expires_in,
                )
                return url

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"Failed to generate presigned URL for {key}: {error_msg}")
            raise S3StorageError(f"Génération URL échouée: {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error generating URL for {key}: {e}")
            raise S3StorageError(f"Erreur inattendue: {str(e)}")

    async def delete_file(self, key: str) -> bool:
        """Delete a file from S3 storage.

        Args:
            key: Storage key/path of the file.

        Returns:
            True if deletion was successful.

        Raises:
            S3StorageError: If deletion fails.
        """
        if not self._is_configured():
            raise S3StorageError("S3 storage not configured")

        logger.info(f"Deleting file from S3: {key}")

        try:
            async with self._session.client("s3", **self._get_client_kwargs()) as s3:
                await s3.delete_object(
                    Bucket=self.bucket_name,
                    Key=key,
                )
                logger.info(f"Successfully deleted file: {key}")
                return True

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"S3 delete failed for {key}: {error_msg}")
            raise S3StorageError(f"Suppression échouée: {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error deleting {key}: {e}")
            raise S3StorageError(f"Erreur inattendue: {str(e)}")

    async def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3 storage.

        Args:
            key: Storage key/path of the file.

        Returns:
            True if file exists.
        """
        if not self._is_configured():
            return False

        try:
            async with self._session.client("s3", **self._get_client_kwargs()) as s3:
                await s3.head_object(
                    Bucket=self.bucket_name,
                    Key=key,
                )
                return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ("404", "NoSuchKey"):
                return False
            logger.warning(f"Error checking file existence {key}: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error checking {key}: {e}")
            return False

    async def health_check(self) -> bool:
        """Check S3 storage availability.

        Returns:
            True if storage is available.
        """
        if not self._is_configured():
            logger.warning("S3 storage not configured")
            return False

        try:
            async with self._session.client("s3", **self._get_client_kwargs()) as s3:
                await s3.head_bucket(Bucket=self.bucket_name)
                return True

        except Exception as e:
            logger.warning(f"S3 health check failed: {e}")
            return False
