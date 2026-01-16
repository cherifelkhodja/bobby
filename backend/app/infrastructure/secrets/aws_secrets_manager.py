"""AWS Secrets Manager integration for secure secrets management.

This module provides a service to fetch and cache secrets from AWS Secrets Manager.
Secrets are loaded at startup and cached in memory for performance.
"""

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSSecretsManager:
    """Service for fetching secrets from AWS Secrets Manager.

    Attributes:
        region_name: AWS region where secrets are stored.
        secret_name: Name of the secret in AWS Secrets Manager.
    """

    def __init__(
        self,
        region_name: str = "eu-west-3",
        secret_name: str = "esn-cooptation/prod",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        """Initialize AWS Secrets Manager client.

        Args:
            region_name: AWS region (default: eu-west-3 Paris).
            secret_name: Name of the secret to fetch.
            access_key_id: Optional AWS access key (uses env/IAM role if not provided).
            secret_access_key: Optional AWS secret key.
        """
        self.region_name = region_name
        self.secret_name = secret_name
        self._secrets_cache: dict[str, Any] | None = None

        # Create client with explicit credentials or default chain
        client_kwargs: dict[str, Any] = {"region_name": region_name}
        if access_key_id and secret_access_key:
            client_kwargs["aws_access_key_id"] = access_key_id
            client_kwargs["aws_secret_access_key"] = secret_access_key

        self._client = boto3.client("secretsmanager", **client_kwargs)

    def get_secrets(self) -> dict[str, Any]:
        """Fetch all secrets from AWS Secrets Manager.

        Returns:
            Dictionary containing all secret key-value pairs.

        Raises:
            ClientError: If unable to fetch secrets from AWS.
        """
        if self._secrets_cache is not None:
            return self._secrets_cache

        try:
            response = self._client.get_secret_value(SecretId=self.secret_name)

            # Secrets can be string or binary
            if "SecretString" in response:
                secret_data = response["SecretString"]
                self._secrets_cache = json.loads(secret_data)
            else:
                # Binary secret - decode as JSON
                import base64
                decoded = base64.b64decode(response["SecretBinary"]).decode("utf-8")
                self._secrets_cache = json.loads(decoded)

            logger.info(f"Successfully loaded secrets from AWS Secrets Manager: {self.secret_name}")
            return self._secrets_cache or {}

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                logger.warning(f"Secret {self.secret_name} not found in AWS Secrets Manager")
            elif error_code == "AccessDeniedException":
                logger.error(f"Access denied to secret {self.secret_name}")
            else:
                logger.error(f"Error fetching secret: {e}")
            raise

    def get_secret(self, key: str, default: Any = None) -> Any:
        """Get a specific secret value by key.

        Args:
            key: The secret key to retrieve.
            default: Default value if key not found.

        Returns:
            The secret value or default.
        """
        try:
            secrets = self.get_secrets()
            return secrets.get(key, default)
        except ClientError:
            return default

    def clear_cache(self) -> None:
        """Clear the secrets cache to force refresh on next access."""
        self._secrets_cache = None
        logger.info("Secrets cache cleared")


def load_secrets_from_aws(
    region_name: str = "eu-west-3",
    secret_name: str = "esn-cooptation/prod",
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
) -> dict[str, Any]:
    """Convenience function to load secrets from AWS Secrets Manager.

    Args:
        region_name: AWS region.
        secret_name: Name of the secret.
        access_key_id: Optional AWS access key.
        secret_access_key: Optional AWS secret key.

    Returns:
        Dictionary of secrets, or empty dict if loading fails.
    """
    try:
        manager = AWSSecretsManager(
            region_name=region_name,
            secret_name=secret_name,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        return manager.get_secrets()
    except Exception as e:
        logger.warning(f"Failed to load secrets from AWS: {e}. Using environment variables.")
        return {}
