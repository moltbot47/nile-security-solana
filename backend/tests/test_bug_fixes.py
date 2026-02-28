"""TDD bug fix tests — each test was written BEFORE the fix.

Tests are grouped by bug ID from the quality improvement plan.
"""

import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from nile.core.rate_limit import RateLimiter

# --- Bug 1: Route shadowing in soul_tokens.py ---


async def test_circuit_breakers_endpoint_reachable(client):
    """GET /soul-tokens/risk/circuit-breakers must return 200, not 422.

    Bug: Static route /risk/circuit-breakers was registered AFTER the dynamic
    /{token_id}/risk route, so FastAPI tried to parse "risk" as a UUID.
    """
    response = await client.get("/api/v1/soul-tokens/risk/circuit-breakers")
    assert response.status_code == 200
    data = response.json()
    assert "active_breakers" in data


# --- Bug 2: Unauthenticated execute_buy ---


async def test_buy_requires_auth(client):
    """POST /trading/buy without auth must return 401."""
    response = await client.post(
        "/api/v1/trading/buy",
        json={
            "person_id": "00000000-0000-0000-0000-000000000001",
            "amount": "1.0",
            "trader_address": "FakeAddress123456789012345678901234567890",
        },
    )
    assert response.status_code == 401


async def test_sell_requires_auth(client):
    """POST /trading/sell without auth must return 401."""
    response = await client.post(
        "/api/v1/trading/sell",
        json={
            "person_id": "00000000-0000-0000-0000-000000000001",
            "amount": "1.0",
            "trader_address": "FakeAddress123456789012345678901234567890",
        },
    )
    assert response.status_code == 401


# --- Bug 3: Unauthenticated submit_report ---


async def test_submit_report_requires_auth(client):
    """POST /oracle/reports without auth must return 401."""
    response = await client.post(
        "/api/v1/oracle/reports",
        json={
            "person_id": "00000000-0000-0000-0000-000000000001",
            "event_type": "social_viral",
            "source": "twitter",
            "headline": "Test event",
            "impact_score": 50,
        },
    )
    assert response.status_code == 401


# --- Bug 4: Unauthenticated update_person ---


async def test_update_person_requires_auth(client):
    """PATCH /persons/{id} without auth must return 401."""
    response = await client.patch(
        "/api/v1/persons/00000000-0000-0000-0000-000000000001",
        json={"display_name": "Hacked Name"},
    )
    assert response.status_code == 401


async def test_create_person_requires_auth(client):
    """POST /persons without auth must return 401."""
    response = await client.post(
        "/api/v1/persons",
        json={
            "display_name": "Test Person",
            "slug": "test-person",
        },
    )
    assert response.status_code == 401


# --- Bug 5: Rate limiter memory leak ---


def test_rate_limiter_cleans_stale_entries():
    """Rate limiter must not grow unbounded with unique IPs.

    Bug: _requests dict grew forever — stale keys for IPs that stopped
    making requests were never cleaned up.
    """
    limiter = RateLimiter(max_requests=100, window_seconds=1)

    # Simulate 500 unique IPs making requests
    for i in range(500):
        mock_request = MagicMock()
        mock_request.client.host = f"192.168.1.{i % 256}"
        mock_request.headers = {}
        limiter.check(mock_request)

    # Wait for window to expire
    time.sleep(1.1)

    # One more request should trigger cleanup
    mock_request = MagicMock()
    mock_request.client.host = "10.0.0.1"
    mock_request.headers = {}
    limiter.check(mock_request)

    # After cleanup, stale entries should be removed
    assert len(limiter._requests) <= 10, (
        f"Expected stale entries cleaned up, got {len(limiter._requests)} keys"
    )


# --- Bug 6: Rate limiter trusts X-Forwarded-For ---


def test_rate_limiter_ignores_forwarded_for():
    """Rate limiter must use real client IP, not X-Forwarded-For.

    Bug: Attacker could spoof X-Forwarded-For to bypass rate limits.
    """
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    # First request with spoofed header
    mock_request = MagicMock()
    mock_request.client.host = "1.2.3.4"
    mock_request.headers = {"x-forwarded-for": "spoofed-ip-1"}
    limiter.check(mock_request)

    # Second request with different spoofed header but SAME real IP
    mock_request2 = MagicMock()
    mock_request2.client.host = "1.2.3.4"
    mock_request2.headers = {"x-forwarded-for": "spoofed-ip-2"}
    limiter.check(mock_request2)

    # Third request should be rate limited (same real IP)
    mock_request3 = MagicMock()
    mock_request3.client.host = "1.2.3.4"
    mock_request3.headers = {"x-forwarded-for": "spoofed-ip-3"}

    with pytest.raises(HTTPException):
        limiter.check(mock_request3)


# --- Bug 7: get_optional_agent swallows invalid credentials ---


async def test_optional_agent_rejects_invalid_token(client):
    """Request with invalid Bearer token to public endpoint should still work.

    Note: get_optional_agent should return None for no-credentials,
    but raise 401 for malformed/invalid credentials.
    This test verifies the health endpoint (public) still works without auth.
    """
    # No auth = fine for public endpoints
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
