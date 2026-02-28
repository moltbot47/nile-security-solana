"""Tests for chain_service method bodies with mock RPC responses."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.services.chain_service import SolanaChainService


def _install_mock_solders():
    """Install mock solders module so local imports succeed."""
    mock_pubkey_cls = MagicMock()
    # from_string returns a mock pubkey
    mock_pubkey_cls.from_string = MagicMock(return_value=MagicMock())
    mock_pubkey_cls.find_program_address = MagicMock(
        return_value=(MagicMock(), 255)
    )
    mock_pubkey_cls.from_bytes = MagicMock(return_value=MagicMock())

    mock_pubkey_mod = MagicMock()
    mock_pubkey_mod.Pubkey = mock_pubkey_cls
    # Also alias Pk = Pubkey (used in get_program_authority)
    return mock_pubkey_mod, mock_pubkey_cls


@pytest.mark.asyncio
class TestGetProgramInfoBody:
    @patch(
        "nile.services.chain_service.validate_solana_address",
        return_value=True,
    )
    async def test_returns_account_info(self, _mock):
        mock_mod, mock_cls = _install_mock_solders()
        with patch.dict(sys.modules, {"solders.pubkey": mock_mod}):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_account = MagicMock()
            mock_account.executable = True
            mock_account.owner = "BPFLoader"
            mock_account.lamports = 5000000
            mock_account.data = b"\x00" * 200
            mock_resp = MagicMock()
            mock_resp.value = mock_account
            mock_client.get_account_info = AsyncMock(
                return_value=mock_resp
            )
            svc._async_client = mock_client

            result = await svc.get_program_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is not None
            assert result["executable"] is True
            assert result["lamports"] == 5000000
            assert result["data_len"] == 200


@pytest.mark.asyncio
class TestGetProgramAuthorityBody:
    @patch(
        "nile.services.chain_service.validate_solana_address",
        return_value=True,
    )
    async def test_short_data_returns_not_upgradeable(self, _mock):
        mock_mod, mock_cls = _install_mock_solders()
        with patch.dict(sys.modules, {"solders.pubkey": mock_mod}):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_account = MagicMock()
            mock_account.data = b"\x00\x01\x02"  # < 4 bytes
            mock_resp = MagicMock()
            mock_resp.value = mock_account
            mock_client.get_account_info = AsyncMock(
                return_value=mock_resp
            )
            svc._async_client = mock_client

            result = await svc.get_program_authority(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is not None
            assert result["upgradeable"] is False

    @patch(
        "nile.services.chain_service.validate_solana_address",
        return_value=True,
    )
    async def test_account_not_found(self, _mock):
        mock_mod, _ = _install_mock_solders()
        with patch.dict(sys.modules, {"solders.pubkey": mock_mod}):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = None
            mock_client.get_account_info = AsyncMock(
                return_value=mock_resp
            )
            svc._async_client = mock_client

            result = await svc.get_program_authority(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None


@pytest.mark.asyncio
class TestGetTokenInfoBody:
    @patch(
        "nile.services.chain_service.validate_solana_address",
        return_value=True,
    )
    async def test_short_data_returns_none(self, _mock):
        mock_mod, _ = _install_mock_solders()
        with patch.dict(sys.modules, {"solders.pubkey": mock_mod}):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_account = MagicMock()
            mock_account.data = b"\x00" * 50  # < 82 bytes
            mock_resp = MagicMock()
            mock_resp.value = mock_account
            mock_client.get_account_info = AsyncMock(
                return_value=mock_resp
            )
            svc._async_client = mock_client

            result = await svc.get_token_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None

    @patch(
        "nile.services.chain_service.validate_solana_address",
        return_value=True,
    )
    async def test_exception_returns_none(self, _mock):
        svc = SolanaChainService()
        mock_client = AsyncMock()
        mock_client.get_account_info = AsyncMock(
            side_effect=Exception("RPC error")
        )
        svc._async_client = mock_client

        result = await svc.get_token_info(
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        )
        assert result is None


@pytest.mark.asyncio
class TestGetSolPriceUsd:
    async def test_exception_returns_none(self):
        svc = SolanaChainService()
        mock_client = AsyncMock()
        mock_client.get_account_info = AsyncMock(
            side_effect=Exception("Pyth error")
        )
        svc._async_client = mock_client

        result = await svc.get_sol_price_usd()
        assert result is None

    async def test_no_account_returns_none(self):
        mock_mod, _ = _install_mock_solders()
        with patch.dict(sys.modules, {"solders.pubkey": mock_mod}):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = None
            mock_client.get_account_info = AsyncMock(
                return_value=mock_resp
            )
            svc._async_client = mock_client

            result = await svc.get_sol_price_usd()
            assert result is None

    async def test_short_data_returns_none(self):
        mock_mod, _ = _install_mock_solders()
        with patch.dict(sys.modules, {"solders.pubkey": mock_mod}):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_account = MagicMock()
            mock_account.data = b"\x00" * 100  # < 208
            mock_resp = MagicMock()
            mock_resp.value = mock_account
            mock_client.get_account_info = AsyncMock(
                return_value=mock_resp
            )
            svc._async_client = mock_client

            result = await svc.get_sol_price_usd()
            assert result is None


@pytest.mark.asyncio
class TestGetTransactionHistoryBody:
    @patch(
        "nile.services.chain_service.validate_solana_address",
        return_value=True,
    )
    async def test_returns_signatures(self, _mock):
        mock_mod, _ = _install_mock_solders()
        with patch.dict(sys.modules, {"solders.pubkey": mock_mod}):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_sig = MagicMock()
            mock_sig.signature = "5abc123"
            mock_sig.slot = 12345
            mock_sig.err = None
            mock_sig.block_time = 1700000000
            mock_resp = MagicMock()
            mock_resp.value = [mock_sig]
            mock_client.get_signatures_for_address = AsyncMock(
                return_value=mock_resp
            )
            svc._async_client = mock_client

            result = await svc.get_transaction_history(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert len(result) == 1
            assert result[0]["slot"] == 12345

    @patch(
        "nile.services.chain_service.validate_solana_address",
        return_value=True,
    )
    async def test_exception_returns_empty(self, _mock):
        svc = SolanaChainService()
        mock_client = AsyncMock()
        mock_client.get_signatures_for_address = AsyncMock(
            side_effect=Exception("RPC error")
        )
        svc._async_client = mock_client

        result = await svc.get_transaction_history(
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        )
        assert result == []


class TestLazyClientProperties:
    def test_sync_client_not_initialized(self):
        svc = SolanaChainService()
        assert svc._client is None

    def test_async_client_not_initialized(self):
        svc = SolanaChainService()
        assert svc._async_client is None

    def test_load_idl_missing_file(self):
        from nile.services.chain_service import _load_idl

        result = _load_idl("nonexistent_program")
        assert result is None
