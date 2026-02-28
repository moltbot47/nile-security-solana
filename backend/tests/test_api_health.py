"""Tests for health check API endpoints."""

import pytest


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_liveness_returns_ok(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "nile-security"
        assert data["chain"] == "solana"
