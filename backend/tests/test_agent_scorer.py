"""Tests for agent_scorer — NILE identity scoring for agents."""

import pytest
from sqlalchemy import select

from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution
from nile.services.agent_scorer import (
    AgentNileResult,
    _grade,
    compute_agent_nile_score,
    update_agent_nile_scores,
)


class TestGrade:
    def test_a_plus(self):
        assert _grade(95) == "A+"

    def test_a(self):
        assert _grade(85) == "A"

    def test_b(self):
        assert _grade(75) == "B"

    def test_c(self):
        assert _grade(65) == "C"

    def test_d(self):
        assert _grade(55) == "D"

    def test_f(self):
        assert _grade(40) == "F"

    def test_boundary_90(self):
        assert _grade(90) == "A+"

    def test_boundary_80(self):
        assert _grade(80) == "A"


@pytest.mark.asyncio
class TestComputeAgentNileScore:
    async def test_minimal_agent(self, db_session):
        agent = Agent(
            name="minimal-agent",
            owner_id="owner-1",
            status="active",
            total_points=0,
            total_contributions=0,
        )
        db_session.add(agent)
        await db_session.flush()

        result = await compute_agent_nile_score(db_session, agent.id)
        assert isinstance(result, AgentNileResult)
        assert result.total_score >= 0
        assert result.grade in ("A+", "A", "B", "C", "D", "F")

    async def test_name_score_all_fields(self, db_session):
        agent = Agent(
            name="full-agent",
            owner_id="owner-1",
            description="A fully described agent",
            version="1.2.0",
            capabilities=["detect", "patch"],
            status="active",
            total_points=0,
            total_contributions=0,
        )
        db_session.add(agent)
        await db_session.flush()

        result = await compute_agent_nile_score(db_session, agent.id)
        # name(20) + description(20) + version!=0.1.0(20) + owner(20) + caps(20) = 100
        assert result.name_score == 100.0

    async def test_image_score_with_contributions(self, db_session):
        agent = Agent(
            name="image-agent",
            owner_id="owner-1",
            status="active",
            is_online=True,
            total_points=200,
            total_contributions=5,
        )
        db_session.add(agent)
        await db_session.flush()

        # 4 verified, 1 false positive
        for _i in range(4):
            db_session.add(
                AgentContribution(
                    agent_id=agent.id,
                    contribution_type="detection",
                    severity_found="high",
                    points_awarded=50,
                    verified=True,
                )
            )
        db_session.add(
            AgentContribution(
                agent_id=agent.id,
                contribution_type="detection",
                severity_found="low",
                points_awarded=-20,
                verified=False,
            )
        )
        await db_session.flush()

        result = await compute_agent_nile_score(db_session, agent.id)
        # accuracy = 4/5 = 0.8 → 56, fp_rate = 1/5 = 0.2 → (1-0.2)*30 = 24 → 80 + online 10 = 90
        assert result.image_score >= 80

    async def test_likeness_score_by_contribution_count(self, db_session):
        agent = Agent(
            name="likeness-agent",
            owner_id="owner-1",
            status="active",
            capabilities=["detect", "patch", "exploit"],
            total_points=500,
            total_contributions=25,
        )
        db_session.add(agent)
        await db_session.flush()

        for _i in range(25):
            db_session.add(
                AgentContribution(
                    agent_id=agent.id,
                    contribution_type="detection",
                    points_awarded=20,
                    verified=True,
                )
            )
        await db_session.flush()

        result = await compute_agent_nile_score(db_session, agent.id)
        # >=1(20) + >=5(20) + >=20(20) + 3 caps * 15 = 45 (capped 40) = 100
        assert result.likeness_score == 100.0

    async def test_essence_score_high_avg(self, db_session):
        agent = Agent(
            name="essence-agent",
            owner_id="owner-1",
            status="active",
            total_points=500,
            total_contributions=5,
        )
        db_session.add(agent)
        await db_session.flush()

        for _i in range(5):
            db_session.add(
                AgentContribution(
                    agent_id=agent.id,
                    contribution_type="detection",
                    points_awarded=100,
                    verified=True,
                )
            )
        await db_session.flush()

        result = await compute_agent_nile_score(db_session, agent.id)
        # avg = 500/5 = 100, >= 50 → 80 + min((100-50)/5, 20) = 80 + 10 = 90
        assert result.essence_score >= 80

    async def test_essence_score_zero_points(self, db_session):
        agent = Agent(
            name="zero-pts",
            owner_id="owner-1",
            status="active",
            total_points=0,
            total_contributions=0,
        )
        db_session.add(agent)
        await db_session.flush()

        result = await compute_agent_nile_score(db_session, agent.id)
        assert result.essence_score == 0.0


@pytest.mark.asyncio
class TestUpdateAgentNileScores:
    async def test_persists_scores(self, db_session):
        agent = Agent(
            name="persist-agent",
            owner_id="owner-1",
            description="Test",
            version="2.0.0",
            capabilities=["detect"],
            status="active",
            total_points=100,
            total_contributions=2,
        )
        db_session.add(agent)
        await db_session.flush()

        await update_agent_nile_scores(db_session, agent.id)

        result = await db_session.execute(select(Agent).where(Agent.id == agent.id))
        updated = result.scalar_one()
        assert float(updated.nile_score_total) > 0
        assert float(updated.nile_score_name) > 0
