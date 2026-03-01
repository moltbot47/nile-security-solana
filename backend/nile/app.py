"""FastAPI application factory."""

import logging
import sys

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nile.config import settings
from nile.core.exceptions import NileBaseError
from nile.middleware.logging import RequestLoggingMiddleware
from nile.middleware.metrics import MetricsMiddleware
from nile.routers.v1 import api_router


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

    app = FastAPI(
        title=settings.app_name,
        description="NILE Smart Contract Security Intelligence Platform",
        version="0.3.0",
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routes ---
    app.include_router(api_router)

    # --- Lifecycle events ---
    log = structlog.get_logger("nile.app")

    @app.on_event("startup")
    async def on_startup() -> None:
        log.info(
            "app_started",
            version="0.3.0",
            env=settings.env,
            chain=settings.chain,
            network=settings.solana_network,
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        log.info("app_shutdown")

    return app


app = create_app()
