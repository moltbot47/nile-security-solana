"""Extended tests for chain_service — mock RPC methods."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.services.chain_service import SolanaChainService


@pytest.mark.asyncio
class TestGetProgramInfo:
    async def test_invalid_address_returns_none(self):
        svc = SolanaChainService()
        result = await svc.get_program_info("invalid")
        assert result is None

    @patch("nile.services.chain_service.validate_solana_address", return_value=True)
    async def test_account_not_found(self, _mock):
        svc = SolanaChainService()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.value = None
        mock_client.get_account_info = AsyncMock(return_value=mock_resp)
        svc._async_client = mock_client

        result = await svc.get_program_info("11111111111111111111111111111111")
        assert result is None

    @patch("nile.services.chain_service.validate_solana_address", return_value=True)
    async def test_exception_returns_none(self, _mock):
        svc = SolanaChainService()
        mock_client = AsyncMock()
        mock_client.get_account_info = AsyncMock(side_effect=Exception("RPC error"))
        svc._async_client = mock_client

        result = await svc.get_program_info("11111111111111111111111111111111")
        assert result is None


@pytest.mark.asyncio
class TestGetTokenInfo:
    async def test_invalid_address_returns_none(self):
        svc = SolanaChainService()
        result = await svc.get_token_info("invalid")
        assert result is None


@pytest.mark.asyncio
class TestGetProgramAuthority:
    async def test_invalid_address_returns_none(self):
        svc = SolanaChainService()
        result = await svc.get_program_authority("bad")
        assert result is None


@pytest.mark.asyncio
class TestGetTransactionHistory:
    async def test_invalid_address_returns_empty(self):
        svc = SolanaChainService()
        result = await svc.get_transaction_history("invalid")
        assert result == []


@pytest.mark.asyncio
class TestAssessProgramSecurity:
    async def test_nonexistent_program(self):
        svc = SolanaChainService()
        svc.get_program_info = AsyncMock(return_value=None)
        result = await svc.assess_program_security("11111111111111111111111111111111")
        assert result["exists"] is False
        assert result["executable"] is False

    async def test_existing_program(self):
        svc = SolanaChainService()
        svc.get_program_info = AsyncMock(return_value={
            "executable": True,
            "data_len": 1000,
        })
        svc.get_program_authority = AsyncMock(return_value={
            "upgradeable": True,
            "authority": "auth123",
        })
        result = await svc.assess_program_security("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        assert result["exists"] is True
        assert result["executable"] is True
        assert result["upgrade_authority_active"] is True


@pytest.mark.asyncio
class TestAssessTokenSecurity:
    async def test_nonexistent_token(self):
        svc = SolanaChainService()
        svc.get_token_info = AsyncMock(return_value=None)
        result = await svc.assess_token_security("11111111111111111111111111111111")
        assert result["exists"] is False

    async def test_existing_token(self):
        svc = SolanaChainService()
        svc.get_token_info = AsyncMock(return_value={
            "mint_authority_active": True,
            "mint_authority": "auth1",
            "freeze_authority_active": False,
            "freeze_authority": None,
            "supply": 1000000,
            "decimals": 9,
        })
        result = await svc.assess_token_security("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        assert result["exists"] is True
        assert result["mint_authority_active"] is True
