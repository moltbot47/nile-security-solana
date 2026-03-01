"""Tests for idl_fetcher — fetch_idl function with mocked chain."""

from unittest.mock import AsyncMock, patch

import pytest

from nile.services.idl_fetcher import fetch_idl


@pytest.mark.asyncio
class TestFetchIdl:
    async def test_invalid_address(self):
        result = await fetch_idl("invalid")
        assert result is None

    @patch(
        "nile.services.idl_fetcher.validate_solana_address",
        return_value=True,
    )
    @patch("nile.services.idl_fetcher.chain_service")
    async def test_no_onchain_idl(self, mock_chain, mock_validate):
        """When on-chain IDL account doesn't exist, returns None."""
        mock_client = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.value = None
        mock_client.get_account_info = AsyncMock(return_value=mock_resp)
        mock_chain.async_client = mock_client

        result = await fetch_idl("11111111111111111111111111111111")
        assert result is None

    @patch(
        "nile.services.idl_fetcher.validate_solana_address",
        return_value=True,
    )
    @patch("nile.services.idl_fetcher.chain_service")
    async def test_solders_import_error(self, mock_chain, mock_validate):
        """When solders not installed, returns None gracefully."""
        with patch.dict("sys.modules", {"solders.pubkey": None}):
            # _fetch_onchain_idl will fail on import
            result = await fetch_idl("11111111111111111111111111111111")
            assert result is None
