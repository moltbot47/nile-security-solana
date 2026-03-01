"""Tests for event_bus — SSE event stream and Redis initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestGetRedis:
    @patch("nile.core.event_bus._redis", None)
    @patch("nile.core.event_bus.aioredis")
    async def test_creates_redis_once(self, mock_aioredis):
        mock_client = MagicMock()
        mock_aioredis.from_url.return_value = mock_client

        from nile.core.event_bus import get_redis

        result = await get_redis()
        assert result is mock_client
        mock_aioredis.from_url.assert_called_once()


@pytest.mark.asyncio
class TestEventStream:
    async def test_yields_messages(self):
        from nile.core.event_bus import event_stream

        mock_pubsub = AsyncMock()

        # Simulate one message then stop
        messages = [
            {"type": "subscribe", "data": None},
            {"type": "message", "data": '{"event_type":"test"}'},
        ]

        async def mock_listen():
            for m in messages:
                yield m

        mock_pubsub.listen = mock_listen
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        async def mock_get_redis():
            return mock_redis

        with patch(
            "nile.core.event_bus.get_redis",
            side_effect=mock_get_redis,
        ):
            collected = []
            async for event in event_stream():
                collected.append(event)
                break  # Stop after first data message

            assert len(collected) == 1
            assert "test" in collected[0]
