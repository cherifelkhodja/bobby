"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Environment
    ENV: Literal["dev", "test", "prod"] = "dev"

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

    # Frontend URL (for email links)
    FRONTEND_URL: str = "http://localhost:3012"

    # Admin seed (dev only - set via environment variables if needed)
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
