"""Tests for health check endpoints."""


async def test_health_liveness(client):
    """GET /health returns ok with service info."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "nile-security"
    assert data["chain"] == "solana"


async def test_health_metrics_endpoint(client):
    """GET /health/metrics returns metric counters."""
    response = await client.get("/api/v1/health/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "total_scans" in data
    assert "avg_scan_duration_ms" in data
