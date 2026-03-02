"""Tests for pagination parameter validation across all list endpoints."""

import pytest


@pytest.mark.asyncio
class TestPaginationBounds:
    """Verify all list endpoints reject out-of-bounds pagination params."""

    @pytest.mark.parametrize(
        "url",
        [
            "/api/v1/agents?limit=-1",
            "/api/v1/agents?limit=0",
            "/api/v1/agents?limit=999",
            "/api/v1/agents/leaderboard?limit=-1",
            "/api/v1/agents/leaderboard?limit=0",
            "/api/v1/contracts?limit=-1",
            "/api/v1/contracts?limit=0",
            "/api/v1/contracts?skip=-1",
            "/api/v1/scans?limit=-1",
            "/api/v1/scans?limit=0",
            "/api/v1/scans?skip=-1",
            "/api/v1/persons?limit=-1",
            "/api/v1/persons?limit=0",
            "/api/v1/persons?offset=-1",
            "/api/v1/soul-tokens?limit=-1",
            "/api/v1/soul-tokens?limit=0",
            "/api/v1/soul-tokens?offset=-1",
            "/api/v1/events/history?limit=-1",
            "/api/v1/events/history?limit=0",
            "/api/v1/benchmarks?limit=-1",
            "/api/v1/benchmarks?skip=-1",
            "/api/v1/trading/history?limit=-1",
            "/api/v1/trading/history?limit=0",
            "/api/v1/kpis/trends?limit=-1",
        ],
    )
    async def test_invalid_pagination_rejected(self, client, db_session, auth_headers, url):
        """Endpoints should return 422 for invalid pagination values."""
        resp = await client.get(url, headers=auth_headers)
        assert resp.status_code == 422, f"Expected 422 for {url}, got {resp.status_code}"

    @pytest.mark.parametrize(
        "url",
        [
            "/api/v1/agents?limit=50",
            "/api/v1/contracts?limit=50&skip=0",
            "/api/v1/persons?limit=50&offset=0",
            "/api/v1/soul-tokens?limit=50&offset=0",
            "/api/v1/events/history?limit=50",
            "/api/v1/benchmarks?limit=50&skip=0",
            "/api/v1/trading/history?limit=50",
            "/api/v1/kpis/trends?limit=100",
        ],
    )
    async def test_valid_pagination_accepted(self, client, db_session, auth_headers, url):
        """Endpoints should return 200 for valid pagination values."""
        resp = await client.get(url, headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200 for {url}, got {resp.status_code}"


@pytest.mark.asyncio
class TestTradeAmountBounds:
    """Verify trade amount upper bound validation."""

    async def test_quote_rejects_excessive_amount(self, client, db_session):
        resp = await client.post(
            "/api/v1/trading/quote",
            json={
                "person_id": "00000000-0000-0000-0000-000000000001",
                "side": "buy",
                "amount": 2_000_000,
            },
        )
        assert resp.status_code == 422

    async def test_quote_rejects_negative_amount(self, client, db_session):
        resp = await client.post(
            "/api/v1/trading/quote",
            json={
                "person_id": "00000000-0000-0000-0000-000000000001",
                "side": "buy",
                "amount": -1,
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestEnumFilterValidation:
    """Verify status/mode filter params reject invalid values."""

    @pytest.mark.parametrize(
        "url",
        [
            "/api/v1/agents?status=bogus",
            "/api/v1/agents?capability=bogus",
            "/api/v1/scans?status=bogus",
            "/api/v1/oracle/reports?status=bogus",
        ],
    )
    async def test_invalid_filter_rejected(self, client, db_session, url):
        """Endpoints should return 422 for invalid filter values."""
        resp = await client.get(url)
        assert resp.status_code == 422, f"Expected 422 for {url}, got {resp.status_code}"

    @pytest.mark.parametrize(
        "url",
        [
            "/api/v1/agents?status=active",
            "/api/v1/agents?capability=detect",
            "/api/v1/scans?status=queued",
            "/api/v1/scans?status=succeeded",
            "/api/v1/oracle/reports?status=pending",
            "/api/v1/oracle/reports?status=confirmed",
        ],
    )
    async def test_valid_filter_accepted(self, client, db_session, url):
        """Endpoints should return 200 for valid filter values."""
        resp = await client.get(url)
        assert resp.status_code == 200, f"Expected 200 for {url}, got {resp.status_code}"


@pytest.mark.asyncio
class TestScanModeValidation:
    """Verify scan create rejects invalid modes."""

    async def test_invalid_scan_mode_rejected(self, client, db_session, auth_headers):
        resp = await client.post(
            "/api/v1/scans",
            json={
                "contract_id": "00000000-0000-0000-0000-000000000001",
                "mode": "invalid_mode",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_invalid_hint_level_rejected(self, client, db_session, auth_headers):
        resp = await client.post(
            "/api/v1/scans",
            json={
                "contract_id": "00000000-0000-0000-0000-000000000001",
                "mode": "detect",
                "hint_level": "extreme",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422
