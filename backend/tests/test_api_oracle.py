"""Tests for oracle API endpoints."""

import uuid

import pytest

from nile.models.oracle_event import OracleEvent
from nile.models.person import Person


@pytest.fixture
async def person_and_event(db_session):
    """Create a person and a pending oracle event."""
    person = Person(
        display_name="Oracle Test Person",
        slug="oracle-test",
        category="athlete",
    )
    db_session.add(person)
    await db_session.flush()

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
        required_confirmations=2,
        agent_votes={"agent-1": {"approve": True, "impact": 80}},
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
    async def test_vote_not_found(self, client):
        resp = await client.post(
            f"/api/v1/oracle/reports/{uuid.uuid4()}/vote",
            json={"agent_id": "agent-2", "approve": True},
        )
        assert resp.status_code == 404

    async def test_vote_reaches_consensus(self, client, db_session, person_and_event):
        _person, event = person_and_event
        resp = await client.post(
            f"/api/v1/oracle/reports/{event.id}/vote",
            json={"agent_id": "agent-2", "approve": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "confirmed"

    async def test_duplicate_vote_rejected(self, client, db_session, person_and_event):
        _person, event = person_and_event
        resp = await client.post(
            f"/api/v1/oracle/reports/{event.id}/vote",
            json={"agent_id": "agent-1", "approve": True},
        )
        assert resp.status_code == 409
