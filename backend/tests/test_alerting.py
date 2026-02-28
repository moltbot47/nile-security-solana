"""Tests for alerting — Discord webhook alerts."""

from unittest.mock import AsyncMock, patch

import pytest

from nile.core.alerting import (
    AlertLevel,
    alert_health_degraded,
    alert_high_error_rate,
    alert_scan_failure,
    send_alert,
)


class TestAlertLevel:
    def test_info(self):
        assert AlertLevel.INFO == "info"

    def test_warning(self):
        assert AlertLevel.WARNING == "warning"

    def test_critical(self):
        assert AlertLevel.CRITICAL == "critical"


@pytest.mark.asyncio
class TestSendAlert:
    async def test_no_webhook_returns_false(self):
        with patch("nile.core.alerting.settings") as mock_settings:
            mock_settings.discord_alert_webhook = ""
            result = await send_alert("Test", "Message")
            assert result is False

    async def test_successful_send(self):
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = lambda: None
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("nile.core.alerting.settings") as mock_settings,
            patch("nile.core.alerting.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.discord_alert_webhook = "https://discord.com/api/webhooks/test"
            mock_settings.solana_network = "devnet"
            result = await send_alert("Test", "Message", level=AlertLevel.CRITICAL)
            assert result is True
            mock_client.post.assert_called_once()

    async def test_http_error_returns_false(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("HTTP error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("nile.core.alerting.settings") as mock_settings,
            patch("nile.core.alerting.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.discord_alert_webhook = "https://discord.com/api/webhooks/test"
            mock_settings.solana_network = "devnet"
            result = await send_alert("Test", "Message")
            assert result is False

    async def test_with_fields(self):
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = lambda: None
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("nile.core.alerting.settings") as mock_settings,
            patch("nile.core.alerting.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.discord_alert_webhook = "https://discord.com/api/webhooks/test"
            mock_settings.solana_network = "devnet"
            result = await send_alert(
                "Test", "Message", fields={"key": "value"}
            )
            assert result is True


@pytest.mark.asyncio
class TestAlertHelpers:
    @patch("nile.core.alerting.send_alert", new_callable=AsyncMock, return_value=True)
    async def test_alert_health_degraded(self, mock_send):
        result = await alert_health_degraded({"database": "error: timeout"})
        assert result is True
        mock_send.assert_called_once()

    @patch("nile.core.alerting.send_alert", new_callable=AsyncMock, return_value=True)
    async def test_alert_scan_failure(self, mock_send):
        result = await alert_scan_failure("addr123", "RPC timeout")
        assert result is True

    @patch("nile.core.alerting.send_alert", new_callable=AsyncMock, return_value=True)
    async def test_alert_high_error_rate(self, mock_send):
        result = await alert_high_error_rate(50, 300)
        assert result is True
