"""Tests for collaboration — agent-to-agent workflow pipelines."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from nile.models.agent import Agent
from nile.models.agent_message import AgentMessage
from nile.models.contract import Contract
from nile.services.collaboration import (
    create_followup_task,
    detect_to_exploit_pipeline,
    detect_to_patch_pipeline,
    patch_verify_pipeline,
    send_agent_message,
)


@pytest.fixture
async def agent_and_contract(db_session):
    """Create an agent and a contract for pipeline tests."""
    agent = Agent(name="collab-agent", owner_id="owner-1", status="active")
    contract = Contract(
        address="ColLabAddr1111111111111111111111111111111111",
        name="Collab Contract",
        chain="solana",
    )
    db_session.add_all([agent, contract])
    await db_session.flush()
    return agent, contract


@pytest.mark.asyncio
class TestCreateFollowupTask:
    @patch("nile.services.collaboration.publish_event", new_callable=AsyncMock)
    async def test_creates_queued_job(self, mock_pub, db_session, agent_and_contract):
        agent, contract = agent_and_contract

        job = await create_followup_task(
            db_session,
            contract_id=contract.id,
            mode="patch",
            triggered_by_agent_id=agent.id,
        )

        assert job.status == "queued"
        assert job.mode == "patch"
        assert job.agent == "unassigned"

    @patch("nile.services.collaboration.publish_event", new_callable=AsyncMock)
    async def test_publishes_event(self, mock_pub, db_session, agent_and_contract):
        agent, contract = agent_and_contract

        await create_followup_task(
            db_session,
            contract_id=contract.id,
            mode="detect",
            triggered_by_agent_id=agent.id,
        )

        mock_pub.assert_called_once()
        assert mock_pub.call_args.kwargs["event_type"] == "task.created.detect"


@pytest.mark.asyncio
class TestDetectToPatch:
    @patch("nile.services.collaboration.publish_event", new_callable=AsyncMock)
    async def test_creates_patch_job_and_message(self, mock_pub, db_session, agent_and_contract):
        agent, contract = agent_and_contract
        vuln_details = {"type": "reentrancy", "severity": "critical"}

        job = await detect_to_patch_pipeline(
            db_session,
            contract_id=contract.id,
            detection_agent_id=agent.id,
            vulnerability_details=vuln_details,
        )

        assert job.mode == "patch"
        assert job.config["vulnerability"] == vuln_details

        # Check broadcast message was created
        result = await db_session.execute(
            select(AgentMessage).where(AgentMessage.channel == "patch")
        )
        msg = result.scalar_one()
        assert msg.payload["action"] == "patch_needed"
        assert msg.recipient_agent_id is None  # broadcast


@pytest.mark.asyncio
class TestDetectToExploit:
    @patch("nile.services.collaboration.publish_event", new_callable=AsyncMock)
    async def test_creates_exploit_job(self, mock_pub, db_session, agent_and_contract):
        agent, contract = agent_and_contract

        job = await detect_to_exploit_pipeline(
            db_session,
            contract_id=contract.id,
            detection_agent_id=agent.id,
            vulnerability_details={"type": "overflow"},
        )

        assert job.mode == "exploit"
        assert job.config["verify_only"] is True

        result = await db_session.execute(
            select(AgentMessage).where(AgentMessage.channel == "exploit")
        )
        msg = result.scalar_one()
        assert msg.payload["action"] == "exploit_verify"


@pytest.mark.asyncio
class TestPatchVerify:
    @patch("nile.services.collaboration.publish_event", new_callable=AsyncMock)
    async def test_creates_verify_scan(self, mock_pub, db_session, agent_and_contract):
        agent, contract = agent_and_contract
        patch_details = {"fixed_line": 42, "patch_type": "bounds_check"}

        job = await patch_verify_pipeline(
            db_session,
            contract_id=contract.id,
            patch_agent_id=agent.id,
            patch_details=patch_details,
        )

        assert job.mode == "detect"
        assert job.config["verify_patch"] is True
        assert job.config["patch_details"] == patch_details

        result = await db_session.execute(
            select(AgentMessage).where(AgentMessage.channel == "detection")
        )
        msg = result.scalar_one()
        assert msg.payload["action"] == "verify_patch"


@pytest.mark.asyncio
class TestSendAgentMessage:
    @patch("nile.services.collaboration.publish_event", new_callable=AsyncMock)
    async def test_broadcast_message(self, mock_pub, db_session, agent_and_contract):
        agent, _ = agent_and_contract

        msg = await send_agent_message(
            db_session,
            sender_id=agent.id,
            channel="detection",
            message_type="alert",
            payload={"severity": "critical"},
        )

        assert msg.channel == "detection"
        assert msg.message_type == "alert"
        assert msg.recipient_agent_id is None

    @patch("nile.services.collaboration.publish_event", new_callable=AsyncMock)
    async def test_directed_message(self, mock_pub, db_session):
        sender = Agent(name="sender-agent", owner_id="o1", status="active")
        recipient = Agent(name="recipient-agent", owner_id="o2", status="active")
        db_session.add_all([sender, recipient])
        await db_session.flush()

        msg = await send_agent_message(
            db_session,
            sender_id=sender.id,
            channel="patch",
            message_type="response",
            payload={"status": "done"},
            recipient_id=recipient.id,
        )

        assert msg.recipient_agent_id == recipient.id
        mock_pub.assert_called_once()
