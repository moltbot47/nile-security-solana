"""Tests for onchain_writer — Solana on-chain score submission (feature-flagged)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nile.services.onchain_writer import (
    _is_enabled,
    _load_idl,
    register_program_onchain,
    submit_score_onchain,
)


class TestIsEnabled:
    @patch("nile.services.onchain_writer.settings")
    def test_disabled_when_no_program_id(self, mock_settings):
        mock_settings.program_id = ""
        mock_settings.deployer_private_key = "some-key"
        assert _is_enabled() is False

    @patch("nile.services.onchain_writer.settings")
    def test_disabled_when_no_deployer_key(self, mock_settings):
        mock_settings.program_id = "some-program"
        mock_settings.deployer_private_key = ""
        assert _is_enabled() is False

    @patch("nile.services.onchain_writer.settings")
    def test_enabled_when_both_configured(self, mock_settings):
        mock_settings.program_id = "some-program"
        mock_settings.deployer_private_key = "some-key"
        assert _is_enabled() is True


class TestLoadIdl:
    @patch("nile.services.onchain_writer._IDL_PATH", Path("/nonexistent/path.json"))
    def test_missing_file_returns_none(self):
        result = _load_idl()
        assert result is None

    def test_valid_idl_file(self, tmp_path):
        idl_file = tmp_path / "test.json"
        idl_file.write_text(json.dumps({"version": "0.1.0", "instructions": []}))
        with patch("nile.services.onchain_writer._IDL_PATH", idl_file):
            result = _load_idl()
        assert result is not None
        assert result["version"] == "0.1.0"


@pytest.mark.asyncio
class TestSubmitScoreOnchain:
    @patch("nile.services.onchain_writer._is_enabled", return_value=False)
    async def test_disabled_returns_none(self, _mock):
        result = await submit_score_onchain(
            program_address="test",
            name_score=80,
            image_score=70,
            likeness_score=60,
            essence_score=50,
        )
        assert result is None

    @patch("nile.services.onchain_writer._is_enabled", return_value=True)
    async def test_import_error_returns_none(self, _mock):
        """If solders is not installed, should return None gracefully."""
        with patch.dict("sys.modules", {"base58": None, "solana": None, "solders": None}):
            result = await submit_score_onchain(
                program_address="test",
                name_score=80,
                image_score=70,
                likeness_score=60,
                essence_score=50,
            )
            assert result is None


@pytest.mark.asyncio
class TestRegisterProgramOnchain:
    @patch("nile.services.onchain_writer._is_enabled", return_value=False)
    async def test_disabled_returns_none(self, _mock):
        result = await register_program_onchain(
            program_address="test", name="Test Program"
        )
        assert result is None
