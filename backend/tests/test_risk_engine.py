"""Tests for risk_engine — wash trade detection, pump/dump, cliff events, circuit breakers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from nile.models.person import Person
from nile.models.soul_token import SoulToken
from nile.models.trade import Trade
from nile.services.risk_engine import (
    _active_breakers,
    activate_circuit_breaker,
    check_cliff_event,
    check_pump_and_dump,
    check_wash_trading,
    get_active_breakers,
    get_token_risk_summary,
    is_circuit_breaker_active,
    run_risk_checks,
)

# ── Circuit breaker tests ────────────────────────────────────────


class TestCircuitBreaker:
    def setup_method(self):
        _active_breakers.clear()

    def test_not_active_by_default(self):
        assert is_circuit_breaker_active("token-1") is False

    def test_activate_and_check(self):
        expiry = activate_circuit_breaker("token-1", minutes=5)
        assert is_circuit_breaker_active("token-1") is True
        assert expiry > datetime.now(UTC)

    def test_expired_breaker_returns_false(self):
        _active_breakers["token-1"] = datetime.now(UTC) - timedelta(minutes=1)
        assert is_circuit_breaker_active("token-1") is False
        assert "token-1" not in _active_breakers

    def test_get_active_breakers_filters_expired(self):
        _active_breakers["active"] = datetime.now(UTC) + timedelta(minutes=10)
        _active_breakers["expired"] = datetime.now(UTC) - timedelta(minutes=1)
        result = get_active_breakers()
        assert "active" in result
        assert "expired" not in result


# ── Wash trade detection ─────────────────────────────────────────


@pytest.fixture
def soul_token_setup(db_session):
    """Create a person + soul token for risk tests."""

    async def _create():
        person = Person(display_name="Risk Test Person", slug="risk-test", category="athlete")
        db_session.add(person)
        await db_session.flush()

        token = SoulToken(
            person_id=person.id,
            name="Risk Token",
            symbol="RISK",
            phase="bonding",
        )
        db_session.add(token)
        await db_session.flush()
        return token

    return _create


@pytest.mark.asyncio
class TestCheckWashTrading:
    async def test_no_trades_returns_none(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        result = await check_wash_trading(
            db_session, soul_token_id=token.id, trader_address="wallet1"
        )
        assert result is None

    async def test_single_trade_returns_none(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=100,
                sol_amount=1.0,
                price_sol=0.01,
                price_usd=2.5,
                trader_address="wallet1",
            )
        )
        await db_session.flush()
        result = await check_wash_trading(
            db_session, soul_token_id=token.id, trader_address="wallet1"
        )
        assert result is None

    async def test_buy_sell_same_amount_detects_wash(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        for side in ("buy", "sell"):
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side=side,
                    token_amount=100,
                    sol_amount=1.0,
                    price_sol=0.01,
                    price_usd=2.5,
                    trader_address="wash_wallet",
                )
            )
        await db_session.flush()
        result = await check_wash_trading(
            db_session, soul_token_id=token.id, trader_address="wash_wallet"
        )
        assert result is not None
        assert result["risk_type"] == "wash_trading"
        assert result["ratio"] >= 0.8

    async def test_only_buys_not_detected(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        for _i in range(3):
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="buy",
                    token_amount=100,
                    sol_amount=1.0,
                    price_sol=0.01,
                    price_usd=2.5,
                    trader_address="buyer",
                )
            )
        await db_session.flush()
        result = await check_wash_trading(
            db_session, soul_token_id=token.id, trader_address="buyer"
        )
        assert result is None


# ── Pump and dump detection ──────────────────────────────────────


@pytest.mark.asyncio
class TestCheckPumpAndDump:
    async def test_few_trades_returns_none(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=100,
                sol_amount=1.0,
                price_sol=0.01,
                price_usd=2.5,
                trader_address="wallet1",
            )
        )
        await db_session.flush()
        result = await check_pump_and_dump(db_session, soul_token_id=token.id)
        assert result is None

    async def test_large_price_increase_concentrated_detects(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        now = datetime.now(UTC)
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=100,
                sol_amount=1.0,
                price_sol=1.0,
                price_usd=250,
                trader_address="pumper",
                created_at=now - timedelta(minutes=30),
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=50,
                sol_amount=5.0,
                price_sol=1.5,
                price_usd=375,
                trader_address="pumper",
                created_at=now - timedelta(minutes=15),
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=20,
                sol_amount=4.0,
                price_sol=2.0,
                price_usd=500,
                trader_address="pumper",
                created_at=now - timedelta(minutes=1),
            )
        )
        await db_session.flush()
        result = await check_pump_and_dump(db_session, soul_token_id=token.id)
        assert result is not None
        assert result["risk_type"] == "pump_and_dump"
        assert result["severity"] == "critical"

    async def test_stable_prices_not_detected(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        now = datetime.now(UTC)
        for i in range(4):
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="buy",
                    token_amount=100,
                    sol_amount=1.0,
                    price_sol=1.0,
                    price_usd=250,
                    trader_address=f"wallet{i}",
                    created_at=now - timedelta(minutes=i * 10),
                )
            )
        await db_session.flush()
        result = await check_pump_and_dump(db_session, soul_token_id=token.id)
        assert result is None


# ── Cliff event detection ────────────────────────────────────────


@pytest.mark.asyncio
class TestCheckCliffEvent:
    async def test_price_drop_over_30pct_detects(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        now = datetime.now(UTC)
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=1000,
                sol_amount=10.0,
                price_sol=1.0,
                price_usd=250,
                trader_address="seller",
                created_at=now - timedelta(minutes=5),
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=500,
                sol_amount=2.0,
                price_sol=0.5,
                price_usd=125,
                trader_address="seller2",
                created_at=now - timedelta(seconds=30),
            )
        )
        await db_session.flush()
        result = await check_cliff_event(db_session, soul_token_id=token.id)
        assert result is not None
        assert result["risk_type"] == "cliff_event"
        assert result["severity"] == "critical"

    async def test_no_drop_returns_none(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        now = datetime.now(UTC)
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=100,
                sol_amount=1.0,
                price_sol=1.0,
                price_usd=250,
                trader_address="buyer",
                created_at=now - timedelta(minutes=5),
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=50,
                sol_amount=0.6,
                price_sol=1.2,
                price_usd=300,
                trader_address="buyer2",
                created_at=now - timedelta(seconds=30),
            )
        )
        await db_session.flush()
        result = await check_cliff_event(db_session, soul_token_id=token.id)
        assert result is None


# ── Run risk checks integration ──────────────────────────────────


@pytest.mark.asyncio
class TestRunRiskChecks:
    def setup_method(self):
        _active_breakers.clear()

    @patch("nile.services.risk_engine.risk_to_circuit_breaker", new_callable=AsyncMock)
    async def test_critical_alert_activates_breaker(self, mock_cb, db_session, soul_token_setup):
        token = await soul_token_setup()
        now = datetime.now(UTC)
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=1000,
                sol_amount=10.0,
                price_sol=1.0,
                price_usd=250,
                trader_address="seller",
                created_at=now - timedelta(minutes=5),
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=500,
                sol_amount=2.0,
                price_sol=0.5,
                price_usd=125,
                trader_address="seller",
                created_at=now - timedelta(seconds=30),
            )
        )
        await db_session.flush()

        alerts = await run_risk_checks(
            db_session, soul_token_id=token.id, trader_address="seller"
        )
        assert any(a["severity"] == "critical" for a in alerts)
        assert is_circuit_breaker_active(str(token.id))  # breaker keyed by str


# ── Token risk summary ───────────────────────────────────────────


@pytest.mark.asyncio
class TestGetTokenRiskSummary:
    def setup_method(self):
        _active_breakers.clear()

    async def test_returns_summary(self, db_session, soul_token_setup):
        token = await soul_token_setup()
        summary = await get_token_risk_summary(db_session, token.id)
        assert summary["circuit_breaker_active"] is False
        assert summary["last_hour"]["trade_count"] == 0
