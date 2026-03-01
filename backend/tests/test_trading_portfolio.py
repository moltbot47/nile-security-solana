"""Tests for trading portfolio endpoint and sell risk alert logging."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from nile.core.auth import create_agent_token
from nile.models.agent import Agent
from nile.models.person import Person
from nile.models.portfolio import Portfolio
from nile.models.soul_token import SoulToken


@pytest.fixture
async def portfolio_env(db_session):
    """Set up person + token + portfolio + agent for portfolio tests."""
    person = Person(
        display_name="Portfolio Test",
        slug=f"port-{uuid.uuid4().hex[:6]}",
        category="athlete",
    )
    db_session.add(person)
    await db_session.flush()

    token = SoulToken(
        person_id=person.id,
        name="Portfolio Token",
        symbol="PFT",
        phase="bonding",
        chain="solana",
        current_price_sol=0.05,
        current_price_usd=12.50,
        market_cap_usd=125000.0,
        total_supply=10000000,
        reserve_balance_sol=25.0,
        graduation_threshold_sol=100.0,
    )
    db_session.add(token)
    await db_session.flush()

    wallet = "H" * 44
    portfolio = Portfolio(
        wallet_address=wallet,
        soul_token_id=token.id,
        balance=500.0,
        avg_buy_price_sol=0.04,
        total_invested_sol=20.0,
        realized_pnl_sol=2.5,
    )
    db_session.add(portfolio)
    await db_session.flush()

    agent = Agent(
        name=f"port-agent-{uuid.uuid4().hex[:6]}",
        owner_id="test",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    jwt = create_agent_token(str(agent.id))
    return person, token, portfolio, agent, jwt, wallet


@pytest.mark.asyncio
class TestPortfolioEndpoint:
    async def test_portfolio_with_holdings(self, client, db_session, portfolio_env):
        _, token, portfolio, _, _, wallet = portfolio_env
        resp = await client.get(f"/api/v1/trading/portfolio?wallet_address={wallet}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        item = data[0]
        assert item["balance"] == 500.0
        assert item["avg_buy_price_sol"] == 0.04
        assert item["current_price_sol"] == 0.05
        assert item["unrealized_pnl_sol"] is not None
        # (0.05 - 0.04) * 500 = 5.0
        assert abs(item["unrealized_pnl_sol"] - 5.0) < 0.01

    async def test_portfolio_empty(self, client, db_session):
        resp = await client.get("/api/v1/trading/portfolio?wallet_address=NONEXISTENT")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
class TestSellRiskAlerts:
    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    async def test_sell_with_risk_alerts_logged(
        self, mock_risk, client, db_session, portfolio_env
    ):
        """Risk alerts after sell are logged but trade still succeeds."""
        mock_risk.return_value = [{"type": "unusual_volume", "severity": "warning"}]
        person, _, _, _, jwt, _ = portfolio_env
        resp = await client.post(
            "/api/v1/trading/sell",
            json={
                "person_id": str(person.id),
                "side": "sell",
                "amount": 100.0,
                "trader_address": "I" * 44,
            },
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 201


@pytest.mark.asyncio
class TestTradeHistory:
    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    async def test_history_filtered_by_trader(
        self, mock_risk, client, db_session, portfolio_env
    ):
        person, _, _, _, jwt, _ = portfolio_env
        addr = "J" * 44
        # Create a trade first
        await client.post(
            "/api/v1/trading/buy",
            json={
                "person_id": str(person.id),
                "side": "buy",
                "amount": 1.0,
                "trader_address": addr,
            },
            headers={"Authorization": f"Bearer {jwt}"},
        )
        resp = await client.get(f"/api/v1/trading/history?trader_address={addr}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all(t["trader_address"] == addr for t in data)
