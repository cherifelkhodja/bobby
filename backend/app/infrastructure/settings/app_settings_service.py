"""Application settings service for runtime configuration."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import AppSettingModel


logger = logging.getLogger(__name__)


# Default settings values
DEFAULT_SETTINGS = {
    "gemini_model": "gemini-2.0-flash",
    "gemini_model_cv": "gemini-2.0-flash",
}

# Available Gemini models
AVAILABLE_GEMINI_MODELS = [
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "description": "Fast and efficient"},
    {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite", "description": "Lighter version, faster"},
    {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "description": "Previous generation, stable"},
    {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "description": "More capable, slower"},
]


class AppSettingsService:
    """Service for managing application runtime settings."""

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the settings service.

        Args:
            db_session: Database session.
        """
        self.db_session = db_session
        self._cache: dict[str, str] = {}

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key.

        Args:
            key: The setting key.
            default: Default value if not found.

        Returns:
            The setting value or default.
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        try:
            result = await self.db_session.execute(
                select(AppSettingModel).where(AppSettingModel.key == key)
            )
            setting = result.scalar_one_or_none()

            if setting and setting.value:
                self._cache[key] = setting.value
                return setting.value
        except Exception as e:
            logger.warning(f"Could not fetch setting '{key}': {e}")

        # Return default from our defaults or the provided default
        return DEFAULT_SETTINGS.get(key, default)

    async def set(
        self,
        key: str,
        value: str,
        updated_by: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> bool:
        """Set a setting value.

        Args:
            key: The setting key.
            value: The value to set.
            updated_by: User ID who made the change.
            description: Optional description for the setting.

        Returns:
            True if successful.
        """
        try:
            result = await self.db_session.execute(
                select(AppSettingModel).where(AppSettingModel.key == key)
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value = value
                setting.updated_by = updated_by
                if description:
                    setting.description = description
            else:
                setting = AppSettingModel(
                    key=key,
                    value=value,
                    description=description,
                    updated_by=updated_by,
                )
                self.db_session.add(setting)

            await self.db_session.commit()

            # Update cache
            self._cache[key] = value
            logger.info(f"Setting '{key}' updated to '{value}'")
            return True

        except Exception as e:
            logger.error(f"Could not set setting '{key}': {e}")
            await self.db_session.rollback()
            return False

    async def get_all(self) -> list[dict]:
        """Get all settings.

        Returns:
            List of all settings with key, value, description.
        """
        try:
            result = await self.db_session.execute(
                select(AppSettingModel).order_by(AppSettingModel.key)
            )
            settings = result.scalars().all()

            return [
                {
                    "key": s.key,
                    "value": s.value,
                    "description": s.description,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in settings
            ]
        except Exception as e:
            logger.warning(f"Could not fetch all settings: {e}")
            # Return defaults if DB fails
            return [
                {"key": k, "value": v, "description": None, "updated_at": None}
                for k, v in DEFAULT_SETTINGS.items()
            ]

    async def get_gemini_model(self) -> str:
        """Get the Gemini model to use for anonymization.

        Returns:
            The Gemini model ID.
        """
        return await self.get("gemini_model", "gemini-2.0-flash") or "gemini-2.0-flash"

    async def get_gemini_model_cv(self) -> str:
        """Get the Gemini model to use for CV transformation.

        Returns:
            The Gemini model ID.
        """
        return await self.get("gemini_model_cv", "gemini-2.0-flash") or "gemini-2.0-flash"

    def clear_cache(self) -> None:
        """Clear the settings cache."""
        self._cache.clear()
