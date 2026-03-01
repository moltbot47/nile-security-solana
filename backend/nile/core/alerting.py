"""Discord webhook alerting for critical system events."""

from datetime import UTC, datetime
from enum import StrEnum

import httpx
import structlog

from nile.config import settings

logger = structlog.get_logger("nile.alerting")


class AlertLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


_LEVEL_COLORS = {
    AlertLevel.INFO: 0x3498DB,  # blue
    AlertLevel.WARNING: 0xF39C12,  # amber
    AlertLevel.CRITICAL: 0xE74C3C,  # red
}

_LEVEL_EMOJI = {
    AlertLevel.INFO: "ℹ️",
    AlertLevel.WARNING: "⚠️",
    AlertLevel.CRITICAL: "🚨",
}


async def send_alert(
    title: str,
    message: str,
    level: AlertLevel = AlertLevel.WARNING,
    fields: dict[str, str] | None = None,
) -> bool:
    """Send an alert to the configured Discord webhook.

    Returns True if sent successfully, False otherwise.
    Silently returns False if no webhook is configured.
    """
    webhook_url = getattr(settings, "discord_alert_webhook", "")
    if not webhook_url:
        logger.debug("Alert skipped (no webhook): %s — %s", title, message)
        return False

    embed = {
        "title": f"{_LEVEL_EMOJI[level]} {title}",
        "description": message,
        "color": _LEVEL_COLORS[level],
        "timestamp": datetime.now(UTC).isoformat(),
        "footer": {
            "text": f"NILE Security • {settings.solana_network}",
        },
    }

    if fields:
        embed["fields"] = [{"name": k, "value": v, "inline": True} for k, v in fields.items()]

    payload = {"embeds": [embed]}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("Failed to send alert: %s", exc)
        return False


async def alert_health_degraded(failed_checks: dict[str, str]) -> bool:
    fields = {k: v for k, v in failed_checks.items() if "error" in v}
    return await send_alert(
        title="Health Check Degraded",
        message="One or more dependencies are unreachable.",
        level=AlertLevel.CRITICAL,
        fields=fields,
    )


async def alert_scan_failure(address: str, error: str) -> bool:
    return await send_alert(
        title="Scan Failed",
        message=f"Program analysis failed for `{address}`",
        level=AlertLevel.WARNING,
        fields={"address": address, "error": error[:200]},
    )


async def alert_high_error_rate(error_count: int, window_seconds: int) -> bool:
    return await send_alert(
        title="High Error Rate",
        message=f"{error_count} errors in the last {window_seconds}s.",
        level=AlertLevel.CRITICAL,
        fields={"error_count": str(error_count), "window": f"{window_seconds}s"},
    )
