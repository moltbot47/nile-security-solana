"""Tests for trading endpoints — quotes, buy/sell, portfolio."""

import uuid

from nile.core.auth import create_agent_token, hash_api_key
from nile.models.agent import Agent
from nile.models.person import Person
from nile.models.soul_token import SoulToken

# --- Helpers ---

VALID_TRADER_ADDR = "FakeTraderAddress1234567890ABCDEFGHIJK"


async def _create_auth_agent(db_session) -> tuple[Agent, str]:
    """Create an active agent and return (agent, jwt_token)."""
    raw_key = f"nile_trade_test_{uuid.uuid4().hex[:8]}"
    agent = Agent(
        name=f"trade-agent-{uuid.uuid4().hex[:6]}",
        owner_id="owner-test",
        capabilities=["detect"],
        status="active",
        api_key_hash=hash_api_key(raw_key),
    )
    db_session.add(agent)
    await db_session.flush()
    token = create_agent_token(str(agent.id))
    return agent, token


async def _create_tradeable_token(
    db_session, slug: str, price_usd: float = 10.0
) -> tuple[Person, SoulToken]:
    """Create person + soul token for trading tests."""
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
        phase="bonding",
        current_price_sol=0.04,
        current_price_usd=price_usd,
        market_cap_usd=100_000,
        volume_24h_usd=5000,
        total_supply=1_000_000,
        reserve_balance_sol=100,
        graduation_threshold_sol=200,
        holder_count=50,
    )
    db_session.add(token)
    await db_session.flush()
    return person, token


# --- Quote ---


async def test_quote_buy(client, db_session):
    """POST /trading/quote returns a buy quote with fee."""
    person, _token = await _create_tradeable_token(db_session, "quote-buy")

    response = await client.post(
        "/api/v1/trading/quote",
        json={
            "person_id": str(person.id),
            "side": "buy",
            "amount": "5.0",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["side"] == "buy"
    assert data["fee"] > 0
    assert data["output_amount"] > 0
    assert data["estimated_price"] == 10.0


async def test_quote_sell(client, db_session):
    """POST /trading/quote returns a sell quote."""
    person, _token = await _create_tradeable_token(db_session, "quote-sell")

    response = await client.post(
        "/api/v1/trading/quote",
        json={
            "person_id": str(person.id),
            "side": "sell",
            "amount": "100.0",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["side"] == "sell"
    assert data["fee"] > 0


async def test_quote_no_token_404(client):
    """POST /trading/quote returns 404 when person has no soul token."""
    fake_id = str(uuid.uuid4())
    response = await client.post(
        "/api/v1/trading/quote",
        json={"person_id": fake_id, "side": "buy", "amount": "1.0"},
    )
    assert response.status_code == 404


# --- Buy ---


async def test_buy_creates_trade(client, db_session):
    """POST /trading/buy creates a trade record."""
    _, token = await _create_auth_agent(db_session)
    person, _soul_token = await _create_tradeable_token(db_session, "buy-trade")

    response = await client.post(
        "/api/v1/trading/buy",
        json={
            "person_id": str(person.id),
            "side": "buy",
            "amount": "2.0",
            "trader_address": VALID_TRADER_ADDR,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["side"] == "buy"
    assert data["trader_address"] == VALID_TRADER_ADDR
    assert float(data["fee_total_sol"]) > 0


async def test_buy_requires_auth(client, db_session):
    """POST /trading/buy without auth returns 401."""
    person, _ = await _create_tradeable_token(db_session, "buy-noauth")
    response = await client.post(
        "/api/v1/trading/buy",
        json={
            "person_id": str(person.id),
            "amount": "1.0",
            "trader_address": VALID_TRADER_ADDR,
        },
    )
    assert response.status_code == 401


# --- Sell ---


async def test_sell_creates_trade(client, db_session):
    """POST /trading/sell creates a trade record."""
    _, token = await _create_auth_agent(db_session)
    person, _soul_token = await _create_tradeable_token(db_session, "sell-trade")

    response = await client.post(
        "/api/v1/trading/sell",
        json={
            "person_id": str(person.id),
            "side": "sell",
            "amount": "50.0",
            "trader_address": VALID_TRADER_ADDR,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["side"] == "sell"


async def test_sell_requires_auth(client, db_session):
    """POST /trading/sell without auth returns 401."""
    person, _ = await _create_tradeable_token(db_session, "sell-noauth")
    response = await client.post(
        "/api/v1/trading/sell",
        json={
            "person_id": str(person.id),
            "amount": "1.0",
            "trader_address": VALID_TRADER_ADDR,
        },
    )
    assert response.status_code == 401


# --- Trade History ---


async def test_trade_history_empty(client):
    """GET /trading/history returns empty list when no trades exist."""
    response = await client.get("/api/v1/trading/history")
    assert response.status_code == 200
    assert response.json() == []


async def test_trade_history_filter_by_trader(client, db_session):
    """GET /trading/history?trader_address=X filters by trader."""
    _, token = await _create_auth_agent(db_session)
    person, _ = await _create_tradeable_token(db_session, "hist-filter")

    # Create two trades with different addresses
    await client.post(
        "/api/v1/trading/buy",
        json={
            "person_id": str(person.id),
            "side": "buy",
            "amount": "1.0",
            "trader_address": VALID_TRADER_ADDR,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    other_addr = "OtherTraderAddress12345678901234567890"
    await client.post(
        "/api/v1/trading/buy",
        json={
            "person_id": str(person.id),
            "side": "buy",
            "amount": "1.0",
            "trader_address": other_addr,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get(f"/api/v1/trading/history?trader_address={VALID_TRADER_ADDR}")
    data = response.json()
    assert len(data) == 1
    assert data[0]["trader_address"] == VALID_TRADER_ADDR


# --- Portfolio ---


async def test_portfolio_empty(client):
    """GET /trading/portfolio returns empty list for unknown wallet."""
    response = await client.get(
        "/api/v1/trading/portfolio?wallet_address=UnknownWallet123456789012345678"
    )
    assert response.status_code == 200
    assert response.json() == []
