"""Tests for soul token API endpoints."""

import uuid

import pytest

from nile.models.person import Person
from nile.models.soul_token import SoulToken


@pytest.fixture
async def person_with_token(db_session):
    """Create a person with a soul token."""
    person = Person(
        display_name="Soul Test Person",
        slug="soul-test",
        category="athlete",
    )
    db_session.add(person)
    await db_session.flush()

    token = SoulToken(
        person_id=person.id,
        name="SoulTest Token",
        symbol="STT",
        phase="bonding",
        chain="solana",
        current_price_sol=0.5,
        current_price_usd=125.0,
        market_cap_usd=50000.0,
        volume_24h_usd=5000.0,
        total_supply=1000000,
        reserve_balance_sol=10.0,
        graduation_threshold_sol=100.0,
        holder_count=42,
    )
    db_session.add(token)
    await db_session.flush()
    return person, token


@pytest.mark.asyncio
class TestListSoulTokens:
    async def test_empty_list(self, client, db_session):
        resp = await client.get("/api/v1/soul-tokens")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_with_token(self, client, db_session, person_with_token):
        resp = await client.get("/api/v1/soul-tokens")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["symbol"] == "STT"

    async def test_sort_by_volume(self, client, db_session, person_with_token):
        resp = await client.get("/api/v1/soul-tokens?sort=volume")
        assert resp.status_code == 200

    async def test_sort_by_new(self, client, db_session, person_with_token):
        resp = await client.get("/api/v1/soul-tokens?sort=new")
        assert resp.status_code == 200

    async def test_sort_by_price(self, client, db_session, person_with_token):
        resp = await client.get("/api/v1/soul-tokens?sort=price")
        assert resp.status_code == 200

    async def test_filter_by_phase(self, client, db_session, person_with_token):
        resp = await client.get("/api/v1/soul-tokens?phase=bonding")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["phase"] == "bonding" for t in data)


@pytest.mark.asyncio
class TestMarketOverview:
    async def test_empty_market(self, client, db_session):
        resp = await client.get("/api/v1/soul-tokens/market-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tokens"] == 0

    async def test_market_with_token(self, client, db_session, person_with_token):
        resp = await client.get("/api/v1/soul-tokens/market-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tokens"] >= 1


@pytest.mark.asyncio
class TestGetSoulToken:
    async def test_not_found(self, client, db_session):
        resp = await client.get(f"/api/v1/soul-tokens/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_found(self, client, db_session, person_with_token):
        _, token = person_with_token
        resp = await client.get(f"/api/v1/soul-tokens/{token.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "STT"
        assert data["person_name"] == "Soul Test Person"


@pytest.mark.asyncio
class TestTokenTrades:
    async def test_empty_trades(self, client, db_session, person_with_token):
        _, token = person_with_token
        resp = await client.get(f"/api/v1/soul-tokens/{token.id}/trades")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
class TestCircuitBreakers:
    async def test_list_breakers(self, client, db_session):
        resp = await client.get("/api/v1/soul-tokens/risk/circuit-breakers")
        assert resp.status_code == 200
        assert "active_breakers" in resp.json()


@pytest.mark.asyncio
class TestGraduatingSoon:
    async def test_empty(self, client, db_session):
        resp = await client.get("/api/v1/soul-tokens/graduating-soon")
        assert resp.status_code == 200

    async def test_with_token(self, client, db_session, person_with_token):
        resp = await client.get("/api/v1/soul-tokens/graduating-soon")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestCandles:
    async def test_empty_candles(self, client, db_session, person_with_token):
        _, token = person_with_token
        resp = await client.get(f"/api/v1/soul-tokens/{token.id}/candles")
        assert resp.status_code == 200
        assert resp.json() == []
