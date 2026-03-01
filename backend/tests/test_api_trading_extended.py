"""Extended trading tests — circuit breakers, risk exceptions, portfolio with data."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from nile.core.auth import create_agent_token
from nile.models.agent import Agent
from nile.models.person import Person
from nile.models.soul_token import SoulToken


@pytest.fixture
async def trade_env(db_session):
    """Set up person + token + agent + jwt for trading tests."""
    person = Person(
        display_name="Trade Extended",
        slug=f"trade-ext-{uuid.uuid4().hex[:6]}",
        category="athlete",
    )
    db_session.add(person)
    await db_session.flush()

    token = SoulToken(
        person_id=person.id,
        name="Trade Ext Token",
        symbol="TEX",
        phase="bonding",
        chain="solana",
        current_price_sol=0.02,
        current_price_usd=5.00,
        market_cap_usd=50000.0,
        total_supply=10000000,
        reserve_balance_sol=10.0,
        graduation_threshold_sol=100.0,
    )
    db_session.add(token)

    agent = Agent(
        name=f"trader-ext-{uuid.uuid4().hex[:6]}",
        owner_id="test",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    jwt = create_agent_token(str(agent.id))
    return person, token, agent, jwt


@pytest.mark.asyncio
class TestCircuitBreaker:
    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    @patch("nile.routers.v1.trading.is_circuit_breaker_active", return_value=True)
    async def test_buy_blocked_by_circuit_breaker(
        self, mock_cb, mock_risk, client, db_session, trade_env
    ):
        person, token, _, jwt = trade_env
        resp = await client.post(
            "/api/v1/trading/buy",
            json={
                "person_id": str(person.id),
                "side": "buy",
                "amount": 1.0,
                "trader_address": "A" * 44,
            },
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 423

    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    @patch("nile.routers.v1.trading.is_circuit_breaker_active", return_value=True)
    async def test_sell_blocked_by_circuit_breaker(
        self, mock_cb, mock_risk, client, db_session, trade_env
    ):
        person, token, _, jwt = trade_env
        resp = await client.post(
            "/api/v1/trading/sell",
            json={
                "person_id": str(person.id),
                "side": "sell",
                "amount": 100.0,
                "trader_address": "B" * 44,
            },
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 423


@pytest.mark.asyncio
class TestRiskCheckExceptions:
    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    async def test_buy_risk_check_fails_gracefully(
        self, mock_risk, client, db_session, trade_env
    ):
        """Risk check exception doesn't prevent trade from completing."""
        mock_risk.side_effect = RuntimeError("Risk engine down")
        person, _, _, jwt = trade_env
        resp = await client.post(
            "/api/v1/trading/buy",
            json={
                "person_id": str(person.id),
                "side": "buy",
                "amount": 1.0,
                "trader_address": "C" * 44,
            },
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 201

    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    async def test_sell_risk_check_fails_gracefully(
        self, mock_risk, client, db_session, trade_env
    ):
        mock_risk.side_effect = RuntimeError("Risk engine down")
        person, _, _, jwt = trade_env
        resp = await client.post(
            "/api/v1/trading/sell",
            json={
                "person_id": str(person.id),
                "side": "sell",
                "amount": 100.0,
                "trader_address": "D" * 44,
            },
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 201

    @patch("nile.routers.v1.trading.run_risk_checks", new_callable=AsyncMock)
    async def test_buy_with_risk_alerts(
        self, mock_risk, client, db_session, trade_env
    ):
        """Risk alerts are returned but trade still succeeds."""
        mock_risk.return_value = [{"type": "unusual_volume", "severity": "warning"}]
        person, _, _, jwt = trade_env
        resp = await client.post(
            "/api/v1/trading/buy",
            json={
                "person_id": str(person.id),
                "side": "buy",
                "amount": 1.0,
                "trader_address": "E" * 44,
            },
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 201
