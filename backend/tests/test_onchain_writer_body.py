"""Tests for onchain_writer — transaction building with mocked solders."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.services.onchain_writer import (
    _is_enabled,
    _load_idl,
    register_program_onchain,
    submit_score_onchain,
)


class TestIsEnabled:
    @patch("nile.services.onchain_writer.settings")
    def test_disabled_no_program_id(self, mock_settings):
        mock_settings.program_id = ""
        mock_settings.deployer_private_key = "key123"
        assert _is_enabled() is False

    @patch("nile.services.onchain_writer.settings")
    def test_disabled_no_key(self, mock_settings):
        mock_settings.program_id = "prog123"
        mock_settings.deployer_private_key = ""
        assert _is_enabled() is False

    @patch("nile.services.onchain_writer.settings")
    def test_enabled(self, mock_settings):
        mock_settings.program_id = "prog123"
        mock_settings.deployer_private_key = "key123"
        assert _is_enabled() is True


class TestLoadIdl:
    def test_missing_file(self):
        result = _load_idl()
        # IDL file won't exist in test env
        assert result is None


@pytest.mark.asyncio
class TestSubmitScoreOnchain:
    @patch("nile.services.onchain_writer._is_enabled", return_value=False)
    async def test_disabled_returns_none(self, _mock):
        result = await submit_score_onchain("addr", 80, 70, 60, 50)
        assert result is None

    @patch("nile.services.onchain_writer._is_enabled", return_value=True)
    async def test_import_error_returns_none(self, _mock):
        """When solders is not installed, returns None gracefully."""
        # Force ImportError by removing mock solders if present
        with patch.dict(sys.modules, {
            "solana": None,
            "solana.rpc": None,
            "solana.rpc.async_api": None,
        }):
            result = await submit_score_onchain("addr", 80, 70, 60, 50)
            assert result is None

    @patch("nile.services.onchain_writer._is_enabled", return_value=True)
    @patch("nile.services.onchain_writer.settings")
    async def test_full_flow_mocked(self, mock_settings, _mock_enabled):
        """Test the full transaction build with mocked solders."""
        mock_settings.deployer_private_key = "A" * 88  # base58 key
        mock_settings.program_id = "11111111111111111111111111111111"
        mock_settings.solana_rpc_url = "http://localhost:8899"

        # Mock all solders imports
        mock_keypair = MagicMock()
        mock_keypair.pubkey.return_value = MagicMock()
        mock_pubkey = MagicMock()
        mock_pubkey.from_string.return_value = MagicMock()
        mock_pubkey.find_program_address.return_value = (MagicMock(), 255)

        mock_client = AsyncMock()
        mock_blockhash_resp = MagicMock()
        mock_blockhash_resp.value.blockhash = MagicMock()
        mock_client.get_latest_blockhash = AsyncMock(
            return_value=mock_blockhash_resp
        )
        mock_result = MagicMock()
        mock_result.value = "txsig123"
        mock_client.send_transaction = AsyncMock(return_value=mock_result)
        mock_client.close = AsyncMock()

        mock_base58 = MagicMock()
        mock_base58.b58decode.return_value = b"\x00" * 64

        with patch.dict(sys.modules, {
            "base58": mock_base58,
            "solana": MagicMock(),
            "solana.rpc": MagicMock(),
            "solana.rpc.async_api": MagicMock(
                AsyncClient=MagicMock(return_value=mock_client)
            ),
            "solders": MagicMock(),
            "solders.keypair": MagicMock(
                Keypair=MagicMock(from_bytes=MagicMock(return_value=mock_keypair))
            ),
            "solders.pubkey": MagicMock(Pubkey=mock_pubkey),
            "solders.instruction": MagicMock(),
            "solders.message": MagicMock(),
            "solders.transaction": MagicMock(),
        }):
            result = await submit_score_onchain(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                80, 70, 60, 50, "ipfs://details",
            )
            assert result is not None

    @patch("nile.services.onchain_writer._is_enabled", return_value=True)
    async def test_general_exception_returns_none(self, _mock):
        """Any other exception returns None."""
        # When solders is missing entirely, ImportError is caught
        result = await submit_score_onchain("addr", 80, 70, 60, 50)
        assert result is None


@pytest.mark.asyncio
class TestRegisterProgramOnchain:
    @patch("nile.services.onchain_writer._is_enabled", return_value=False)
    async def test_disabled_returns_none(self, _mock):
        result = await register_program_onchain("addr", "Test Program")
        assert result is None

    @patch("nile.services.onchain_writer._is_enabled", return_value=True)
    async def test_exception_returns_none(self, _mock):
        """General exception returns None."""
        result = await register_program_onchain("addr", "Test Program")
        assert result is None
