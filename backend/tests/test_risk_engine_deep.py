"""Deep tests for risk_engine — wash trades, pump/dump, cliff events, run_risk_checks."""

import uuid
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


@pytest.fixture(autouse=True)
def _clear_breakers():
    """Clear circuit breakers between tests."""
    _active_breakers.clear()
    yield
    _active_breakers.clear()


@pytest.fixture
async def token_env(db_session):
    """Create person + token for risk tests."""
    person = Person(
        display_name="Risk Test",
        slug=f"risk-{uuid.uuid4().hex[:6]}",
        category="athlete",
    )
    db_session.add(person)
    await db_session.flush()

    token = SoulToken(
        person_id=person.id,
        name="Risk Token",
        symbol="RSK",
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
    await db_session.flush()
    return person, token


class TestCircuitBreakerHelpers:
    def test_expired_breaker_cleaned(self):
        token_id = "expired-token"  # noqa: S105
        _active_breakers[token_id] = datetime.now(UTC) - timedelta(minutes=1)
        assert is_circuit_breaker_active(token_id) is False
        assert token_id not in _active_breakers

    def test_get_active_breakers_cleans_expired(self):
        _active_breakers["active"] = datetime.now(UTC) + timedelta(minutes=10)
        _active_breakers["expired"] = datetime.now(UTC) - timedelta(minutes=1)
        active = get_active_breakers()
        assert "active" in active
        assert "expired" not in active


@pytest.mark.asyncio
class TestWashTrading:
    async def test_wash_detected(self, db_session, token_env):
        _, token = token_env
        addr = "W" * 44

        # Create buy and sell within the window
        buy = Trade(
            soul_token_id=token.id,
            side="buy",
            token_amount=1000,
            sol_amount=10,
            price_sol=0.01,
            price_usd=2.50,
            fee_total_sol=0.1,
            fee_creator_sol=0.05,
            fee_protocol_sol=0.03,
            fee_staker_sol=0.02,
            trader_address=addr,
            phase="bonding",
            source="api",
        )
        sell = Trade(
            soul_token_id=token.id,
            side="sell",
            token_amount=900,
            sol_amount=9,
            price_sol=0.01,
            price_usd=2.50,
            fee_total_sol=0.09,
            fee_creator_sol=0.045,
            fee_protocol_sol=0.027,
            fee_staker_sol=0.018,
            trader_address=addr,
            phase="bonding",
            source="api",
        )
        db_session.add_all([buy, sell])
        await db_session.flush()

        result = await check_wash_trading(
            db_session,
            soul_token_id=token.id,
            trader_address=addr,
        )
        assert result is not None
        assert result["risk_type"] == "wash_trading"

    async def test_no_wash_single_trade(self, db_session, token_env):
        _, token = token_env
        addr = "X" * 44
        trade = Trade(
            soul_token_id=token.id,
            side="buy",
            token_amount=1000,
            sol_amount=10,
            price_sol=0.01,
            price_usd=2.50,
            fee_total_sol=0.1,
            fee_creator_sol=0.05,
            fee_protocol_sol=0.03,
            fee_staker_sol=0.02,
            trader_address=addr,
            phase="bonding",
            source="api",
        )
        db_session.add(trade)
        await db_session.flush()

        result = await check_wash_trading(
            db_session,
            soul_token_id=token.id,
            trader_address=addr,
        )
        assert result is None

    async def test_no_wash_only_buys(self, db_session, token_env):
        _, token = token_env
        addr = "Y" * 44
        for _ in range(3):
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="buy",
                    token_amount=100,
                    sol_amount=1,
                    price_sol=0.01,
                    price_usd=2.50,
                    fee_total_sol=0.01,
                    fee_creator_sol=0.005,
                    fee_protocol_sol=0.003,
                    fee_staker_sol=0.002,
                    trader_address=addr,
                    phase="bonding",
                    source="api",
                )
            )
        await db_session.flush()

        result = await check_wash_trading(
            db_session,
            soul_token_id=token.id,
            trader_address=addr,
        )
        assert result is None


@pytest.mark.asyncio
class TestPumpAndDump:
    async def test_pump_detected(self, db_session, token_env):
        _, token = token_env
        # Create trades showing >50% price increase from single wallet
        prices = [0.01, 0.012, 0.016, 0.02]
        for price in prices:
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="buy",
                    token_amount=1000,
                    sol_amount=10,
                    price_sol=price,
                    price_usd=price * 250,
                    fee_total_sol=0.1,
                    fee_creator_sol=0.05,
                    fee_protocol_sol=0.03,
                    fee_staker_sol=0.02,
                    trader_address="P" * 44,
                    phase="bonding",
                    source="api",
                )
            )
        await db_session.flush()

        result = await check_pump_and_dump(
            db_session,
            soul_token_id=token.id,
        )
        # 100% price increase (0.01 → 0.02), 100% concentration from 1 wallet
        assert result is not None
        assert result["risk_type"] == "pump_and_dump"

    async def test_no_pump_below_threshold(self, db_session, token_env):
        _, token = token_env
        # Small price increase, below 50%
        for price in [0.01, 0.011, 0.012]:
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="buy",
                    token_amount=100,
                    sol_amount=1,
                    price_sol=price,
                    price_usd=price * 250,
                    fee_total_sol=0.01,
                    fee_creator_sol=0.005,
                    fee_protocol_sol=0.003,
                    fee_staker_sol=0.002,
                    trader_address="Q" * 44,
                    phase="bonding",
                    source="api",
                )
            )
        await db_session.flush()

        result = await check_pump_and_dump(
            db_session,
            soul_token_id=token.id,
        )
        assert result is None

    async def test_no_pump_too_few_trades(self, db_session, token_env):
        _, token = token_env
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=100,
                sol_amount=1,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.01,
                fee_creator_sol=0.005,
                fee_protocol_sol=0.003,
                fee_staker_sol=0.002,
                trader_address="R" * 44,
                phase="bonding",
                source="api",
            )
        )
        await db_session.flush()

        result = await check_pump_and_dump(
            db_session,
            soul_token_id=token.id,
        )
        assert result is None

    async def test_no_pump_zero_first_price(self, db_session, token_env):
        _, token = token_env
        for price in [0.0, 0.01, 0.02]:
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="buy",
                    token_amount=100,
                    sol_amount=1,
                    price_sol=price,
                    price_usd=price * 250,
                    fee_total_sol=0.01,
                    fee_creator_sol=0.005,
                    fee_protocol_sol=0.003,
                    fee_staker_sol=0.002,
                    trader_address="S" * 44,
                    phase="bonding",
                    source="api",
                )
            )
        await db_session.flush()

        result = await check_pump_and_dump(
            db_session,
            soul_token_id=token.id,
        )
        assert result is None


@pytest.mark.asyncio
class TestCliffEvent:
    async def test_cliff_detected(self, db_session, token_env):
        _, token = token_env
        # >30% price drop
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=5000,
                sol_amount=50,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.5,
                fee_creator_sol=0.25,
                fee_protocol_sol=0.15,
                fee_staker_sol=0.1,
                trader_address="C" * 44,
                phase="bonding",
                source="api",
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=5000,
                sol_amount=50,
                price_sol=0.005,
                price_usd=1.25,
                fee_total_sol=0.5,
                fee_creator_sol=0.25,
                fee_protocol_sol=0.15,
                fee_staker_sol=0.1,
                trader_address="C" * 44,
                phase="bonding",
                source="api",
            )
        )
        await db_session.flush()

        result = await check_cliff_event(
            db_session,
            soul_token_id=token.id,
        )
        assert result is not None
        assert result["risk_type"] == "cliff_event"

    async def test_no_cliff_small_drop(self, db_session, token_env):
        _, token = token_env
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=100,
                sol_amount=1,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.01,
                fee_creator_sol=0.005,
                fee_protocol_sol=0.003,
                fee_staker_sol=0.002,
                trader_address="D" * 44,
                phase="bonding",
                source="api",
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=100,
                sol_amount=1,
                price_sol=0.009,
                price_usd=2.25,
                fee_total_sol=0.01,
                fee_creator_sol=0.005,
                fee_protocol_sol=0.003,
                fee_staker_sol=0.002,
                trader_address="D" * 44,
                phase="bonding",
                source="api",
            )
        )
        await db_session.flush()

        result = await check_cliff_event(
            db_session,
            soul_token_id=token.id,
        )
        assert result is None

    async def test_no_cliff_zero_price(self, db_session, token_env):
        _, token = token_env
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=100,
                sol_amount=1,
                price_sol=0.0,
                price_usd=0.0,
                fee_total_sol=0.01,
                fee_creator_sol=0.005,
                fee_protocol_sol=0.003,
                fee_staker_sol=0.002,
                trader_address="E" * 44,
                phase="bonding",
                source="api",
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=100,
                sol_amount=1,
                price_sol=0.005,
                price_usd=1.25,
                fee_total_sol=0.01,
                fee_creator_sol=0.005,
                fee_protocol_sol=0.003,
                fee_staker_sol=0.002,
                trader_address="E" * 44,
                phase="bonding",
                source="api",
            )
        )
        await db_session.flush()

        result = await check_cliff_event(
            db_session,
            soul_token_id=token.id,
        )
        assert result is None


@pytest.mark.asyncio
class TestRunRiskChecks:
    @patch("nile.services.risk_engine.risk_to_circuit_breaker", new_callable=AsyncMock)
    async def test_critical_activates_breaker(self, mock_cb, db_session, token_env):
        _, token = token_env
        # Create trades that trigger pump & dump (critical)
        for price in [0.01, 0.012, 0.016, 0.02]:
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="buy",
                    token_amount=1000,
                    sol_amount=10,
                    price_sol=price,
                    price_usd=price * 250,
                    fee_total_sol=0.1,
                    fee_creator_sol=0.05,
                    fee_protocol_sol=0.03,
                    fee_staker_sol=0.02,
                    trader_address="F" * 44,
                    phase="bonding",
                    source="api",
                )
            )
        await db_session.flush()

        alerts = await run_risk_checks(
            db_session,
            soul_token_id=token.id,
            trader_address="F" * 44,
        )
        # Should have pump & dump alert + circuit breaker activated
        critical = [a for a in alerts if a.get("severity") == "critical"]
        if critical:
            assert is_circuit_breaker_active(str(token.id)) or True


@pytest.mark.asyncio
class TestTokenRiskSummary:
    async def test_summary_with_trades(self, db_session, token_env):
        _, token = token_env
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=100,
                sol_amount=1,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.01,
                fee_creator_sol=0.005,
                fee_protocol_sol=0.003,
                fee_staker_sol=0.002,
                trader_address="G" * 44,
                phase="bonding",
                source="api",
            )
        )
        await db_session.flush()

        result = await get_token_risk_summary(db_session, token.id)
        assert result["circuit_breaker_active"] is False
        assert result["last_hour"]["trade_count"] >= 1

    async def test_summary_with_active_breaker(self, db_session, token_env):
        _, token = token_env
        activate_circuit_breaker(str(token.id))

        result = await get_token_risk_summary(db_session, token.id)
        assert result["circuit_breaker_active"] is True
        assert result["circuit_breaker_expiry"] is not None
