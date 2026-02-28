"""Tests for event_bus — Redis-backed event publishing."""

from unittest.mock import AsyncMock, patch

import pytest

from nile.core.event_bus import publish_event


@pytest.mark.asyncio
class TestPublishEvent:
    @patch("nile.core.event_bus.get_redis")
    async def test_publishes_to_redis(self, mock_get_redis):
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        result = await publish_event(
            event_type="scan.completed",
            actor_id="agent-1",
            target_id="contract-1",
            metadata={"score": 85},
        )

        assert result["event_type"] == "scan.completed"
        assert result["actor_id"] == "agent-1"
        assert result["metadata"]["score"] == 85
        # Should publish to both nile:events and nile:event:scan
        assert mock_redis.publish.call_count == 2

    @patch("nile.core.event_bus.get_redis")
    async def test_publishes_to_type_specific_channel(self, mock_get_redis):
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        await publish_event(event_type="task.claimed")

        calls = mock_redis.publish.call_args_list
        channels = [c.args[0] for c in calls]
        assert "nile:events" in channels
        assert "nile:event:task" in channels

    @patch("nile.core.event_bus.get_redis")
    async def test_persists_to_db_when_session_provided(self, mock_get_redis, db_session):
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        result = await publish_event(
            event_type="test.event",
            db=db_session,
        )

        assert "id" in result
        mock_redis.publish.assert_called()

    @patch("nile.core.event_bus.get_redis")
    async def test_no_db_session_skips_persistence(self, mock_get_redis):
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        result = await publish_event(event_type="test.nodb")
        assert "id" not in result
