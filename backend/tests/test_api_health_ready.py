"""Tests for health metrics endpoint."""

import pytest


@pytest.mark.asyncio
class TestMetricsEndpoint:
    async def test_metrics_summary(self, client):
        resp = await client.get("/api/v1/health/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data
        assert "total_scans" in data
        assert "avg_scan_duration_ms" in data
