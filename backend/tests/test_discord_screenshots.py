"""Tests for discord screenshots module — mocked Playwright."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.discord.screenshots import (
    DASHBOARD_PAGES,
    SCREENSHOT_DIR,
    capture_all_pages,
    capture_page,
)


class TestDashboardPages:
    def test_has_pages(self):
        assert len(DASHBOARD_PAGES) == 5

    def test_each_page_has_required_keys(self):
        for page in DASHBOARD_PAGES:
            assert "path" in page
            assert "name" in page
            assert "channel" in page

    def test_screenshot_dir_defined(self):
        assert Path("/tmp/nile-screenshots") == SCREENSHOT_DIR  # noqa: S108


@pytest.mark.asyncio
class TestCapturePage:
    async def test_playwright_not_installed(self):
        with patch.dict(
            "sys.modules", {"playwright": None, "playwright.async_api": None}
        ):
            result = await capture_page("http://localhost", "/", "test")
            assert result is None

    async def test_capture_success(self):
        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_pw = AsyncMock()
        mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_async_pw = MagicMock(return_value=mock_ctx)

        mock_pw_mod = MagicMock()
        mock_pw_mod.async_playwright = mock_async_pw

        with patch.dict("sys.modules", {
            "playwright": MagicMock(),
            "playwright.async_api": mock_pw_mod,
        }):
            import importlib

            import nile.discord.screenshots as ss

            importlib.reload(ss)
            result = await ss.capture_page(
                "http://localhost:3000", "/", "dashboard"
            )
            assert result is not None
            assert str(result).endswith("dashboard.png")

    async def test_capture_general_exception(self):
        """General exception in capture returns None."""
        mock_pw_mod = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(
            side_effect=Exception("Browser crash")
        )
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_pw_mod.async_playwright = MagicMock(return_value=mock_ctx)

        with patch.dict("sys.modules", {
            "playwright": MagicMock(),
            "playwright.async_api": mock_pw_mod,
        }):
            import importlib

            import nile.discord.screenshots as ss

            importlib.reload(ss)
            result = await ss.capture_page(
                "http://localhost", "/", "test"
            )
            assert result is None


@pytest.mark.asyncio
class TestCaptureAllPages:
    @patch("nile.discord.screenshots.capture_page")
    async def test_captures_all(self, mock_capture):
        mock_capture.return_value = Path("/tmp/nile-screenshots/test.png")
        results = await capture_all_pages("http://localhost:3000")
        assert len(results) == 5

    @patch("nile.discord.screenshots.capture_page")
    async def test_skips_failed(self, mock_capture):
        mock_capture.return_value = None
        results = await capture_all_pages("http://localhost:3000")
        assert len(results) == 0
