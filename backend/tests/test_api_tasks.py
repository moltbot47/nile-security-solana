"""Tests for task assignment API endpoints (auth required)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.core.auth import create_agent_token
from nile.models.agent import Agent
from nile.models.contract import Contract
from nile.models.scan_job import ScanJob


@pytest.fixture
async def agent_and_token(db_session):
    """Create an agent and return (agent, jwt_token)."""
    agent = Agent(
        name=f"task-agent-{uuid.uuid4().hex[:8]}",
        owner_id="test-owner",
        capabilities=["detect"],
        status="active",
        api_key_hash="fakehash",
    )
    db_session.add(agent)
    await db_session.flush()
    token = create_agent_token(str(agent.id))
    return agent, token


@pytest.fixture
async def queued_task(db_session, agent_and_token):
    """Create a contract + queued scan job."""
    agent, _token = agent_and_token
    contract = Contract(name="Task Test Contract", chain="solana")
    db_session.add(contract)
    await db_session.flush()

    job = ScanJob(
        contract_id=contract.id,
        mode="detect",
        agent="unassigned",
        status="queued",
        hint_level="none",
    )
    db_session.add(job)
    await db_session.flush()
    return contract, job


@pytest.mark.asyncio
class TestListAvailableTasks:
    async def test_unauthenticated(self, client):
        resp = await client.get("/api/v1/tasks/available")
        assert resp.status_code == 401

    async def test_empty_list(self, client, db_session, agent_and_token):
        _agent, token = agent_and_token
        resp = await client.get(
            "/api/v1/tasks/available",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_lists_queued_tasks(self, client, db_session, agent_and_token, queued_task):
        _agent, token = agent_and_token
        resp = await client.get(
            "/api/v1/tasks/available",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["status"] == "queued"

    async def test_filter_by_mode(self, client, db_session, agent_and_token, queued_task):
        _agent, token = agent_and_token
        resp = await client.get(
            "/api/v1/tasks/available?mode=exploit",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        # No exploit-mode tasks exist
        assert resp.json() == []


@pytest.mark.asyncio
class TestClaimTask:
    async def test_not_found(self, client, db_session, agent_and_token):
        _agent, token = agent_and_token
        resp = await client.post(
            f"/api/v1/tasks/{uuid.uuid4()}/claim",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @patch("nile.routers.v1.tasks.publish_event", new_callable=AsyncMock)
    async def test_claim_success(self, _mock_pub, client, db_session, agent_and_token, queued_task):
        _agent, token = agent_and_token
        _contract, job = queued_task
        resp = await client.post(
            f"/api/v1/tasks/{job.id}/claim",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"

    @patch("nile.routers.v1.tasks.publish_event", new_callable=AsyncMock)
    async def test_claim_already_running(
        self, _mock_pub, client, db_session, agent_and_token, queued_task
    ):
        _agent, token = agent_and_token
        _contract, job = queued_task
        # Claim once
        await client.post(
            f"/api/v1/tasks/{job.id}/claim",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Try again
        resp = await client.post(
            f"/api/v1/tasks/{job.id}/claim",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409


@pytest.mark.asyncio
class TestSubmitTask:
    async def test_not_found(self, client, db_session, agent_and_token):
        _agent, token = agent_and_token
        resp = await client.post(
            f"/api/v1/tasks/{uuid.uuid4()}/submit",
            json={"result": {"score": 85}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @patch("nile.routers.v1.tasks.award_contribution")
    @patch("nile.routers.v1.tasks.publish_event", new_callable=AsyncMock)
    async def test_submit_success(
        self,
        _mock_pub,
        mock_award,
        client,
        db_session,
        agent_and_token,
        queued_task,
    ):
        # Mock award_contribution to avoid UUID string issues
        mock_contribution = MagicMock()
        mock_contribution.points_awarded = 50
        mock_award.return_value = mock_contribution

        _agent, token = agent_and_token
        _contract, job = queued_task
        # Claim first
        await client.post(
            f"/api/v1/tasks/{job.id}/claim",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Submit
        resp = await client.post(
            f"/api/v1/tasks/{job.id}/submit",
            json={
                "result": {"score": 85},
                "contribution_type": "detection",
                "severity_found": "high",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "succeeded"
        assert data["points_awarded"] == 50

    async def test_submit_not_running(self, client, db_session, agent_and_token, queued_task):
        _agent, token = agent_and_token
        _contract, job = queued_task
        # Try to submit without claiming
        resp = await client.post(
            f"/api/v1/tasks/{job.id}/submit",
            json={"result": {"score": 85}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
