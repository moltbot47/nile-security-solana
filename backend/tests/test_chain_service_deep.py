"""Tests for chain_service — deep body coverage with mocked solders."""

import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.services.chain_service import SolanaChainService


def _install_mock_solders():
    """Create mock solders modules for import patching."""
    mock_pubkey_cls = MagicMock()
    mock_pubkey_cls.from_string = MagicMock(
        side_effect=lambda s: MagicMock(__bytes__=lambda _: b"\x00" * 32)
    )
    mock_pubkey_cls.from_bytes = MagicMock(
        side_effect=lambda b: MagicMock(__str__=lambda _: "MockPubkey")
    )
    mock_pubkey_cls.find_program_address = MagicMock(
        return_value=(MagicMock(__str__=lambda _: "PDAAddress"), 255)
    )

    mock_pubkey_mod = MagicMock()
    mock_pubkey_mod.Pubkey = mock_pubkey_cls
    mock_pubkey_mod.Pk = mock_pubkey_cls

    mock_rpc_client = MagicMock()
    mock_rpc_api = MagicMock()
    mock_rpc_api.Client = mock_rpc_client

    mock_async_client_cls = MagicMock()
    mock_rpc_async_api = MagicMock()
    mock_rpc_async_api.AsyncClient = mock_async_client_cls

    return {
        "solders": MagicMock(),
        "solders.pubkey": mock_pubkey_mod,
        "solders.rpc": MagicMock(),
        "solders.rpc.api": mock_rpc_api,
        "solders.rpc.async_api": mock_rpc_async_api,
    }, mock_pubkey_cls, mock_async_client_cls


@pytest.mark.asyncio
class TestClientProperties:
    def test_client_lazy_init(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            svc._client = None
            _ = svc.client
            assert svc._client is not None

    def test_client_import_error(self):
        svc = SolanaChainService()
        svc._client = None
        # Without solders installed, should raise ImportError
        with pytest.raises(ImportError):
            _ = svc.client

    def test_async_client_lazy_init(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            svc._async_client = None
            _ = svc.async_client
            assert svc._async_client is not None

    def test_async_client_import_error(self):
        svc = SolanaChainService()
        svc._async_client = None
        with pytest.raises(ImportError):
            _ = svc.async_client


@pytest.mark.asyncio
class TestGetProgramAuthority:
    async def test_invalid_address(self):
        svc = SolanaChainService()
        result = await svc.get_program_authority("invalid")
        assert result is None

    async def test_account_not_found(self):
        mods, mock_pk, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = None
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_program_authority(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None

    async def test_short_data_not_upgradeable(self):
        mods, mock_pk, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()

            # First call: program account (short data)
            mock_resp1 = MagicMock()
            mock_resp1.value = MagicMock()
            mock_resp1.value.data = b"\x00" * 3  # < 4 bytes

            mock_client.get_account_info = AsyncMock(return_value=mock_resp1)
            svc._async_client = mock_client

            result = await svc.get_program_authority(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result == {"upgradeable": False, "authority": None}

    async def test_programdata_with_authority(self):
        mods, mock_pk, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()

            # First call: program account (enough data)
            prog_data = b"\x00" * 100
            mock_resp1 = MagicMock()
            mock_resp1.value = MagicMock()
            mock_resp1.value.data = prog_data

            # Second call: programdata account with authority
            pd_data = bytearray(100)
            pd_data[12] = 1  # has_authority = true
            pd_data[13:45] = b"\xAA" * 32  # authority pubkey
            mock_resp2 = MagicMock()
            mock_resp2.value = MagicMock()
            mock_resp2.value.data = bytes(pd_data)

            mock_client.get_account_info = AsyncMock(
                side_effect=[mock_resp1, mock_resp2]
            )
            svc._async_client = mock_client

            result = await svc.get_program_authority(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is not None
            assert result["upgradeable"] is True

    async def test_exception_returns_none(self):
        mods, mock_pk, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_client.get_account_info = AsyncMock(
                side_effect=RuntimeError("RPC error")
            )
            svc._async_client = mock_client

            result = await svc.get_program_authority(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None


@pytest.mark.asyncio
class TestGetTokenInfo:
    async def test_invalid_address(self):
        svc = SolanaChainService()
        result = await svc.get_token_info("bad")
        assert result is None

    async def test_account_not_found(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = None
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_token_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None

    async def test_short_data(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = b"\x00" * 50  # < 82
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_token_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None

    async def test_valid_mint_data(self):
        mods, mock_pk, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()

            # Build valid SPL token mint data (82 bytes)
            data = bytearray(82)
            # mint_authority option = 1 (Some)
            struct.pack_into("<I", data, 0, 1)
            # mint_authority pubkey (32 bytes)
            data[4:36] = b"\xBB" * 32
            # supply = 1000000 (u64 LE)
            struct.pack_into("<Q", data, 36, 1000000)
            # decimals = 9
            data[44] = 9
            # freeze_authority option = 0 (None)
            struct.pack_into("<I", data, 46, 0)

            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = bytes(data)
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_token_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is not None
            assert result["supply"] == 1000000
            assert result["decimals"] == 9
            assert result["mint_authority_active"] is True
            assert result["freeze_authority_active"] is False

    async def test_exception_returns_none(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_client.get_account_info = AsyncMock(
                side_effect=RuntimeError("RPC fail")
            )
            svc._async_client = mock_client

            result = await svc.get_token_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None


@pytest.mark.asyncio
class TestGetSolPriceUsd:
    async def test_feed_not_found(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = None
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_sol_price_usd()
            assert result is None

    async def test_short_data(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = b"\x00" * 100  # < 208
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_sol_price_usd()
            assert result is None

    async def test_valid_price(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()

            # Build Pyth price data (>= 216 bytes)
            data = bytearray(300)
            # Exponent at offset 20 (i32) = -8
            struct.pack_into("<i", data, 20, -8)
            # Price at offset 208 (i64) = 25000000000 ($250)
            struct.pack_into("<q", data, 208, 25000000000)

            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = bytes(data)
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_sol_price_usd()
            assert result is not None
            assert abs(result - 250.0) < 0.01

    async def test_exception_returns_none(self):
        mods, _, _ = _install_mock_solders()
        with patch.dict("sys.modules", mods):
            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_client.get_account_info = AsyncMock(
                side_effect=RuntimeError("RPC error")
            )
            svc._async_client = mock_client

            result = await svc.get_sol_price_usd()
            assert result is None
