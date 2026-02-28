"""Tests for workers/main.py entrypoint."""

from unittest.mock import AsyncMock, patch

from nile.workers.main import main


class TestWorkerMain:
    @patch("nile.workers.main.run_worker", new_callable=AsyncMock)
    @patch("nile.workers.main.asyncio")
    def test_main_calls_run_worker(self, mock_asyncio, mock_run_worker):
        main()
        mock_asyncio.run.assert_called_once()
