"""Tests for agent registry endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

from nile.core.auth import hash_api_key
from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution

# --- Registration ---


@patch("nile.routers.v1.agents.publish_event", new_callable=AsyncMock)
async def test_register_agent(mock_pub, client):
    """POST /agents/register creates a new agent and returns credentials."""
    response = await client.post(
        "/api/v1/agents/register",
        json={
            "name": "test-detector",
            "description": "A test detection agent",
            "owner_id": "owner-test",
            "capabilities": ["detect"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-detector"
    assert data["status"] == "active"
    assert "api_key" in data
    assert "jwt_token" in data
    assert data["api_key"].startswith("nile_")
    mock_pub.assert_awaited_once()


@patch("nile.routers.v1.agents.publish_event", new_callable=AsyncMock)
async def test_register_duplicate_name_rejected(mock_pub, client, db_session):
    """Registration with an existing agent name returns 409."""
    agent = Agent(
        name="taken-name",
        owner_id="owner-1",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    response = await client.post(
        "/api/v1/agents/register",
        json={"name": "taken-name", "owner_id": "owner-2"},
    )
    assert response.status_code == 409


# --- Listing ---


async def test_list_agents_empty(client):
    """GET /agents returns empty list when no agents exist."""
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_agents_with_data(client, db_session):
    """GET /agents returns registered agents."""
    agent = Agent(
        name="list-agent",
        owner_id="owner-1",
        capabilities=["detect", "patch"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "list-agent"
    assert data[0]["capabilities"] == ["detect", "patch"]


async def test_list_agents_filter_by_status(client, db_session):
    """GET /agents?status=active filters by status."""
    for name, status in [("active-1", "active"), ("suspended-1", "suspended")]:
        db_session.add(
            Agent(
                name=name,
                owner_id="owner",
                capabilities=[],
                status=status,
                api_key_hash="unused",
            )
        )
    await db_session.flush()

    response = await client.get("/api/v1/agents?status=active")
    data = response.json()
    assert all(a["status"] == "active" for a in data)
    assert len(data) == 1


# --- Leaderboard ---


async def test_leaderboard_sorted_by_points(client, db_session):
    """GET /agents/leaderboard returns agents sorted by total_points desc."""
    for name, pts in [("low-agent", 10), ("high-agent", 500)]:
        db_session.add(
            Agent(
                name=name,
                owner_id="owner",
                capabilities=["detect"],
                status="active",
                api_key_hash="unused",
                total_points=pts,
            )
        )
    await db_session.flush()

    response = await client.get("/api/v1/agents/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "high-agent"
    assert data[0]["total_points"] == 500


# --- Get by ID ---


async def test_get_agent_by_id(client, db_session):
    """GET /agents/{id} returns the correct agent."""
    agent = Agent(
        name="get-me",
        owner_id="owner-1",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    response = await client.get(f"/api/v1/agents/{agent.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "get-me"


async def test_get_agent_not_found(client):
    """GET /agents/{id} returns 404 for non-existent agent."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/agents/{fake_id}")
    assert response.status_code == 404


# --- Heartbeat ---


async def test_heartbeat_updates_online_status(client, db_session):
    """POST /agents/{id}/heartbeat sets is_online to True."""
    raw_key = "nile_heartbeat_test_key"
    agent = Agent(
        name="heartbeat-agent",
        owner_id="owner-1",
        capabilities=["detect"],
        status="active",
        api_key_hash=hash_api_key(raw_key),
        is_online=False,
    )
    db_session.add(agent)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/agents/{agent.id}/heartbeat",
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_heartbeat_rejects_other_agent(client, db_session):
    """Heartbeat for a different agent returns 403."""
    raw_key = "nile_hb_reject_key"
    agent1 = Agent(
        name="hb-agent-1",
        owner_id="owner",
        capabilities=[],
        status="active",
        api_key_hash=hash_api_key(raw_key),
    )
    agent2 = Agent(
        name="hb-agent-2",
        owner_id="owner",
        capabilities=[],
        status="active",
        api_key_hash="other-hash",
    )
    db_session.add(agent1)
    db_session.add(agent2)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/agents/{agent2.id}/heartbeat",
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 403


# --- Contributions ---


async def test_agent_contributions_empty(client, db_session):
    """GET /agents/{id}/contributions returns empty list initially."""
    agent = Agent(
        name="contrib-agent",
        owner_id="owner",
        capabilities=[],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    response = await client.get(f"/api/v1/agents/{agent.id}/contributions")
    assert response.status_code == 200
    assert response.json() == []


async def test_agent_contributions_with_data(client, db_session):
    """GET /agents/{id}/contributions returns contribution records."""
    agent = Agent(
        name="contrib-data-agent",
        owner_id="owner",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    contrib = AgentContribution(
        agent_id=agent.id,
        contribution_type="detection",
        severity_found="high",
        verified=True,
        points_awarded=100,
        summary="Found critical vuln",
    )
    db_session.add(contrib)
    await db_session.flush()

    response = await client.get(f"/api/v1/agents/{agent.id}/contributions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["contribution_type"] == "detection"
    assert data[0]["points_awarded"] == 100
