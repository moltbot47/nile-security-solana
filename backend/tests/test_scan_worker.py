"""Tests for scan_worker — processes queued scan jobs."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from nile.models.contract import Contract
from nile.models.scan_job import ScanJob
from nile.workers.scan_worker import process_scan_job


@pytest.fixture
async def contract_and_job(db_session):
    """Create a contract and a queued scan job."""
    contract = Contract(
        name="Test Program",
        address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        chain="solana",
    )
    db_session.add(contract)
    await db_session.flush()

    job = ScanJob(
        contract_id=contract.id,
        status="queued",
        mode="detect",
        agent="program_analyzer",
    )
    db_session.add(job)
    await db_session.flush()
    return contract, job


@pytest.mark.asyncio
class TestProcessScanJob:
    @patch(
        "nile.workers.scan_worker.submit_score_onchain",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("nile.workers.scan_worker.publish_event", new_callable=AsyncMock)
    @patch("nile.workers.scan_worker.program_analyzer")
    async def test_successful_scan(
        self, mock_analyzer, mock_event, mock_onchain, db_session, contract_and_job
    ):
        contract, job = contract_and_job

        # Mock the analysis result
        mock_score = SimpleNamespace(
            total_score=75.0,
            grade="B",
            name_score=80.0,
            image_score=70.0,
            likeness_score=75.0,
            essence_score=72.0,
            details={"name": {}, "image": {}, "likeness": {}, "essence": {}},
        )
        mock_analyzer.analyze = AsyncMock(return_value={
            "score": mock_score,
            "analysis_type": "program",
            "idl_analysis": {"has_idl": True},
            "ecosystem": {"known": True},
            "exploit_matches": [],
        })

        await process_scan_job(db_session, job)

        assert job.status == "succeeded"
        assert job.result["nile_score"] == 75.0
        assert job.result["grade"] == "B"
        assert job.finished_at is not None
        mock_event.assert_called_once()

    @patch("nile.workers.scan_worker.program_analyzer")
    async def test_contract_not_found_fails(self, mock_analyzer, db_session):
        """Job referencing a nonexistent contract should fail."""
        import uuid
        job = ScanJob(
            contract_id=uuid.uuid4(),
            status="queued",
            mode="detect",
            agent="program_analyzer",
        )
        db_session.add(job)
        await db_session.flush()

        await process_scan_job(db_session, job)
        assert job.status == "failed"
        assert "not found" in job.result_error

    @patch("nile.workers.scan_worker.program_analyzer")
    async def test_analysis_error_fails(self, mock_analyzer, db_session, contract_and_job):
        contract, job = contract_and_job
        mock_analyzer.analyze = AsyncMock(return_value={"error": "RPC timeout"})

        await process_scan_job(db_session, job)
        assert job.status == "failed"
        assert "RPC timeout" in job.result_error

    @patch("nile.workers.scan_worker.program_analyzer")
    async def test_contract_no_address_fails(self, mock_analyzer, db_session):
        """Contract with no address should fail."""
        contract = Contract(name="No Address", chain="solana")
        db_session.add(contract)
        await db_session.flush()

        job = ScanJob(
            contract_id=contract.id,
            status="queued",
            mode="detect",
            agent="program_analyzer",
        )
        db_session.add(job)
        await db_session.flush()

        await process_scan_job(db_session, job)
        assert job.status == "failed"
        assert "no address" in job.result_error.lower()
