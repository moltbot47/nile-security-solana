"""Tests for pattern_library — vulnerability pattern storage and retrieval."""

from unittest.mock import AsyncMock, patch

import pytest

from nile.models.agent import Agent
from nile.services.pattern_library import query_patterns, store_pattern


@pytest.fixture
async def discovery_agent(db_session):
    agent = Agent(name="discovery-agent", owner_id="owner-1", status="active")
    db_session.add(agent)
    await db_session.flush()
    return agent


@pytest.mark.asyncio
class TestStorePattern:
    @patch("nile.services.pattern_library.publish_event", new_callable=AsyncMock)
    async def test_creates_ecosystem_event(self, mock_pub, db_session, discovery_agent):
        event = await store_pattern(
            db_session,
            category="reentrancy",
            severity="critical",
            pattern_data={"signature": "call_before_update"},
            discovered_by_agent_id=discovery_agent.id,
        )

        assert event.event_type == "knowledge.pattern_added"
        assert event.metadata_["category"] == "reentrancy"
        assert event.metadata_["severity"] == "critical"
        assert event.metadata_["pattern"]["signature"] == "call_before_update"

    @patch("nile.services.pattern_library.publish_event", new_callable=AsyncMock)
    async def test_publishes_event(self, mock_pub, db_session, discovery_agent):
        await store_pattern(
            db_session,
            category="overflow",
            severity="high",
            pattern_data={},
            discovered_by_agent_id=discovery_agent.id,
        )

        mock_pub.assert_called_once()
        assert mock_pub.call_args.kwargs["event_type"] == "knowledge.pattern_added"


@pytest.mark.asyncio
class TestQueryPatterns:
    @patch("nile.services.pattern_library.publish_event", new_callable=AsyncMock)
    async def test_empty_library(self, mock_pub, db_session):
        patterns = await query_patterns(db_session)
        assert patterns == []

    @patch("nile.services.pattern_library.publish_event", new_callable=AsyncMock)
    async def test_returns_all_patterns(self, mock_pub, db_session, discovery_agent):
        await store_pattern(db_session, "reentrancy", "critical", {"sig": "a"}, discovery_agent.id)
        await store_pattern(db_session, "overflow", "high", {"sig": "b"}, discovery_agent.id)

        patterns = await query_patterns(db_session)
        assert len(patterns) == 2

    @patch("nile.services.pattern_library.publish_event", new_callable=AsyncMock)
    async def test_filter_by_category(self, mock_pub, db_session, discovery_agent):
        await store_pattern(db_session, "reentrancy", "critical", {}, discovery_agent.id)
        await store_pattern(db_session, "overflow", "high", {}, discovery_agent.id)

        patterns = await query_patterns(db_session, category="reentrancy")
        assert len(patterns) == 1
        assert patterns[0]["category"] == "reentrancy"

    @patch("nile.services.pattern_library.publish_event", new_callable=AsyncMock)
    async def test_filter_by_severity(self, mock_pub, db_session, discovery_agent):
        await store_pattern(db_session, "reentrancy", "critical", {}, discovery_agent.id)
        await store_pattern(db_session, "overflow", "high", {}, discovery_agent.id)

        patterns = await query_patterns(db_session, severity="high")
        assert len(patterns) == 1
        assert patterns[0]["severity"] == "high"

    @patch("nile.services.pattern_library.publish_event", new_callable=AsyncMock)
    async def test_respects_limit(self, mock_pub, db_session, discovery_agent):
        for i in range(5):
            await store_pattern(db_session, "type", "low", {"i": i}, discovery_agent.id)

        patterns = await query_patterns(db_session, limit=3)
        # limit applies at SQL level, but filter is in-memory, so we get at most 3
        assert len(patterns) <= 3

    @patch("nile.services.pattern_library.publish_event", new_callable=AsyncMock)
    async def test_pattern_data_preserved(self, mock_pub, db_session, discovery_agent):
        original = {"signature": "test_sig", "opcode_sequence": [1, 2, 3]}
        await store_pattern(db_session, "custom", "medium", original, discovery_agent.id)

        patterns = await query_patterns(db_session, category="custom")
        assert len(patterns) == 1
        assert patterns[0]["pattern"] == original
