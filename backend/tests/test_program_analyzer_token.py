"""Tests for program_analyzer — token analysis path."""

from unittest.mock import AsyncMock, patch

import pytest

from nile.services.program_analyzer import SolanaProgramAnalyzer


@pytest.mark.asyncio
class TestAnalyzeToken:
    @patch("nile.services.program_analyzer.assess_ecosystem_presence", new_callable=AsyncMock)
    @patch("nile.services.program_analyzer.chain_service")
    async def test_token_analysis(self, mock_chain, mock_ecosystem):
        mock_chain.get_program_info = AsyncMock(return_value=None)
        mock_chain.get_token_info = AsyncMock(
            return_value={
                "exists": True,
                "mint": "Test",
                "supply": 1000000,
                "decimals": 9,
                "mint_authority_active": True,
                "freeze_authority_active": False,
            }
        )
        mock_ecosystem.return_value = {
            "jupiter_strict_list": False,
            "age_days": 10,
            "known_program": None,
            "ecosystem_score": 20.0,
        }

        analyzer = SolanaProgramAnalyzer()
        result = await analyzer.analyze("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

        assert result["analysis_type"] == "token"
        assert "score" in result
        assert result["score"].total_score >= 0

    @patch("nile.services.program_analyzer.chain_service")
    async def test_invalid_address(self, mock_chain):
        analyzer = SolanaProgramAnalyzer()
        result = await analyzer.analyze("bad")
        assert "error" in result

    @patch("nile.services.program_analyzer.chain_service")
    async def test_unrecognized_address(self, mock_chain):
        mock_chain.get_program_info = AsyncMock(return_value=None)
        mock_chain.get_token_info = AsyncMock(return_value=None)

        analyzer = SolanaProgramAnalyzer()
        result = await analyzer.analyze("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        assert "error" in result
        assert "not a recognized" in result["error"]

    @patch("nile.services.program_analyzer.assess_ecosystem_presence", new_callable=AsyncMock)
    @patch("nile.services.program_analyzer.chain_service")
    async def test_token_with_verified_ecosystem(self, mock_chain, mock_ecosystem):
        mock_chain.get_program_info = AsyncMock(return_value=None)
        mock_chain.get_token_info = AsyncMock(
            return_value={
                "exists": True,
                "mint": "Verified",
                "supply": 5000000,
                "decimals": 6,
                "mint_authority_active": False,
                "freeze_authority_active": False,
            }
        )
        mock_ecosystem.return_value = {
            "jupiter_strict_list": True,
            "age_days": 365,
            "known_program": {"name": "USDC"},
            "ecosystem_score": 90.0,
        }

        analyzer = SolanaProgramAnalyzer()
        result = await analyzer.analyze("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

        assert result["analysis_type"] == "token"
        # Verified token with no mint authority should score higher
        assert result["score"].total_score > 0

    @patch("nile.services.program_analyzer.assess_ecosystem_presence", new_callable=AsyncMock)
    @patch("nile.services.program_analyzer.chain_service")
    async def test_program_analysis_path(self, mock_chain, mock_ecosystem):
        """When address is executable, takes the program path."""
        mock_chain.get_program_info = AsyncMock(
            return_value={
                "address": "Test",
                "executable": True,
                "owner": "BPF",
                "lamports": 100,
                "data_len": 50,
            }
        )
        mock_chain.get_token_info = AsyncMock(return_value=None)
        mock_chain.get_program_authority = AsyncMock(return_value=None)

        mock_ecosystem.return_value = {
            "jupiter_strict_list": False,
            "age_days": 5,
            "known_program": None,
            "ecosystem_score": 10.0,
        }

        with patch(
            "nile.services.program_analyzer.fetch_idl",
            new_callable=AsyncMock,
            return_value=None,
        ):
            analyzer = SolanaProgramAnalyzer()
            result = await analyzer.analyze("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

        assert result["analysis_type"] == "program"
        assert "score" in result
