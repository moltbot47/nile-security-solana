"""Tests for soul token listing and market data endpoints."""

import uuid

from nile.models.person import Person
from nile.models.soul_token import SoulToken

# --- Helpers ---


async def _create_person_with_token(
    db_session,
    slug: str,
    *,
    price_usd: float = 1.0,
    market_cap: float = 10000.0,
    volume: float = 500.0,
    phase: str = "bonding",
) -> tuple[Person, SoulToken]:
    """Create a person + linked soul token."""
    person = Person(
        display_name=slug.replace("-", " ").title(),
        slug=slug,
        category="general",
    )
    db_session.add(person)
    await db_session.flush()

    token = SoulToken(
        person_id=person.id,
        name=f"{slug}-token",
        symbol=slug[:4].upper(),
        phase=phase,
        current_price_sol=price_usd / 250,
        current_price_usd=price_usd,
        market_cap_usd=market_cap,
        volume_24h_usd=volume,
        total_supply=1_000_000,
        reserve_balance_sol=10,
        graduation_threshold_sol=200,
        holder_count=42,
    )
    db_session.add(token)
    await db_session.flush()
    return person, token


# --- List ---


async def test_list_soul_tokens_empty(client):
    """GET /soul-tokens returns empty list when none exist."""
    response = await client.get("/api/v1/soul-tokens")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_soul_tokens_with_data(client, db_session):
    """GET /soul-tokens returns tokens with market data."""
    await _create_person_with_token(db_session, "token-list-1")
    await _create_person_with_token(db_session, "token-list-2")

    response = await client.get("/api/v1/soul-tokens")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert "market_cap_usd" in data[0]


async def test_list_soul_tokens_filter_phase(client, db_session):
    """GET /soul-tokens?phase=bonding filters by phase."""
    await _create_person_with_token(db_session, "bonding-tok", phase="bonding")
    await _create_person_with_token(db_session, "amm-tok", phase="amm")

    response = await client.get("/api/v1/soul-tokens?phase=bonding")
    data = response.json()
    assert len(data) == 1
    assert data[0]["phase"] == "bonding"


async def test_list_soul_tokens_pagination(client, db_session):
    """GET /soul-tokens supports offset and limit pagination."""
    for i in range(5):
        await _create_person_with_token(db_session, f"pag-tok-{i}")

    response = await client.get("/api/v1/soul-tokens?limit=2&offset=0")
    assert len(response.json()) == 2

    response = await client.get("/api/v1/soul-tokens?limit=2&offset=4")
    assert len(response.json()) == 1


# --- Market Overview ---


async def test_market_overview_empty(client):
    """GET /soul-tokens/market-overview returns zeros when no tokens exist."""
    response = await client.get("/api/v1/soul-tokens/market-overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tokens"] == 0
    assert data["total_market_cap_usd"] == 0


async def test_market_overview_with_data(client, db_session):
    """GET /soul-tokens/market-overview aggregates market data."""
    await _create_person_with_token(db_session, "mkt-tok-1", market_cap=5000.0, volume=100.0)
    await _create_person_with_token(db_session, "mkt-tok-2", market_cap=3000.0, volume=200.0)

    response = await client.get("/api/v1/soul-tokens/market-overview")
    data = response.json()
    assert data["total_tokens"] == 2
    assert data["total_market_cap_usd"] == 8000.0
    assert data["total_volume_24h_usd"] == 300.0


# --- Get by ID ---


async def test_get_soul_token_by_id(client, db_session):
    """GET /soul-tokens/{id} returns the correct token."""
    _, token = await _create_person_with_token(db_session, "get-tok")

    response = await client.get(f"/api/v1/soul-tokens/{token.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "GET-"


async def test_get_soul_token_not_found(client):
    """GET /soul-tokens/{id} returns 404 for non-existent token."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/soul-tokens/{fake_id}")
    assert response.status_code == 404


# --- Trades (per token) ---


async def test_token_trades_empty(client, db_session):
    """GET /soul-tokens/{id}/trades returns empty list initially."""
    _, token = await _create_person_with_token(db_session, "no-trades")
    response = await client.get(f"/api/v1/soul-tokens/{token.id}/trades")
    assert response.status_code == 200
    assert response.json() == []


# --- Candles ---


async def test_token_candles_empty(client, db_session):
    """GET /soul-tokens/{id}/candles returns empty list initially."""
    _, token = await _create_person_with_token(db_session, "no-candles")
    response = await client.get(f"/api/v1/soul-tokens/{token.id}/candles")
    assert response.status_code == 200
    assert response.json() == []


# --- Circuit Breakers (static route, tested in bug_fixes too) ---


async def test_circuit_breakers_endpoint(client):
    """GET /soul-tokens/risk/circuit-breakers returns active breakers."""
    response = await client.get("/api/v1/soul-tokens/risk/circuit-breakers")
    assert response.status_code == 200
    assert "active_breakers" in response.json()
