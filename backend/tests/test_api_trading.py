"""Tests for trading API endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from nile.core.auth import create_agent_token
from nile.models.agent import Agent
from nile.models.person import Person
from nile.models.soul_token import SoulToken


@pytest.fixture
async def trading_setup(db_session):
    """Create person, soul token, and authenticated agent for trading tests."""
    person = Person(
        display_name="Trading Test",
        slug="trading-test",
        category="athlete",
    )
    db_session.add(person)
    await db_session.flush()

    token = SoulToken(
        person_id=person.id,
        name="Trade Token",
        symbol="TRD",
        phase="bonding",
        chain="solana",
        current_price_sol=0.01,
        current_price_usd=2.50,
        market_cap_usd=25000.0,
        total_supply=10000000,
        reserve_balance_sol=5.0,
        graduation_threshold_sol=100.0,
    )
    db_session.add(token)

    agent = Agent(
        name=f"trader-{uuid.uuid4().hex[:8]}",
        owner_id="test-owner",
        capabilities=["detect"],
        status="active",
        api_key_hash="fakehash",
    )
    db_session.add(agent)
    await db_session.flush()

    jwt_token = create_agent_token(str(agent.id))
    return person, token, agent, jwt_token


@pytest.mark.asyncio
class TestGetQuote:
    async def test_quote_buy(self, client, db_session, trading_setup):
        person, token, _, _ = trading_setup
        resp = await client.post(
            "/api/v1/trading/quote",
            json={
                "person_id": str(person.id),
                "side": "buy",
                "amount": 1.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["side"] == "buy"
        assert data["fee"] > 0

    async def test_quote_sell(self, client, db_session, trading_setup):
        person, _, _, _ = trading_setup
        resp = await client.post(
            "/api/v1/trading/quote",
            json={
                "person_id": str(person.id),
                "side": "sell",
                "amount": 100.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["side"] == "sell"

    async def test_quote_not_found(self, client, db_session):
        resp = await client.post(
            "/api/v1/trading/quote",
            json={
                "person_id": str(uuid.uuid4()),
                "side": "buy",
                "amount": 1.0,
            },
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestTradeHistory:
    async def test_empty_history(self, client, db_session):
        resp = await client.get("/api/v1/trading/history")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_filter_by_address(self, client, db_session):
        resp = await client.get("/api/v1/trading/history?trader_address=someaddr")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestExecuteBuy:
    async def test_buy_unauthenticated(self, client, db_session):
        resp = await client.post(
            "/api/v1/trading/buy",
            json={
                "person_id": str(uuid.uuid4()),
                "side": "buy",
                "amount": 1.0,
                "trader_address": "A" * 44,
            },
        )
        assert resp.status_code == 401

    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    async def test_buy_success(self, mock_risk, client, db_session, trading_setup):
        mock_risk.return_value = []
        person, token, agent, jwt_token = trading_setup
        resp = await client.post(
            "/api/v1/trading/buy",
            json={
                "person_id": str(person.id),
                "side": "buy",
                "amount": 1.0,
                "trader_address": "B" * 44,
            },
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["side"] == "buy"

    async def test_buy_not_found(self, client, db_session, trading_setup):
        _, _, _, jwt_token = trading_setup
        resp = await client.post(
            "/api/v1/trading/buy",
            json={
                "person_id": str(uuid.uuid4()),
                "side": "buy",
                "amount": 1.0,
                "trader_address": "C" * 44,
            },
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestExecuteSell:
    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    async def test_sell_success(self, mock_risk, client, db_session, trading_setup):
        mock_risk.return_value = []
        person, _, _, jwt_token = trading_setup
        resp = await client.post(
            "/api/v1/trading/sell",
            json={
                "person_id": str(person.id),
                "side": "sell",
                "amount": 100.0,
                "trader_address": "D" * 44,
            },
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["side"] == "sell"

    async def test_sell_not_found(self, client, db_session, trading_setup):
        _, _, _, jwt_token = trading_setup
        resp = await client.post(
            "/api/v1/trading/sell",
            json={
                "person_id": str(uuid.uuid4()),
                "side": "sell",
                "amount": 100.0,
                "trader_address": "E" * 44,
            },
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestPortfolio:
    async def test_empty_portfolio(self, client, db_session):
        resp = await client.get("/api/v1/trading/portfolio?wallet_address=test123")
        assert resp.status_code == 200
        assert resp.json() == []
