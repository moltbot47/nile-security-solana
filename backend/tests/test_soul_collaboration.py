"""Tests for soul_collaboration — Redis pub/sub event pipelines between agent types."""

from unittest.mock import AsyncMock, patch

import pytest

from nile.services.soul_collaboration import (
    graduation_notification,
    oracle_consensus_broadcast,
    oracle_to_valuation,
    risk_to_circuit_breaker,
    valuation_to_market_maker,
)


@pytest.fixture
def mock_redis():
    """Mock Redis for all publish tests."""
    mock_r = AsyncMock()
    mock_r.publish = AsyncMock()
    mock_r.close = AsyncMock()
    with patch("nile.services.soul_collaboration.aioredis.from_url", return_value=mock_r):
        yield mock_r


@pytest.mark.asyncio
class TestOracleToValuation:
    async def test_publishes_event(self, mock_redis):
        await oracle_to_valuation(
            person_id="p1", event_id="e1", impact_score=50, event_type="sports_win"
        )
        mock_redis.publish.assert_called_once()
        channel, payload = mock_redis.publish.call_args.args
        assert channel == "nile:events"
        assert '"soul.oracle_confirmed"' in payload
        assert '"action": "revalue"' in payload


@pytest.mark.asyncio
class TestValuationToMarketMaker:
    async def test_significant_change_publishes(self, mock_redis):
        await valuation_to_market_maker(
            person_id="p1", old_score=50.0, new_score=60.0, fair_value_usd=5000.0
        )
        mock_redis.publish.assert_called_once()
        payload = mock_redis.publish.call_args.args[1]
        assert '"adjust_spread"' in payload

    async def test_small_change_does_not_publish(self, mock_redis):
        # 2% change < 5% threshold
        await valuation_to_market_maker(
            person_id="p1", old_score=50.0, new_score=51.0, fair_value_usd=5000.0
        )
        mock_redis.publish.assert_not_called()

    async def test_zero_old_score_uses_floor(self, mock_redis):
        # old_score=0 → divisor=max(0,1)=1 → change=100% → publishes
        await valuation_to_market_maker(
            person_id="p1", old_score=0.0, new_score=10.0, fair_value_usd=1000.0
        )
        mock_redis.publish.assert_called_once()


@pytest.mark.asyncio
class TestRiskToCircuitBreaker:
    async def test_publishes_risk_alert(self, mock_redis):
        await risk_to_circuit_breaker(
            person_id="p1",
            token_id="t1",
            risk_type="wash_trade",
            severity="critical",
            details={"volume": 100000},
        )
        mock_redis.publish.assert_called_once()
        payload = mock_redis.publish.call_args.args[1]
        assert '"circuit_breaker"' in payload
        assert '"pause_minutes": 15' in payload


@pytest.mark.asyncio
class TestOracleConsensusBroadcast:
    async def test_publishes_pending_report(self, mock_redis):
        await oracle_consensus_broadcast(
            event_id="e1",
            person_id="p1",
            headline="Test headline",
            source="twitter",
        )
        mock_redis.publish.assert_called_once()
        payload = mock_redis.publish.call_args.args[1]
        assert '"cross_verify"' in payload
        assert '"Test headline"' in payload


@pytest.mark.asyncio
class TestGraduationNotification:
    async def test_publishes_graduation(self, mock_redis):
        await graduation_notification(
            person_id="p1",
            token_id="t1",
            token_symbol="ATHLETE",
            reserve_sol=100.5,
        )
        mock_redis.publish.assert_called_once()
        payload = mock_redis.publish.call_args.args[1]
        assert '"graduation"' in payload
        assert '"ATHLETE"' in payload


@pytest.mark.asyncio
class TestPublishFailure:
    async def test_redis_failure_doesnt_raise(self):
        with patch(
            "nile.services.soul_collaboration.aioredis.from_url",
            side_effect=Exception("Redis down"),
        ):
            # Should not raise
            await oracle_to_valuation(
                person_id="p1", event_id="e1", impact_score=50, event_type="test"
            )
