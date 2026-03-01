"""Tests for events API endpoints."""

import uuid

import pytest

from nile.models.ecosystem_event import EcosystemEvent


@pytest.mark.asyncio
class TestEventHistory:
    async def test_empty_history(self, client):
        resp = await client.get("/api/v1/events/history")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_with_events(self, client, db_session):
        db_session.add(
            EcosystemEvent(
                event_type="scan.completed",
                actor_id=uuid.uuid4(),
                target_id=uuid.uuid4(),
            )
        )
        await db_session.flush()

        resp = await client.get("/api/v1/events/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["event_type"] == "scan.completed"

    async def test_filter_by_type(self, client, db_session):
        db_session.add(EcosystemEvent(event_type="scan.completed", actor_id=uuid.uuid4()))
        db_session.add(EcosystemEvent(event_type="task.claimed", actor_id=uuid.uuid4()))
        await db_session.flush()

        resp = await client.get("/api/v1/events/history?event_type=scan.completed")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["event_type"] == "scan.completed" for e in data)
