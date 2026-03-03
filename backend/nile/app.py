"""FastAPI application factory."""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from nile.config import settings
from nile.core.exceptions import NileBaseError
from nile.middleware.logging import RequestLoggingMiddleware
from nile.middleware.metrics import MetricsMiddleware
from nile.routers.v1 import api_router


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Rate limit headers (set by rate limiter check())
        rl = getattr(request.state, "rate_limit", None)
        if rl:
            response.headers["X-RateLimit-Limit"] = str(rl["limit"])
            response.headers["X-RateLimit-Remaining"] = str(rl["remaining"])
            response.headers["X-RateLimit-Reset"] = str(rl["reset"])
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.devnet.solana.com "
            "https://api.mainnet-beta.solana.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        if settings.env != "development":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response


def _configure_logging() -> None:
    """Set up structlog for structured JSON logging in prod, pretty in dev."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.env == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def create_app() -> FastAPI:
    _configure_logging()
    log = structlog.get_logger("nile.app")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        log.info(
            "app_started",
            version="0.3.0",
            env=settings.env,
            chain=settings.chain,
            network=settings.solana_network,
        )
        yield
        log.info("app_shutdown")

    app = FastAPI(
        title=settings.app_name,
        description=(
            "## NILE Security API\n\n"
            "Pre-transaction security intelligence for Solana programs and tokens.\n\n"
            "**Core endpoint:** `POST /api/v1/scans/solana` — paste any Solana address, "
            "get a 0-100 security score with exploit pattern matching, holder concentration "
            "analysis, liquidity detection, and creator wallet profiling.\n\n"
            "### Scoring Dimensions\n"
            "- **Name** (25%) — Identity, provenance, ecosystem presence\n"
            "- **Image** (25%) — Security posture (signer checks, CPI safety)\n"
            "- **Likeness** (25%) — Exploit pattern matching (14 known patterns)\n"
            "- **Essence** (25%) — Code quality, upgrade authority, decentralization\n\n"
            "### Grades\n"
            "| Score | Grade | Meaning |\n"
            "|-------|-------|---------|\n"
            "| 90-100 | A | Very safe |\n"
            "| 80-89 | B | Safe |\n"
            "| 70-79 | C | Moderate risk |\n"
            "| 50-69 | D | High risk |\n"
            "| 0-49 | F | Critical risk |\n\n"
            "### Integration\n"
            "Wallet teams: contact dbutler@eulaproperties.com for API key access.\n"
        ),
        version="0.4.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # --- Exception handlers ---
    @app.exception_handler(NileBaseError)
    async def nile_exception_handler(request: Request, exc: NileBaseError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # --- Middleware (order matters: last added = first executed) ---
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-API-Key"],
    )

    # --- Routes ---
    app.include_router(api_router)

    return app


app = create_app()
