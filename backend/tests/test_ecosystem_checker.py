"""Tests for ecosystem_checker — Solana program verification against known registries."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.services.ecosystem_checker import (
    assess_ecosystem_presence,
    check_jupiter_strict_list,
    check_known_program,
    check_program_age_days,
)


@pytest.mark.asyncio
class TestCheckKnownProgram:
    async def test_known_program_returns_name(self):
        result = await check_known_program(
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        )
        assert result == "SPL Token"

    async def test_unknown_program_returns_none(self):
        result = await check_known_program("UnknownProgramAddress123")
        assert result is None

    async def test_system_program(self):
        result = await check_known_program(
            "11111111111111111111111111111111"
        )
        assert result == "System Program"


@pytest.mark.asyncio
class TestCheckJupiterStrictList:
    @patch("nile.services.ecosystem_checker.httpx.AsyncClient")
    async def test_found_on_list(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"address": "SomeTokenAddr123", "symbol": "TEST"},
        ]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await check_jupiter_strict_list("SomeTokenAddr123")
        assert result is True

    @patch("nile.services.ecosystem_checker.httpx.AsyncClient")
    async def test_not_on_list(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"address": "OtherAddr", "symbol": "OTHER"},
        ]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await check_jupiter_strict_list("NotOnList123")
        assert result is False

    @patch("nile.services.ecosystem_checker.httpx.AsyncClient")
    async def test_api_failure_returns_false(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await check_jupiter_strict_list("AnyAddr")
        assert result is False


@pytest.mark.asyncio
class TestCheckProgramAgeDays:
    @patch("nile.services.chain_service.chain_service")
    async def test_old_program(self, mock_chain):
        import time

        # 400 days old
        old_block_time = time.time() - (400 * 86400)
        mock_chain.get_transaction_history = AsyncMock(
            return_value=[{"block_time": old_block_time}]
        )

        age = await check_program_age_days("SomeProgram")
        assert age >= 399

    @patch("nile.services.chain_service.chain_service")
    async def test_no_history(self, mock_chain):
        mock_chain.get_transaction_history = AsyncMock(return_value=[])

        age = await check_program_age_days("NoHistoryProgram")
        assert age == 0

    @patch("nile.services.chain_service.chain_service")
    async def test_rpc_failure_returns_zero(self, mock_chain):
        mock_chain.get_transaction_history = AsyncMock(
            side_effect=Exception("RPC error")
        )

        age = await check_program_age_days("FailProgram")
        assert age == 0


@pytest.mark.asyncio
class TestAssessEcosystemPresence:
    @patch("nile.services.ecosystem_checker.check_program_age_days", new_callable=AsyncMock)
    @patch("nile.services.ecosystem_checker.check_jupiter_strict_list", new_callable=AsyncMock)
    @patch("nile.services.ecosystem_checker.check_known_program", new_callable=AsyncMock)
    async def test_known_program_scores_high(self, mock_known, mock_jup, mock_age):
        mock_known.return_value = "Jupiter v6"
        mock_jup.return_value = True
        mock_age.return_value = 500

        details = await assess_ecosystem_presence("JupiterAddr")
        score = details["ecosystem_score"]
        # 15 (known) + 10 (jupiter) + 5 (age>365) = 30, capped at 20
        assert score == 20.0

    @patch("nile.services.ecosystem_checker.check_program_age_days", new_callable=AsyncMock)
    @patch("nile.services.ecosystem_checker.check_jupiter_strict_list", new_callable=AsyncMock)
    @patch("nile.services.ecosystem_checker.check_known_program", new_callable=AsyncMock)
    async def test_unknown_new_program_scores_zero(self, mock_known, mock_jup, mock_age):
        mock_known.return_value = None
        mock_jup.return_value = False
        mock_age.return_value = 5

        details = await assess_ecosystem_presence("NewUnknownProgram")
        assert details["ecosystem_score"] == 0.0

    @patch("nile.services.ecosystem_checker.check_program_age_days", new_callable=AsyncMock)
    @patch("nile.services.ecosystem_checker.check_jupiter_strict_list", new_callable=AsyncMock)
    @patch("nile.services.ecosystem_checker.check_known_program", new_callable=AsyncMock)
    async def test_age_thresholds(self, mock_known, mock_jup, mock_age):
        mock_known.return_value = None
        mock_jup.return_value = False

        # > 365 days → +5
        mock_age.return_value = 400
        details = await assess_ecosystem_presence("OldProgram")
        assert details["ecosystem_score"] == 5.0

        # 90-365 → +3
        mock_age.return_value = 180
        details = await assess_ecosystem_presence("MediumProgram")
        assert details["ecosystem_score"] == 3.0

        # 30-90 → +1
        mock_age.return_value = 60
        details = await assess_ecosystem_presence("YoungProgram")
        assert details["ecosystem_score"] == 1.0

        # < 30 → +0
        mock_age.return_value = 10
        details = await assess_ecosystem_presence("BrandNewProgram")
        assert details["ecosystem_score"] == 0.0
