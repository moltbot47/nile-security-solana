"""Structured request/response logging middleware using structlog."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("nile.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with structured JSON fields: timing, status, request ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        # Skip health check noise
        if request.url.path == "/api/v1/health":
            return response

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 1),
            request_id=request_id,
            client=request.client.host if request.client else "unknown",
        )

        return response
