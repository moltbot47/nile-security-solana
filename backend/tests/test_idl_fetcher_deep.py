"""Tests for _fetch_onchain_idl — deep body coverage with mocked solders."""

import json
import struct
import zlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_solders_mocks():
    """Create solders module mocks."""
    mock_pk_cls = MagicMock()
    mock_pk_cls.from_string = MagicMock(
        return_value=MagicMock(__bytes__=lambda _: b"\x00" * 32)
    )
    mock_pk_cls.find_program_address = MagicMock(
        return_value=(MagicMock(), 255)
    )
    mock_mod = MagicMock()
    mock_mod.Pubkey = mock_pk_cls
    return {
        "solders": MagicMock(),
        "solders.pubkey": mock_mod,
    }, mock_pk_cls


@pytest.mark.asyncio
class TestFetchOnchainIdl:
    async def test_account_not_found(self):
        mods, _ = _make_solders_mocks()
        with patch.dict("sys.modules", mods):
            import importlib

            import nile.services.idl_fetcher as fetcher_mod

            importlib.reload(fetcher_mod)

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = None
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)

            with patch.object(
                fetcher_mod.chain_service, "_async_client", mock_client
            ):
                result = await fetcher_mod._fetch_onchain_idl(
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                )
                assert result is None

    async def test_short_data_returns_none(self):
        mods, _ = _make_solders_mocks()
        with patch.dict("sys.modules", mods):
            import importlib

            import nile.services.idl_fetcher as fetcher_mod

            importlib.reload(fetcher_mod)

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = b"\x00" * 20  # < 44 bytes
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)

            with patch.object(
                fetcher_mod.chain_service, "_async_client", mock_client
            ):
                result = await fetcher_mod._fetch_onchain_idl(
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                )
                assert result is None

    async def test_compressed_idl(self):
        mods, _ = _make_solders_mocks()
        with patch.dict("sys.modules", mods):
            import importlib

            import nile.services.idl_fetcher as fetcher_mod

            importlib.reload(fetcher_mod)

            # Build mock IDL data: 44 bytes header + 4 bytes len + compressed JSON
            idl_json = json.dumps({"instructions": [], "version": "0.1.0"}).encode()
            compressed = zlib.compress(idl_json)

            header = b"\x00" * 44  # 8 disc + 4 auth option + 32 auth pubkey
            data_len = struct.pack("<I", len(compressed))
            full_data = header + data_len + compressed

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = full_data
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)

            with patch.object(
                fetcher_mod.chain_service, "_async_client", mock_client
            ):
                result = await fetcher_mod._fetch_onchain_idl(
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                )
                assert result is not None
                assert result["version"] == "0.1.0"

    async def test_uncompressed_idl(self):
        mods, _ = _make_solders_mocks()
        with patch.dict("sys.modules", mods):
            import importlib

            import nile.services.idl_fetcher as fetcher_mod

            importlib.reload(fetcher_mod)

            # Uncompressed JSON (old Anchor format)
            idl_json = json.dumps({"instructions": [{"name": "init"}]}).encode()

            header = b"\x00" * 44
            data_len = struct.pack("<I", len(idl_json))
            full_data = header + data_len + idl_json

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = full_data
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)

            with patch.object(
                fetcher_mod.chain_service, "_async_client", mock_client
            ):
                result = await fetcher_mod._fetch_onchain_idl(
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                )
                assert result is not None
                assert len(result["instructions"]) == 1

    async def test_exception_returns_none(self):
        mods, mk = _make_solders_mocks()
        mk.from_string = MagicMock(side_effect=RuntimeError("boom"))
        with patch.dict("sys.modules", mods):
            import importlib

            import nile.services.idl_fetcher as fetcher_mod

            importlib.reload(fetcher_mod)

            result = await fetcher_mod._fetch_onchain_idl(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result is None

    async def test_data_len_mismatch(self):
        mods, _ = _make_solders_mocks()
        with patch.dict("sys.modules", mods):
            import importlib

            import nile.services.idl_fetcher as fetcher_mod

            importlib.reload(fetcher_mod)

            # Header + data_len claiming 999 bytes but actual data is shorter
            header = b"\x00" * 44
            data_len = struct.pack("<I", 999)
            full_data = header + data_len + b"\x00" * 10  # only 10 bytes of data

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            mock_resp.value.data = full_data
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)

            with patch.object(
                fetcher_mod.chain_service, "_async_client", mock_client
            ):
                result = await fetcher_mod._fetch_onchain_idl(
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                )
                assert result is None

    async def test_fetch_idl_returns_onchain(self):
        """fetch_idl calls _fetch_onchain_idl and returns result."""
        mods, _ = _make_solders_mocks()
        with patch.dict("sys.modules", mods):
            import importlib

            import nile.services.idl_fetcher as fetcher_mod

            importlib.reload(fetcher_mod)

            idl_data = {"instructions": [], "version": "0.2.0"}
            fetcher_mod._fetch_onchain_idl = AsyncMock(return_value=idl_data)

            result = await fetcher_mod.fetch_idl(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            )
            assert result == idl_data
