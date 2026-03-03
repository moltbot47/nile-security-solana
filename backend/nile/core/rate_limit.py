"""Rate limiter with Redis backend (production) and in-memory fallback (dev)."""

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory sliding window rate limiter keyed by client IP.

    Used as fallback when Redis is unavailable (development, testing).
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup: float = 0.0

    def _client_key(self, request: Request) -> str:
        """Use the real client IP only — never trust X-Forwarded-For."""
        return request.client.host if request.client else "unknown"

    def _cleanup_stale(self, now: float) -> None:
        """Remove entries for IPs that have no recent requests."""
        if now - self._last_cleanup < self.window_seconds:
            return
        self._last_cleanup = now
        cutoff = now - self.window_seconds
        stale_keys = [
            k
            for k, timestamps in self._requests.items()
            if not timestamps or timestamps[-1] <= cutoff
        ]
        for k in stale_keys:
            del self._requests[k]

    async def check(self, request: Request) -> None:
        """Raise 429 if rate limit exceeded."""
        key = self._client_key(request)
        now = time.monotonic()

        self._cleanup_stale(now)

        cutoff = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        current = len(self._requests[key])

        # Store rate limit info for response headers
        request.state.rate_limit = {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - current - 1),
            "reset": int(now + self.window_seconds),
        }

        if current >= self.max_requests:
            request.state.rate_limit["remaining"] = 0
            raise HTTPException(
                429,
                detail=f"Rate limit exceeded: {self.max_requests} requests "
                f"per {self.window_seconds}s",
            )

        self._requests[key].append(now)


class RedisRateLimiter:
    """Redis-backed sliding window rate limiter using sorted sets.

    Shared across all uvicorn workers for accurate rate limiting.
    """

    def __init__(
        self, max_requests: int = 10, window_seconds: int = 60, prefix: str = "rl"
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix
        self._redis = None

    def _client_key(self, request: Request) -> str:
        return request.client.host if request.client else "unknown"

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            from nile.config import settings

            self._redis = aioredis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=2
            )
        return self._redis

    async def check(self, request: Request) -> None:
        """Raise 429 if rate limit exceeded. Falls back to pass-through on Redis errors."""
        try:
            r = await self._get_redis()
            key = f"{self.prefix}:{self._client_key(request)}"
            now = time.time()
            cutoff = now - self.window_seconds

            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zadd(key, {f"{now}": now})
            pipe.expire(key, self.window_seconds + 1)
            results = await pipe.execute()

            count = results[1]

            # Store rate limit info for response headers
            request.state.rate_limit = {
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - count - 1),
                "reset": int(now + self.window_seconds),
            }

            if count >= self.max_requests:
                request.state.rate_limit["remaining"] = 0
                raise HTTPException(
                    429,
                    detail=f"Rate limit exceeded: {self.max_requests} requests "
                    f"per {self.window_seconds}s",
                )
        except HTTPException:
            raise
        except Exception:
            # Redis down — fail open (allow request) rather than blocking all traffic
            logger.warning("Redis rate limiter unavailable, allowing request")


def create_limiter(
    max_requests: int = 10, window_seconds: int = 60, prefix: str = "rl"
) -> RateLimiter | RedisRateLimiter:
    """Create the appropriate rate limiter based on environment."""
    from nile.config import settings

    if settings.env != "development":
        return RedisRateLimiter(max_requests, window_seconds, prefix)
    return RateLimiter(max_requests, window_seconds)


# Pre-configured limiters
trading_limiter = create_limiter(max_requests=20, window_seconds=60, prefix="rl:trading")
quote_limiter = create_limiter(max_requests=60, window_seconds=60, prefix="rl:quote")
