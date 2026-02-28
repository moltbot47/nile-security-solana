"""Health check endpoints with real dependency validation."""

import logging

from fastapi import APIRouter

from nile.config import settings

router = APIRouter()
logger = logging.getLogger("nile.health")


@router.get("/health")
async def health():
    """Liveness probe — always returns ok if the process is running."""
    return {
        "status": "ok",
        "service": "nile-security",
        "version": "0.3.0",
        "chain": settings.chain,
        "network": settings.solana_network,
    }


@router.get("/health/ready")
async def readiness():
    """Readiness probe — validates database, Redis, and Solana RPC connectivity."""
    checks: dict[str, str] = {}
    overall = "ready"

    # Database check
    try:
        from sqlalchemy import text

        from nile.core.database import async_session

        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        overall = "degraded"
        logger.warning("Health check: database unreachable: %s", exc)

    # Redis check
    try:
        from nile.core.event_bus import get_redis

        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        overall = "degraded"
        logger.warning("Health check: redis unreachable: %s", exc)

    # Solana RPC check
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                settings.solana_rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
            )
            data = resp.json()
            if data.get("result") == "ok":
                checks["solana_rpc"] = "ok"
            else:
                checks["solana_rpc"] = f"unhealthy: {data.get('error', data)}"
                overall = "degraded"
    except Exception as exc:
        checks["solana_rpc"] = f"error: {exc}"
        overall = "degraded"
        logger.warning("Health check: Solana RPC unreachable: %s", exc)

    status_code = 200 if overall == "ready" else 503
    return {"status": overall, "checks": checks}, status_code


@router.get("/health/metrics")
async def metrics_summary():
    """Quick metrics summary (full Prometheus metrics at /metrics)."""
    from nile.middleware.metrics import metrics

    return {
        "total_requests": sum(metrics.request_count.values()),
        "total_scans": metrics.scan_count,
        "avg_scan_duration_ms": (
            round(metrics.scan_duration_sum / metrics.scan_count * 1000, 1)
            if metrics.scan_count > 0
            else 0
        ),
        "status_codes": dict(metrics.status_count),
    }
