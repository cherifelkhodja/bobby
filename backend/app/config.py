"""Application configuration using Pydantic Settings."""

import logging
import os
from functools import lru_cache
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Environment
    ENV: Literal["dev", "test", "prod"] = "dev"

    # AWS Secrets Manager (optional - set AWS_SECRETS_ENABLED=true to use)
    AWS_SECRETS_ENABLED: bool = False
    AWS_SECRETS_NAME: str = "esn-cooptation/prod"
    AWS_SECRETS_REGION: str = "eu-west-3"

    # Track if secrets were loaded from AWS (set at runtime)
    _secrets_source: str = "environment"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cooptation:cooptation@postgres:5432/cooptation"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    JWT_SECRET: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # BoondManager
    BOOND_API_URL: str = "https://ui.boondmanager.com/api"
    BOOND_USERNAME: str = ""
    BOOND_PASSWORD: str = ""
    BOOND_CANDIDATE_STATE_ID: int = 1
    BOOND_POSITIONING_STATE_ID: int = 1

    # Email
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@geminiconsulting.fr"
    RESEND_API_KEY: str = ""  # If set, uses Resend instead of SMTP

    # Frontend URL (for email links and CORS)
    FRONTEND_URL: str = "http://localhost:3012"

    # Additional CORS origins (comma-separated, optional)
    CORS_ORIGINS: str = ""

    # Admin seed (dev only - set via environment variables if needed)
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    # Google Gemini API
    GEMINI_API_KEY: str = ""

    # Turnover-IT API
    TURNOVERIT_API_KEY: str = ""
    TURNOVERIT_API_URL: str = "https://api.turnover-it.com/jobconnect/v2"

    # S3/MinIO Storage (Scaleway Object Storage)
    S3_ENDPOINT_URL: str = ""  # e.g., https://s3.fr-par.scw.cloud (empty for AWS S3)
    S3_BUCKET_NAME: str = "esn-cooptation-cvs"
    S3_REGION: str = "fr-par"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # Feature flags
    FEATURE_MAGIC_LINK: bool = True
    FEATURE_EMAIL_NOTIFICATIONS: bool = True
    FEATURE_BOOND_SYNC: bool = True

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENV == "prod"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENV == "dev"

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode."""
        return self.ENV == "test"

    @property
    def async_database_url(self) -> str:
        """Get DATABASE_URL converted to asyncpg format."""
        url = self.DATABASE_URL
        # Railway provides postgresql:// but asyncpg needs postgresql+asyncpg://
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def cors_origins(self) -> list[str]:
        """Get list of allowed CORS origins."""
        origins = [self.FRONTEND_URL]

        # Add localhost for development
        if not self.is_production:
            origins.extend([
                "http://localhost:3012",
                "http://127.0.0.1:3012",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ])

        # Add additional origins from CORS_ORIGINS
        if self.CORS_ORIGINS:
            origins.extend([
                origin.strip()
                for origin in self.CORS_ORIGINS.split(",")
                if origin.strip()
            ])

        return list(set(origins))  # Remove duplicates


def _load_aws_secrets() -> dict[str, Any]:
    """Load secrets from AWS Secrets Manager if enabled.

    Returns:
        Dictionary of secrets, or empty dict if not enabled or failed.
    """
    # Check if AWS Secrets Manager is enabled via environment variable
    if not os.getenv("AWS_SECRETS_ENABLED", "").lower() in ("true", "1", "yes"):
        return {}

    try:
        from app.infrastructure.secrets import load_secrets_from_aws

        secret_name = os.getenv("AWS_SECRETS_NAME", "esn-cooptation/prod")
        region = os.getenv("AWS_SECRETS_REGION", "eu-west-3")

        # Use S3 credentials for AWS Secrets Manager if available
        access_key = os.getenv("S3_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("S3_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")

        secrets = load_secrets_from_aws(
            region_name=region,
            secret_name=secret_name,
            access_key_id=access_key,
            secret_access_key=secret_key,
        )

        if secrets:
            logger.info(f"Loaded {len(secrets)} secrets from AWS Secrets Manager")
        return secrets

    except ImportError:
        logger.warning("boto3 not installed, cannot use AWS Secrets Manager")
        return {}
    except Exception as e:
        logger.warning(f"Failed to load AWS secrets: {e}")
        return {}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance with AWS secrets if enabled."""
    # Load AWS secrets first
    aws_secrets = _load_aws_secrets()

    if aws_secrets:
        # Map AWS secret keys to environment variables
        # AWS Secrets Manager keys should match our env var names
        secret_mappings = {
            "GEMINI_API_KEY": "GEMINI_API_KEY",
            "TURNOVERIT_API_KEY": "TURNOVERIT_API_KEY",
            "RESEND_API_KEY": "RESEND_API_KEY",
            "BOOND_USERNAME": "BOOND_USERNAME",
            "BOOND_PASSWORD": "BOOND_PASSWORD",
            "S3_ACCESS_KEY": "S3_ACCESS_KEY",
            "S3_SECRET_KEY": "S3_SECRET_KEY",
            "JWT_SECRET": "JWT_SECRET",
        }

        # Set environment variables from AWS secrets (don't override existing)
        for aws_key, env_key in secret_mappings.items():
            if aws_key in aws_secrets and not os.getenv(env_key):
                os.environ[env_key] = str(aws_secrets[aws_key])
                logger.debug(f"Set {env_key} from AWS Secrets Manager")

        # Create settings with AWS secrets loaded
        instance = Settings()
        instance._secrets_source = "aws"
        return instance

    return Settings()


settings = get_settings()
