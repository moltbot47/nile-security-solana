"""Tests for chain_service.get_program_info and get_transaction_history."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_solders():
    """Create mock solders modules."""
    mock_pk = MagicMock()
    mock_pk.from_string = MagicMock(side_effect=lambda s: MagicMock())
    return {
        "solders": MagicMock(),
        "solders.pubkey": MagicMock(Pubkey=mock_pk),
        "solders.rpc": MagicMock(),
        "solders.rpc.api": MagicMock(),
        "solders.rpc.async_api": MagicMock(AsyncClient=MagicMock()),
    }, mock_pk


@pytest.mark.asyncio
class TestGetProgramInfo:
    async def test_invalid_address(self):
        from nile.services.chain_service import SolanaChainService

        svc = SolanaChainService()
        result = await svc.get_program_info("bad")
        assert result is None

    async def test_successful_info(self):
        mods, _ = _mock_solders()
        with patch.dict("sys.modules", mods):
            from nile.services.chain_service import SolanaChainService

            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_account = MagicMock()
            mock_account.executable = True
            mock_account.owner = MagicMock(__str__=lambda _: "BPFLoader")
            mock_account.lamports = 1000000
            mock_account.data = b"\x00" * 100
            mock_resp.value = mock_account
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_program_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is not None
            assert result["executable"] is True

    async def test_exception_returns_none(self):
        mods, _ = _mock_solders()
        with patch.dict("sys.modules", mods):
            from nile.services.chain_service import SolanaChainService

            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_client.get_account_info = AsyncMock(
                side_effect=RuntimeError("RPC error")
            )
            svc._async_client = mock_client

            result = await svc.get_program_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None


@pytest.mark.asyncio
class TestGetProgramAuthorityPdaResp:
    async def test_pd_resp_none(self):
        """When programdata account is not found, returns not upgradeable."""
        mods, mock_pk = _mock_solders()
        mock_pk.from_string = MagicMock(
            side_effect=lambda s: MagicMock(__bytes__=lambda _: b"\x00" * 32)
        )
        mock_pk.find_program_address = MagicMock(
            return_value=(MagicMock(), 255)
        )
        # Also add Pk alias
        mods["solders.pubkey"].Pk = mock_pk

        with patch.dict("sys.modules", mods):
            from nile.services.chain_service import SolanaChainService

            svc = SolanaChainService()
            mock_client = AsyncMock()

            # First call: program account with enough data
            mock_resp1 = MagicMock()
            mock_resp1.value = MagicMock()
            mock_resp1.value.data = b"\x00" * 100

            # Second call: programdata account not found
            mock_resp2 = MagicMock()
            mock_resp2.value = None

            mock_client.get_account_info = AsyncMock(
                side_effect=[mock_resp1, mock_resp2]
            )
            svc._async_client = mock_client

            result = await svc.get_program_authority(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result == {"upgradeable": False, "authority": None}

    async def test_pd_short_data(self):
        """When programdata is too short, returns not upgradeable."""
        mods, mock_pk = _mock_solders()
        mock_pk.from_string = MagicMock(
            side_effect=lambda s: MagicMock(__bytes__=lambda _: b"\x00" * 32)
        )
        mock_pk.find_program_address = MagicMock(
            return_value=(MagicMock(), 255)
        )
        mods["solders.pubkey"].Pk = mock_pk

        with patch.dict("sys.modules", mods):
            from nile.services.chain_service import SolanaChainService

            svc = SolanaChainService()
            mock_client = AsyncMock()

            mock_resp1 = MagicMock()
            mock_resp1.value = MagicMock()
            mock_resp1.value.data = b"\x00" * 100

            mock_resp2 = MagicMock()
            mock_resp2.value = MagicMock()
            mock_resp2.value.data = b"\x00" * 10  # < 45

            mock_client.get_account_info = AsyncMock(
                side_effect=[mock_resp1, mock_resp2]
            )
            svc._async_client = mock_client

            result = await svc.get_program_authority(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result == {"upgradeable": False, "authority": None}


@pytest.mark.asyncio
class TestGetTokenInfoFreeze:
    async def test_token_with_freeze_authority(self):
        """Token with freeze authority active."""
        import struct

        mods, mock_pk = _mock_solders()
        mock_pk.from_string = MagicMock(
            side_effect=lambda s: MagicMock(__bytes__=lambda _: b"\x00" * 32)
        )
        mock_pk.from_bytes = MagicMock(
            side_effect=lambda b: MagicMock(__str__=lambda _: "MockAddr")
        )

        with patch.dict("sys.modules", mods):
            from nile.services.chain_service import SolanaChainService

            svc = SolanaChainService()
            mock_client = AsyncMock()

            data = bytearray(82)
            struct.pack_into("<I", data, 0, 0)  # no mint authority
            struct.pack_into("<Q", data, 36, 5000000)
            data[44] = 6
            struct.pack_into("<I", data, 46, 1)  # freeze authority active
            data[50:82] = b"\xCC" * 32

            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = bytes(data)
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_token_info(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is not None
            assert result["freeze_authority_active"] is True
            assert result["mint_authority_active"] is False
