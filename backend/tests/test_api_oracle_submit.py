"""Tests for oracle report submission (auth-required endpoint)."""

import uuid

import pytest

from nile.core.auth import create_agent_token
from nile.models.agent import Agent
from nile.models.oracle_event import OracleEvent
from nile.models.person import Person


@pytest.fixture
async def oracle_setup(db_session):
    """Person + authenticated agent for oracle tests."""
    person = Person(
        display_name="Oracle Subject",
        slug=f"oracle-sub-{uuid.uuid4().hex[:6]}",
        category="athlete",
    )
    db_session.add(person)

    agent = Agent(
        name=f"oracle-agent-{uuid.uuid4().hex[:6]}",
        owner_id="test",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    token = create_agent_token(str(agent.id))
    return person, agent, token


@pytest.mark.asyncio
class TestSubmitReport:
    async def test_unauthenticated(self, client):
        resp = await client.post(
            "/api/v1/oracle/reports",
            json={
                "person_id": str(uuid.uuid4()),
                "event_type": "sports_win",
                "source": "espn",
                "headline": "Won game",
                "impact_score": 50,
            },
        )
        assert resp.status_code == 401

    async def test_submit_success(self, client, db_session, oracle_setup):
        person, agent, token = oracle_setup
        resp = await client.post(
            "/api/v1/oracle/reports",
            json={
                "person_id": str(person.id),
                "event_type": "sports_win",
                "source": "espn",
                "headline": "Won championship game",
                "impact_score": 80,
                "confidence": 0.9,
                "agent_id": str(agent.id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_type"] == "sports_win"
        assert data["status"] == "pending"
        assert data["confirmations"] == 1

    async def test_submit_no_agent_id(self, client, db_session, oracle_setup):
        person, _, token = oracle_setup
        resp = await client.post(
            "/api/v1/oracle/reports",
            json={
                "person_id": str(person.id),
                "event_type": "scandal",
                "source": "twitter",
                "headline": "Bad news",
                "impact_score": -50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["impact_score"] == -50


@pytest.mark.asyncio
class TestVoteOnReportExtended:
    async def test_vote_reject(self, client, db_session, oracle_setup):
        """Rejection vote increments rejections."""
        person, _, token = oracle_setup
        headers = {"Authorization": f"Bearer {token}"}
        event = OracleEvent(
            person_id=person.id,
            event_type="news_positive",
            source="reuters",
            headline="Good news",
            impact_score=30,
            confidence=0.7,
            status="pending",
            confirmations=1,
            rejections=0,
            required_confirmations=3,
        )
        db_session.add(event)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/oracle/reports/{event.id}/vote",
            json={"agent_id": "voter-1", "approve": False, "impact_score": 20},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rejections"] == 1

    async def test_vote_on_confirmed_report(self, client, db_session, oracle_setup):
        """Voting on a confirmed report returns 409."""
        person, _, token = oracle_setup
        headers = {"Authorization": f"Bearer {token}"}
        event = OracleEvent(
            person_id=person.id,
            event_type="sports_win",
            source="espn",
            headline="Old event",
            impact_score=50,
            confidence=0.8,
            status="confirmed",
            confirmations=3,
            rejections=0,
        )
        db_session.add(event)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/oracle/reports/{event.id}/vote",
            json={"agent_id": "late-voter", "approve": True},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_vote_reaches_rejection(self, client, db_session, oracle_setup):
        """Enough rejections marks report as rejected."""
        person, _, token = oracle_setup
        headers = {"Authorization": f"Bearer {token}"}
        event = OracleEvent(
            person_id=person.id,
            event_type="scandal",
            source="twitter",
            headline="Disputed",
            impact_score=-40,
            confidence=0.5,
            status="pending",
            confirmations=0,
            rejections=1,
            required_confirmations=2,
            agent_votes={"agent-a": {"approve": False, "impact": -40}},
        )
        db_session.add(event)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/oracle/reports/{event.id}/vote",
            json={"agent_id": "agent-b", "approve": False},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
