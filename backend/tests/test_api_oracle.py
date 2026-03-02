"""Tests for oracle API endpoints."""

import uuid

import pytest

from nile.models.agent import Agent
from nile.models.oracle_event import OracleEvent
from nile.models.person import Person


@pytest.fixture
async def oracle_submitter(db_session):
    """Create a separate agent that submitted the oracle report."""
    agent = Agent(
        name="oracle-submitter",
        owner_id="test-owner",
        capabilities=["detect"],
        status="active",
        api_key_hash="submitterhash",
    )
    db_session.add(agent)
    await db_session.flush()
    return agent


@pytest.fixture
async def person_and_event(db_session, oracle_submitter):
    """Create a person and a pending oracle event."""
    person = Person(
        display_name="Oracle Test Person",
        slug="oracle-test",
        category="athlete",
    )
    db_session.add(person)
    await db_session.flush()

    submitter_id = str(oracle_submitter.id)
    event = OracleEvent(
        person_id=person.id,
        event_type="sports_win",
        source="twitter",
        headline="Won championship",
        impact_score=80,
        confidence=0.9,
        status="pending",
        confirmations=1,
        rejections=0,
        required_confirmations=3,
        agent_votes={submitter_id: {"approve": True, "impact": 80, "submitter": True}},
    )
    db_session.add(event)
    await db_session.flush()
    return person, event


@pytest.mark.asyncio
class TestListReports:
    async def test_empty_list(self, client):
        resp = await client.get("/api/v1/oracle/reports")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_with_events(self, client, db_session, person_and_event):
        resp = await client.get("/api/v1/oracle/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["status"] == "pending"

    async def test_filter_by_status(self, client, db_session, person_and_event):
        resp = await client.get("/api/v1/oracle/reports?status=pending")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["status"] == "pending" for e in data)

    async def test_filter_confirmed_empty(self, client, db_session, person_and_event):
        resp = await client.get("/api/v1/oracle/reports?status=confirmed")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
class TestVoteOnReport:
    async def test_vote_unauthenticated(self, client):
        resp = await client.post(
            f"/api/v1/oracle/reports/{uuid.uuid4()}/vote",
            json={"agent_id": "agent-2", "approve": True},
        )
        assert resp.status_code == 401

    async def test_vote_not_found(self, client, auth_headers):
        resp = await client.post(
            f"/api/v1/oracle/reports/{uuid.uuid4()}/vote",
            json={"agent_id": "agent-2", "approve": True},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_vote_accepted(self, client, auth_headers, db_session, person_and_event):
        """Auth agent (not the submitter) can vote successfully."""
        _person, event = person_and_event
        resp = await client.post(
            f"/api/v1/oracle/reports/{event.id}/vote",
            json={"agent_id": "ignored", "approve": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # 2 of 3 confirmations — still pending
        assert data["status"] == "pending"
        assert data["confirmations"] == 2

    async def test_duplicate_vote_rejected(
        self, client, auth_headers, db_session, person_and_event
    ):
        """Same agent voting twice is rejected."""
        _person, event = person_and_event
        # First vote succeeds
        resp1 = await client.post(
            f"/api/v1/oracle/reports/{event.id}/vote",
            json={"agent_id": "ignored", "approve": True},
            headers=auth_headers,
        )
        assert resp1.status_code == 200
        # Second vote from same agent is rejected
        resp2 = await client.post(
            f"/api/v1/oracle/reports/{event.id}/vote",
            json={"agent_id": "ignored", "approve": True},
            headers=auth_headers,
        )
        assert resp2.status_code == 409
