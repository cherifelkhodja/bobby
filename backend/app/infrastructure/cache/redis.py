"""Redis cache implementation."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from redis.asyncio import Redis

from app.config import settings


async def get_redis_client() -> AsyncGenerator[Redis, None]:
    """Get Redis client."""
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


class CacheService:
    """Cache service using Redis."""

    OPPORTUNITIES_KEY = "opportunities"
    OPPORTUNITIES_TTL = 300  # 5 minutes

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        return await self.redis.get(key)

    async def get_json(self, key: str) -> Any | None:
        """Get JSON value from cache."""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> bool:
        """Set value in cache with TTL."""
        await self.redis.set(key, value, ex=ttl_seconds)
        return True

    async def set_json(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set JSON value in cache with TTL."""
        await self.redis.set(key, json.dumps(value), ex=ttl_seconds)
        return True

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        result = await self.redis.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return await self.redis.exists(key) > 0

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            return await self.redis.delete(*keys)
        return 0

    # Opportunity caching helpers
    async def get_opportunities(self) -> list[dict[str, Any]] | None:
        """Get cached opportunities."""
        return await self.get_json(self.OPPORTUNITIES_KEY)

    async def set_opportunities(self, opportunities: list[dict[str, Any]]) -> bool:
        """Cache opportunities."""
        return await self.set_json(self.OPPORTUNITIES_KEY, opportunities, self.OPPORTUNITIES_TTL)

    async def invalidate_opportunities(self) -> bool:
        """Invalidate opportunities cache."""
        return await self.delete(self.OPPORTUNITIES_KEY)

    # App settings helpers (no TTL - persistent)
    SETTINGS_PREFIX = "app_setting:"
    GEMINI_MODEL_KEY = "gemini_model"
    DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"

    async def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Get app setting from cache (persistent, no TTL)."""
        value = await self.redis.get(f"{self.SETTINGS_PREFIX}{key}")
        return value if value is not None else default

    async def set_setting(self, key: str, value: str) -> bool:
        """Set app setting in cache (persistent, no TTL)."""
        await self.redis.set(f"{self.SETTINGS_PREFIX}{key}", value)
        return True

    async def get_gemini_model(self) -> str:
        """Get configured Gemini model."""
        return (
            await self.get_setting(self.GEMINI_MODEL_KEY, self.DEFAULT_GEMINI_MODEL)
            or self.DEFAULT_GEMINI_MODEL
        )

    async def set_gemini_model(self, model: str) -> bool:
        """Set Gemini model."""
        return await self.set_setting(self.GEMINI_MODEL_KEY, model)
