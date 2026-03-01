"""Extended tests for agents API — register, update, heartbeat, contributions."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from nile.core.auth import create_agent_token
from nile.models.agent import Agent


@pytest.fixture
async def registered_agent(db_session):
    """Create an active agent and return (agent, token)."""
    agent = Agent(
        name=f"ext-agent-{uuid.uuid4().hex[:8]}",
        owner_id="test-owner",
        capabilities=["detect", "patch"],
        status="active",
        api_key_hash="fakehash",
    )
    db_session.add(agent)
    await db_session.flush()
    token = create_agent_token(str(agent.id))
    return agent, token


@pytest.mark.asyncio
class TestRegisterAgent:
    @patch("nile.routers.v1.agents.publish_event", new_callable=AsyncMock)
    async def test_register_success(self, _mock_pub, client, db_session):
        resp = await client.post(
            "/api/v1/agents/register",
            json={
                "name": f"new-agent-{uuid.uuid4().hex[:8]}",
                "owner_id": "owner1",
                "capabilities": ["detect"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "api_key" in data
        assert "jwt_token" in data
        assert data["status"] == "active"

    @patch("nile.routers.v1.agents.publish_event", new_callable=AsyncMock)
    async def test_register_duplicate_name(self, _mock_pub, client, db_session, registered_agent):
        agent, _ = registered_agent
        resp = await client.post(
            "/api/v1/agents/register",
            json={
                "name": agent.name,
                "owner_id": "owner2",
            },
        )
        assert resp.status_code == 409


@pytest.mark.asyncio
class TestListAgents:
    async def test_list_empty(self, client, db_session):
        resp = await client.get("/api/v1/agents")
        assert resp.status_code == 200

    async def test_list_with_agent(self, client, db_session, registered_agent):
        resp = await client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    async def test_filter_by_capability(self, client, db_session, registered_agent):
        resp = await client.get("/api/v1/agents?capability=detect")
        assert resp.status_code == 200
        data = resp.json()
        assert all("detect" in a["capabilities"] for a in data)


@pytest.mark.asyncio
class TestGetAgent:
    async def test_not_found(self, client, db_session):
        resp = await client.get(f"/api/v1/agents/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_found(self, client, db_session, registered_agent):
        agent, _ = registered_agent
        resp = await client.get(f"/api/v1/agents/{agent.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == agent.name


@pytest.mark.asyncio
class TestLeaderboard:
    async def test_leaderboard(self, client, db_session, registered_agent):
        resp = await client.get("/api/v1/agents/leaderboard")
        assert resp.status_code == 200

    async def test_leaderboard_filter_capability(self, client, db_session, registered_agent):
        resp = await client.get("/api/v1/agents/leaderboard?capability=exploit")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestUpdateAgent:
    async def test_update_own_agent(self, client, db_session, registered_agent):
        agent, token = registered_agent
        resp = await client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"description": "Updated description"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    async def test_update_other_agent_forbidden(self, client, db_session, registered_agent):
        _, token = registered_agent
        resp = await client.patch(
            f"/api/v1/agents/{uuid.uuid4()}",
            json={"description": "Hacker"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestHeartbeat:
    async def test_heartbeat_own(self, client, db_session, registered_agent):
        agent, token = registered_agent
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/heartbeat",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_heartbeat_other_forbidden(self, client, db_session, registered_agent):
        _, token = registered_agent
        resp = await client.post(
            f"/api/v1/agents/{uuid.uuid4()}/heartbeat",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestContributions:
    async def test_empty_contributions(self, client, db_session, registered_agent):
        agent, _ = registered_agent
        resp = await client.get(f"/api/v1/agents/{agent.id}/contributions")
        assert resp.status_code == 200
        assert resp.json() == []
