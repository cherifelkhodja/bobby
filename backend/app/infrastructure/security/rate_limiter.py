"""
Rate limiting infrastructure.

Provides token bucket rate limiting with in-memory and Redis backends.
"""

import time
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from threading import Lock
from typing import Any

from fastapi import HTTPException, Request, status


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: int,
        window: int,
        retry_after: int,
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {limit} requests per {window} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
        self.limit = limit
        self.window = window
        self.retry_after = retry_after


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    reset_at: float
    limit: int


class RateLimiter(ABC):
    """
    Abstract base class for rate limiters.

    Implements the token bucket algorithm for rate limiting.
    """

    @abstractmethod
    async def check(self, key: str, limit: int, window: int) -> RateLimitResult:
        """
        Check if a request is allowed under the rate limit.

        Args:
            key: Unique identifier for the client (e.g., IP, user ID)
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            RateLimitResult with allowed status and metadata
        """
        pass

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset the rate limit for a key."""
        pass


class InMemoryRateLimiter(RateLimiter):
    """
    In-memory rate limiter using sliding window algorithm.

    Suitable for single-instance deployments.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    async def check(self, key: str, limit: int, window: int) -> RateLimitResult:
        """Check rate limit using sliding window."""
        now = time.time()
        window_start = now - window

        with self._lock:
            # Remove old requests outside the window
            self._requests[key] = [ts for ts in self._requests[key] if ts > window_start]

            current_count = len(self._requests[key])

            if current_count >= limit:
                # Rate limit exceeded
                oldest = min(self._requests[key]) if self._requests[key] else now
                reset_at = oldest + window
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    limit=limit,
                )

            # Allow request and record timestamp
            self._requests[key].append(now)
            return RateLimitResult(
                allowed=True,
                remaining=limit - current_count - 1,
                reset_at=now + window,
                limit=limit,
            )

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        with self._lock:
            self._requests.pop(key, None)


class RedisRateLimiter(RateLimiter):
    """
    Redis-based rate limiter using sliding window algorithm.

    Suitable for distributed deployments.
    """

    def __init__(self, redis_client: Any):
        self._redis = redis_client

    async def check(self, key: str, limit: int, window: int) -> RateLimitResult:
        """Check rate limit using Redis sorted sets."""
        now = time.time()
        window_start = now - window
        redis_key = f"ratelimit:{key}"

        # Use a pipeline for atomic operations
        pipe = self._redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, window_start)

        # Count current entries
        pipe.zcard(redis_key)

        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]

        if current_count >= limit:
            # Get oldest entry to calculate reset time
            oldest = await self._redis.zrange(redis_key, 0, 0, withscores=True)
            reset_at = oldest[0][1] + window if oldest else now + window

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                limit=limit,
            )

        # Add new entry and set expiry
        pipe = self._redis.pipeline()
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, window)
        await pipe.execute()

        return RateLimitResult(
            allowed=True,
            remaining=limit - current_count - 1,
            reset_at=now + window,
            limit=limit,
        )

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        await self._redis.delete(f"ratelimit:{key}")


# Default in-memory rate limiter
_default_limiter = InMemoryRateLimiter()


def rate_limit(
    limit: int = 100,
    window: int = 60,
    key_func: Callable[[Request], str] | None = None,
    limiter: RateLimiter | None = None,
):
    """
    Rate limiting decorator for FastAPI endpoints.

    Args:
        limit: Maximum requests allowed in the window
        window: Time window in seconds
        key_func: Function to extract rate limit key from request
        limiter: RateLimiter instance (defaults to in-memory)

    Example:
        @router.get("/api/resource")
        @rate_limit(limit=10, window=60)
        async def get_resource(request: Request):
            return {"data": "value"}
    """

    def get_default_key(request: Request) -> str:
        """Default key function using client IP."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    actual_key_func = key_func or get_default_key
    actual_limiter = limiter or _default_limiter

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args or kwargs
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                # Can't rate limit without request
                return await func(*args, **kwargs)

            # Get rate limit key
            key = actual_key_func(request)

            # Check rate limit
            result = await actual_limiter.check(key, limit, window)

            if not result.allowed:
                retry_after = int(result.reset_at - time.time())
                raise RateLimitExceeded(
                    limit=limit,
                    window=window,
                    retry_after=max(1, retry_after),
                )

            # Add rate limit headers to response
            response = await func(*args, **kwargs)

            # Note: Headers would need to be added via middleware
            # for proper response header injection

            return response

        return wrapper

    return decorator
