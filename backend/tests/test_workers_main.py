"""Tests for nile.workers.main and scan_worker exception handling."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from nile.workers.main import main


class TestWorkerMain:
    @patch("nile.workers.main.run_worker", new_callable=AsyncMock)
    @patch("nile.workers.main.asyncio")
    def test_main_calls_run_worker(self, mock_asyncio, mock_run_worker):
        main()
        mock_asyncio.run.assert_called_once()


class TestScanWorkerExceptionHandling:
    @pytest.mark.asyncio
    async def test_poll_cycle_exception_caught(self):
        """run_worker catches exceptions from poll_and_process and continues."""
        from nile.workers.scan_worker import run_worker

        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                raise asyncio.CancelledError()

        with (
            patch(
                "nile.workers.scan_worker.poll_and_process",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB connection lost"),
            ),
            patch("nile.workers.scan_worker.asyncio.sleep", side_effect=mock_sleep),
            pytest.raises(asyncio.CancelledError),
        ):
            await run_worker()
