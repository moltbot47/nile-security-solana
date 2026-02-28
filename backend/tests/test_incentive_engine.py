"""Tests for incentive_engine — agent points system."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution
from nile.services.incentive_engine import (
    FALSE_POSITIVE_PENALTY,
    award_contribution,
    calculate_points,
    penalize_false_positive,
)

# ── Pure function tests ─────────────────────────────────────────


class TestCalculatePoints:
    def test_detection_critical(self):
        assert calculate_points("detection", "critical") == 100

    def test_detection_high(self):
        assert calculate_points("detection", "high") == 50

    def test_detection_medium(self):
        assert calculate_points("detection", "medium") == 25

    def test_detection_low(self):
        assert calculate_points("detection", "low") == 10

    def test_patch_no_severity(self):
        assert calculate_points("patch") == 75

    def test_exploit_no_severity(self):
        assert calculate_points("exploit") == 60

    def test_verification_no_severity(self):
        assert calculate_points("verification") == 15

    def test_unknown_type_returns_zero(self):
        assert calculate_points("unknown_type") == 0

    def test_detection_with_unknown_severity_falls_back(self):
        # detection + unknown severity → no exact match, no (detection, None) → tries fallback
        assert calculate_points("detection", "unknown") == 0

    def test_patch_ignores_severity(self):
        # patch with a severity → no exact match → falls back to (patch, None) = 75
        assert calculate_points("patch", "critical") == 75


# ── DB-dependent tests ──────────────────────────────────────────


@pytest.mark.asyncio
class TestAwardContribution:
    @patch("nile.services.incentive_engine.publish_event", new_callable=AsyncMock)
    async def test_creates_contribution_record(self, mock_pub, db_session):
        agent = Agent(
            name="test-agent",
            owner_id="owner-1",
            status="active",
        )
        db_session.add(agent)
        await db_session.flush()

        contribution = await award_contribution(
            db_session,
            agent_id=agent.id,
            contribution_type="detection",
            severity_found="high",
        )

        assert contribution.points_awarded == 50
        assert contribution.contribution_type == "detection"
        assert contribution.severity_found == "high"

    @patch("nile.services.incentive_engine.publish_event", new_callable=AsyncMock)
    async def test_updates_agent_stats(self, mock_pub, db_session):
        agent = Agent(
            name="stats-agent",
            owner_id="owner-1",
            status="active",
            total_points=0,
            total_contributions=0,
        )
        db_session.add(agent)
        await db_session.flush()

        await award_contribution(
            db_session,
            agent_id=agent.id,
            contribution_type="detection",
            severity_found="critical",
        )

        result = await db_session.execute(select(Agent).where(Agent.id == agent.id))
        refreshed = result.scalar_one()
        assert refreshed.total_points == 100
        assert refreshed.total_contributions == 1

    @patch("nile.services.incentive_engine.publish_event", new_callable=AsyncMock)
    async def test_publishes_event(self, mock_pub, db_session):
        agent = Agent(name="event-agent", owner_id="owner-1", status="active")
        db_session.add(agent)
        await db_session.flush()

        await award_contribution(
            db_session,
            agent_id=agent.id,
            contribution_type="patch",
        )

        mock_pub.assert_called_once()
        call_kwargs = mock_pub.call_args
        assert call_kwargs.kwargs["event_type"] == "contribution.patch"

    @patch("nile.services.incentive_engine.publish_event", new_callable=AsyncMock)
    async def test_agent_not_found_still_creates_contribution(self, mock_pub, db_session):
        fake_id = uuid.uuid4()
        contribution = await award_contribution(
            db_session,
            agent_id=fake_id,
            contribution_type="verification",
        )
        assert contribution.points_awarded == 15


@pytest.mark.asyncio
class TestPenalizeFalsePositive:
    @patch("nile.services.incentive_engine.publish_event", new_callable=AsyncMock)
    async def test_reverses_points_and_applies_penalty(self, mock_pub, db_session):
        agent = Agent(
            name="penalty-agent",
            owner_id="owner-1",
            status="active",
            total_points=100,
            total_contributions=1,
        )
        db_session.add(agent)
        await db_session.flush()

        contrib = AgentContribution(
            agent_id=agent.id,
            contribution_type="detection",
            severity_found="critical",
            points_awarded=100,
        )
        db_session.add(contrib)
        await db_session.flush()

        await penalize_false_positive(db_session, contrib.id)

        # Contribution now has penalty
        result = await db_session.execute(
            select(AgentContribution).where(AgentContribution.id == contrib.id)
        )
        updated = result.scalar_one()
        assert updated.points_awarded == FALSE_POSITIVE_PENALTY
        assert updated.verified is False

        # Agent points: 100 - 100 (reverse) + (-20) penalty = -20
        result = await db_session.execute(select(Agent).where(Agent.id == agent.id))
        agent_updated = result.scalar_one()
        assert agent_updated.total_points == -20

    @patch("nile.services.incentive_engine.publish_event", new_callable=AsyncMock)
    async def test_nonexistent_contribution_does_nothing(self, mock_pub, db_session):
        fake_id = uuid.uuid4()
        await penalize_false_positive(db_session, fake_id)
        mock_pub.assert_not_called()
