"""Simple in-memory rate limiter for trading endpoints."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    """Token bucket rate limiter keyed by client IP."""

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
        # Run cleanup at most once per window
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

    def check(self, request: Request) -> None:
        """Raise 429 if rate limit exceeded."""
        key = self._client_key(request)
        now = time.monotonic()

        # Periodically clean up stale entries to prevent memory leak
        self._cleanup_stale(now)

        cutoff = now - self.window_seconds

        # Prune expired entries for this key
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

        if len(self._requests[key]) >= self.max_requests:
            raise HTTPException(
                429,
                detail=f"Rate limit exceeded: {self.max_requests} requests "
                f"per {self.window_seconds}s",
            )

        self._requests[key].append(now)


# Pre-configured limiters
trading_limiter = RateLimiter(max_requests=20, window_seconds=60)
quote_limiter = RateLimiter(max_requests=60, window_seconds=60)
