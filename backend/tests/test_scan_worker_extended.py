"""Extended scan worker tests — poll_and_process, onchain write success."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.models.contract import Contract
from nile.models.scan_job import ScanJob
from nile.workers.scan_worker import process_scan_job


@pytest.fixture
async def ready_job(db_session):
    """Contract with address + queued job."""
    contract = Contract(
        name="OnChain Program",
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
class TestOnchainWriteSuccess:
    @patch(
        "nile.workers.scan_worker.submit_score_onchain",
        new_callable=AsyncMock,
        return_value="5wHB...txsig",
    )
    @patch("nile.workers.scan_worker.publish_event", new_callable=AsyncMock)
    @patch("nile.workers.scan_worker.program_analyzer")
    async def test_onchain_tx_saved(
        self, mock_analyzer, mock_event, mock_onchain, db_session, ready_job
    ):
        contract, job = ready_job

        mock_score = SimpleNamespace(
            total_score=88.0,
            grade="A",
            name_score=90.0,
            image_score=85.0,
            likeness_score=88.0,
            essence_score=86.0,
            details={},
        )
        mock_analyzer.analyze = AsyncMock(
            return_value={
                "score": mock_score,
                "analysis_type": "program",
                "idl_analysis": {},
                "ecosystem": {},
                "exploit_matches": [
                    {
                        "pattern_id": "SOL-001",
                        "name": "Reentrancy",
                        "severity": "high",
                        "confidence": 0.7,
                    }
                ],
            }
        )

        await process_scan_job(db_session, job)

        assert job.status == "succeeded"
        assert job.result["onchain_tx"] == "5wHB...txsig"
        assert job.result["exploit_match_count"] == 1


@pytest.mark.asyncio
class TestPollAndProcess:
    @patch("nile.workers.scan_worker.async_session")
    @patch("nile.workers.scan_worker.process_scan_job", new_callable=AsyncMock)
    async def test_polls_queued_jobs(self, mock_process, mock_session_ctx):
        from nile.workers.scan_worker import poll_and_process

        mock_db = AsyncMock()
        mock_job = MagicMock()
        # scalars() is sync, returns a sync object with .all() method
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_job]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        await poll_and_process()

        mock_process.assert_called_once_with(mock_db, mock_job)
        mock_db.commit.assert_called_once()

    @patch("nile.workers.scan_worker.async_session")
    @patch("nile.workers.scan_worker.process_scan_job", new_callable=AsyncMock)
    async def test_no_queued_jobs(self, mock_process, mock_session_ctx):
        from nile.workers.scan_worker import poll_and_process

        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        await poll_and_process()

        mock_process.assert_not_called()


@pytest.mark.asyncio
class TestRunWorker:
    async def test_worker_loop(self):
        """run_worker polls then sleeps in a loop."""
        import asyncio

        from nile.workers.scan_worker import run_worker

        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                raise asyncio.CancelledError()

        with (
            patch("nile.workers.scan_worker.poll_and_process", new_callable=AsyncMock),
            patch("nile.workers.scan_worker.asyncio.sleep", side_effect=mock_sleep),
            pytest.raises(asyncio.CancelledError),
        ):
            await run_worker()
