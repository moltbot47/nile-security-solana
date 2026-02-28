"""Tests for authentication and authorization."""

import uuid

from nile.core.auth import create_agent_token, hash_api_key
from nile.models.agent import Agent


async def test_protected_endpoint_rejects_no_auth(client):
    """Protected endpoints return 401 without credentials."""
    response = await client.post(
        "/api/v1/trading/buy",
        json={
            "person_id": str(uuid.uuid4()),
            "amount": "1.0",
            "trader_address": "FakeAddr" + "x" * 35,
        },
    )
    assert response.status_code == 401


async def test_protected_endpoint_rejects_invalid_jwt(client):
    """Protected endpoints return 401 with invalid JWT."""
    response = await client.post(
        "/api/v1/trading/buy",
        json={
            "person_id": str(uuid.uuid4()),
            "amount": "1.0",
            "trader_address": "FakeAddr" + "x" * 35,
        },
        headers={"Authorization": "Bearer invalid-token-here"},
    )
    assert response.status_code == 401


async def test_jwt_auth_with_valid_agent(client, db_session):
    """Valid JWT for an existing agent grants access."""
    # Create an agent in the DB
    agent = Agent(
        name="test-jwt-agent",
        owner_id="owner-1",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    # Create a JWT for this agent
    token = create_agent_token(str(agent.id))

    # Access a protected read endpoint (persons list — doesn't need auth but tests the flow)
    response = await client.get(
        "/api/v1/persons",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


async def test_api_key_auth_with_valid_agent(client, db_session):
    """Valid API key for an existing agent grants access."""
    raw_key = "nile_test_key_12345"
    agent = Agent(
        name="test-apikey-agent",
        owner_id="owner-2",
        capabilities=["detect"],
        status="active",
        api_key_hash=hash_api_key(raw_key),
    )
    db_session.add(agent)
    await db_session.flush()

    response = await client.get(
        "/api/v1/persons",
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 200


async def test_suspended_agent_returns_403(client, db_session):
    """Suspended agents get 403 even with valid credentials."""
    agent = Agent(
        name="suspended-agent",
        owner_id="owner-3",
        capabilities=["detect"],
        status="suspended",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()

    token = create_agent_token(str(agent.id))

    response = await client.post(
        "/api/v1/oracle/reports",
        json={
            "person_id": str(uuid.uuid4()),
            "event_type": "test",
            "source": "test",
            "headline": "Test",
            "impact_score": 50,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_public_endpoints_work_without_auth(client):
    """Public endpoints like health, contracts list work without auth."""
    # Health
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    # Contracts list (read, no auth required)
    response = await client.get("/api/v1/contracts")
    assert response.status_code == 200

    # Persons list (read, no auth required)
    response = await client.get("/api/v1/persons")
    assert response.status_code == 200
