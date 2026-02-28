"""Tests for middleware: metrics and request logging."""

from nile.middleware.metrics import _Metrics


async def test_metrics_middleware_counts_requests(client):
    """MetricsMiddleware increments request count on each request."""
    from nile.middleware.metrics import metrics

    initial = sum(metrics.request_count.values())

    await client.get("/api/v1/health")
    await client.get("/api/v1/health")
    await client.get("/api/v1/contracts")

    after = sum(metrics.request_count.values())
    assert after >= initial + 3


async def test_metrics_middleware_tracks_status_codes(client):
    """MetricsMiddleware tracks HTTP status code distribution."""
    from nile.middleware.metrics import metrics

    initial_200 = metrics.status_count.get(200, 0)

    await client.get("/api/v1/health")

    assert metrics.status_count.get(200, 0) >= initial_200 + 1


async def test_request_logging_adds_request_id(client):
    """RequestLoggingMiddleware adds X-Request-ID to responses."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers


def test_metrics_initialization():
    """_Metrics initializes with zero counters."""
    m = _Metrics()
    assert m.scan_count == 0
    assert m.scan_duration_sum == 0.0
    assert sum(m.request_count.values()) == 0
    assert sum(m.status_count.values()) == 0
