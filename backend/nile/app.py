"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nile.config import settings
from nile.core.exceptions import NileBaseError
from nile.middleware.logging import RequestLoggingMiddleware
from nile.routers.v1 import api_router


def create_app() -> FastAPI:
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

    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "ok", "version": "0.3.0", "chain": settings.chain}

    return app


app = create_app()
