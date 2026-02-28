"""Tests for soul_agent_incentives — extended points for oracle/valuation/risk agents."""

import pytest
from sqlalchemy import select

from nile.models.agent import Agent
from nile.services.soul_agent_incentives import (
    SOUL_CAPABILITIES,
    SOUL_POINTS,
    award_soul_points,
    get_soul_agent_rankings,
)


class TestSoulPointsTable:
    def test_oracle_report_confirmed(self):
        assert SOUL_POINTS["oracle_report_confirmed"] == 50

    def test_oracle_report_rejected_is_negative(self):
        assert SOUL_POINTS["oracle_report_rejected"] < 0

    def test_risk_detection_critical(self):
        assert SOUL_POINTS["risk_detection_critical"] == 100

    def test_capabilities_list(self):
        assert "oracle" in SOUL_CAPABILITIES
        assert "valuation" in SOUL_CAPABILITIES
        assert "risk" in SOUL_CAPABILITIES


@pytest.mark.asyncio
class TestAwardSoulPoints:
    async def test_known_action_awards_points(self, db_session):
        agent = Agent(
            name="soul-oracle",
            owner_id="owner-1",
            status="active",
            total_points=0,
            total_contributions=0,
        )
        db_session.add(agent)
        await db_session.flush()

        points = await award_soul_points(
            db_session, agent_id=agent.id, action="oracle_report_confirmed"
        )
        assert points == 50

        result = await db_session.execute(select(Agent).where(Agent.id == agent.id))
        updated = result.scalar_one()
        assert updated.total_points == 50
        assert updated.total_contributions == 1

    async def test_negative_action_doesnt_increment_contributions(self, db_session):
        agent = Agent(
            name="soul-penalty",
            owner_id="owner-1",
            status="active",
            total_points=100,
            total_contributions=2,
        )
        db_session.add(agent)
        await db_session.flush()

        points = await award_soul_points(
            db_session, agent_id=agent.id, action="oracle_report_rejected"
        )
        assert points == -10

        result = await db_session.execute(select(Agent).where(Agent.id == agent.id))
        updated = result.scalar_one()
        assert updated.total_points == 90
        assert updated.total_contributions == 2  # unchanged

    async def test_unknown_action_returns_zero(self, db_session):
        agent = Agent(name="soul-unknown", owner_id="o1", status="active")
        db_session.add(agent)
        await db_session.flush()

        points = await award_soul_points(
            db_session, agent_id=agent.id, action="nonexistent_action"
        )
        assert points == 0

    async def test_agent_not_found_returns_zero(self, db_session):
        import uuid

        points = await award_soul_points(
            db_session, agent_id=uuid.uuid4(), action="oracle_report_confirmed"
        )
        assert points == 0


@pytest.mark.asyncio
class TestGetSoulAgentRankings:
    async def test_returns_agents_sorted_by_points(self, db_session):
        a1 = Agent(name="low-pts", owner_id="o1", status="active", total_points=10)
        a2 = Agent(name="high-pts", owner_id="o2", status="active", total_points=500)
        a3 = Agent(name="mid-pts", owner_id="o3", status="active", total_points=100)
        db_session.add_all([a1, a2, a3])
        await db_session.flush()

        rankings = await get_soul_agent_rankings(db_session)
        assert len(rankings) == 3
        assert rankings[0]["name"] == "high-pts"
        assert rankings[1]["name"] == "mid-pts"
        assert rankings[2]["name"] == "low-pts"

    async def test_respects_limit(self, db_session):
        for i in range(5):
            db_session.add(
                Agent(name=f"rank-agent-{i}", owner_id="o1", status="active", total_points=i)
            )
        await db_session.flush()

        rankings = await get_soul_agent_rankings(db_session, limit=2)
        assert len(rankings) == 2

    async def test_empty_returns_empty(self, db_session):
        rankings = await get_soul_agent_rankings(db_session)
        assert rankings == []
