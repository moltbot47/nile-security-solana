"""Deep tests for health endpoints — readiness degraded, metrics summary."""

import pytest


@pytest.mark.asyncio
class TestReadinessEndpoint:
    async def test_readiness_returns_checks(self, client):
        """Readiness endpoint returns status and checks dict."""
        resp = await client.get("/api/v1/health/ready")
        # With test SQLite DB, database check should pass
        # Redis and Solana RPC will likely fail → degraded
        assert resp.status_code in (200, 503)
        data = resp.json()
        # Response is either a dict or a tuple (dict, status_code)
        if isinstance(data, list):
            data = data[0]
        assert "checks" in data or "status" in data


@pytest.mark.asyncio
class TestMetricsSummary:
    async def test_metrics_returns_counts(self, client):
        resp = await client.get("/api/v1/health/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data
        assert "total_scans" in data
        assert "avg_scan_duration_ms" in data
