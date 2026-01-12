"""Redis cache implementation."""

import json
from typing import Any, AsyncGenerator, Optional

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

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        return await self.redis.get(key)

    async def get_json(self, key: str) -> Optional[Any]:
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
    async def get_opportunities(self) -> Optional[list[dict[str, Any]]]:
        """Get cached opportunities."""
        return await self.get_json(self.OPPORTUNITIES_KEY)

    async def set_opportunities(self, opportunities: list[dict[str, Any]]) -> bool:
        """Cache opportunities."""
        return await self.set_json(
            self.OPPORTUNITIES_KEY, opportunities, self.OPPORTUNITIES_TTL
        )

    async def invalidate_opportunities(self) -> bool:
        """Invalidate opportunities cache."""
        return await self.delete(self.OPPORTUNITIES_KEY)
