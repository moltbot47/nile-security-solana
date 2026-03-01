"""Tests for security headers middleware."""

import pytest


@pytest.mark.asyncio
class TestSecurityHeaders:
    async def test_health_has_x_content_type_options(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    async def test_health_has_x_frame_options(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.headers["X-Frame-Options"] == "DENY"

    async def test_health_has_xss_protection(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.headers["X-XSS-Protection"] == "1; mode=block"

    async def test_health_has_referrer_policy(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    async def test_health_has_permissions_policy(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"

    async def test_headers_present_on_all_routes(self, client):
        """Security headers should be set on every response, not just health."""
        resp = await client.get("/api/v1/contracts")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
