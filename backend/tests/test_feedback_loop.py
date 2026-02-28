"""Tests for feedback_loop — agent accuracy tracking and cross-verification."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution
from nile.services.feedback_loop import get_agent_accuracy, verify_contribution


@pytest.fixture
async def agent_with_contributions(db_session):
    """Create an agent with some detection contributions."""
    agent = Agent(name="accuracy-agent", owner_id="owner-1", status="active")
    db_session.add(agent)
    await db_session.flush()

    # 8 verified detections
    for _i in range(8):
        db_session.add(
            AgentContribution(
                agent_id=agent.id,
                contribution_type="detection",
                severity_found="high",
                points_awarded=50,
                verified=True,
            )
        )

    # 2 false positives (negative points)
    for _i in range(2):
        db_session.add(
            AgentContribution(
                agent_id=agent.id,
                contribution_type="detection",
                severity_found="medium",
                points_awarded=-20,
                verified=False,
            )
        )

    await db_session.flush()
    return agent


@pytest.mark.asyncio
class TestGetAgentAccuracy:
    async def test_no_contributions(self, db_session):
        agent = Agent(name="empty-agent", owner_id="owner-1", status="active")
        db_session.add(agent)
        await db_session.flush()

        metrics = await get_agent_accuracy(db_session, agent.id)
        assert metrics["total_detections"] == 0
        assert metrics["precision"] == 0.0
        assert metrics["false_positive_rate"] == 0.0

    async def test_mixed_contributions(self, db_session, agent_with_contributions):
        agent = agent_with_contributions
        metrics = await get_agent_accuracy(db_session, agent.id)

        assert metrics["total_detections"] == 10
        assert metrics["verified_detections"] == 8
        assert metrics["false_positives"] == 2
        assert metrics["precision"] == 0.8
        assert metrics["false_positive_rate"] == 0.2

    async def test_only_counts_detections(self, db_session):
        agent = Agent(name="mixed-agent", owner_id="owner-1", status="active")
        db_session.add(agent)
        await db_session.flush()

        # Add a patch contribution (should be excluded)
        db_session.add(
            AgentContribution(
                agent_id=agent.id,
                contribution_type="patch",
                points_awarded=75,
                verified=True,
            )
        )
        # Add a detection contribution
        db_session.add(
            AgentContribution(
                agent_id=agent.id,
                contribution_type="detection",
                severity_found="low",
                points_awarded=10,
                verified=True,
            )
        )
        await db_session.flush()

        metrics = await get_agent_accuracy(db_session, agent.id)
        assert metrics["total_detections"] == 1  # only detection, not patch


@pytest.mark.asyncio
class TestVerifyContribution:
    @patch("nile.services.feedback_loop.publish_event", new_callable=AsyncMock)
    @patch("nile.services.incentive_engine.penalize_false_positive", new_callable=AsyncMock)
    async def test_verify_valid(self, mock_penalize, mock_pub, db_session):
        agent = Agent(name="verify-agent", owner_id="owner-1", status="active")
        db_session.add(agent)
        await db_session.flush()

        contrib = AgentContribution(
            agent_id=agent.id,
            contribution_type="detection",
            severity_found="high",
            points_awarded=50,
        )
        db_session.add(contrib)
        await db_session.flush()

        await verify_contribution(
            db_session,
            contribution_id=contrib.id,
            verifier_agent_id="verifier-1",
            is_valid=True,
        )

        # Check contribution marked as verified
        result = await db_session.execute(
            select(AgentContribution).where(AgentContribution.id == contrib.id)
        )
        updated = result.scalar_one()
        assert updated.verified is True

        # Should publish verified event, NOT penalize
        mock_pub.assert_called_once()
        assert mock_pub.call_args.kwargs["event_type"] == "contribution.verified"
        mock_penalize.assert_not_called()

    @patch("nile.services.feedback_loop.publish_event", new_callable=AsyncMock)
    @patch("nile.services.incentive_engine.penalize_false_positive", new_callable=AsyncMock)
    async def test_verify_invalid_triggers_penalty(self, mock_penalize, mock_pub, db_session):
        agent = Agent(name="rejected-agent", owner_id="owner-1", status="active")
        db_session.add(agent)
        await db_session.flush()

        contrib = AgentContribution(
            agent_id=agent.id,
            contribution_type="detection",
            severity_found="medium",
            points_awarded=25,
        )
        db_session.add(contrib)
        await db_session.flush()

        await verify_contribution(
            db_session,
            contribution_id=contrib.id,
            verifier_agent_id="verifier-1",
            is_valid=False,
        )

        mock_pub.assert_called_once()
        assert mock_pub.call_args.kwargs["event_type"] == "contribution.rejected"
        mock_penalize.assert_called_once_with(db_session, str(contrib.id))

    @patch("nile.services.feedback_loop.publish_event", new_callable=AsyncMock)
    async def test_nonexistent_contribution_does_nothing(self, mock_pub, db_session):
        await verify_contribution(
            db_session,
            contribution_id=uuid.uuid4(),
            verifier_agent_id="verifier-1",
            is_valid=True,
        )
        mock_pub.assert_not_called()
