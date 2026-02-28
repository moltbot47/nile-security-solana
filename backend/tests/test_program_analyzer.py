"""Tests for program_analyzer — Solana program and token security analysis."""

from unittest.mock import AsyncMock, patch

import pytest

from nile.services.program_analyzer import SolanaProgramAnalyzer, _load_exploit_patterns


@pytest.fixture
def analyzer():
    return SolanaProgramAnalyzer()


class TestLoadExploitPatterns:
    @patch("nile.services.program_analyzer._EXPLOIT_PATTERNS", [])
    @patch("nile.services.program_analyzer._EXPLOIT_PATTERNS_PATH")
    def test_missing_file_returns_empty(self, mock_path):
        mock_path.exists.return_value = False
        result = _load_exploit_patterns()
        assert result == []

    @patch("nile.services.program_analyzer._EXPLOIT_PATTERNS", [])
    @patch("nile.services.program_analyzer._EXPLOIT_PATTERNS_PATH")
    def test_valid_file_loads_patterns(self, mock_path):
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = '{"patterns": [{"id": "p1", "name": "test"}]}'
        result = _load_exploit_patterns()
        assert len(result) == 1
        assert result[0]["id"] == "p1"


@pytest.mark.asyncio
class TestAnalyze:
    @patch("nile.services.program_analyzer.validate_solana_address", return_value=False)
    async def test_invalid_address(self, _mock, analyzer):
        result = await analyzer.analyze("invalid")
        assert "error" in result
        assert "Invalid" in result["error"]

    @patch("nile.services.program_analyzer.validate_solana_address", return_value=True)
    @patch("nile.services.program_analyzer.chain_service")
    async def test_unrecognized_address(self, mock_chain, _mock, analyzer):
        mock_chain.get_program_info = AsyncMock(return_value=None)
        mock_chain.get_token_info = AsyncMock(return_value=None)
        result = await analyzer.analyze("11111111111111111111111111111111")
        assert "error" in result
        assert "not a recognized" in result["error"]

    @patch("nile.services.program_analyzer.validate_solana_address", return_value=True)
    @patch("nile.services.program_analyzer.assess_ecosystem_presence", new_callable=AsyncMock)
    @patch("nile.services.program_analyzer.chain_service")
    async def test_token_analysis(self, mock_chain, mock_eco, _mock, analyzer):
        mock_chain.get_program_info = AsyncMock(return_value=None)
        mock_chain.get_token_info = AsyncMock(return_value={
            "exists": True,
            "mint_authority_active": True,
            "freeze_authority_active": False,
            "supply": 1_000_000_000,
            "decimals": 9,
        })
        mock_eco.return_value = {
            "jupiter_strict_list": False,
            "known_program": None,
            "age_days": 30,
            "ecosystem_score": 5.0,
        }
        with patch("nile.services.program_analyzer._load_exploit_patterns", return_value=[]):
            result = await analyzer.analyze("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        assert result["analysis_type"] == "token"
        assert "score" in result

    @patch("nile.services.program_analyzer.validate_solana_address", return_value=True)
    @patch("nile.services.program_analyzer.assess_ecosystem_presence", new_callable=AsyncMock)
    @patch("nile.services.program_analyzer.check_known_program", new_callable=AsyncMock)
    @patch("nile.services.program_analyzer.fetch_idl", new_callable=AsyncMock)
    @patch("nile.services.program_analyzer.analyze_idl_security")
    @patch("nile.services.program_analyzer.chain_service")
    async def test_program_analysis(
        self, mock_chain, mock_idl_sec, mock_fetch_idl, mock_known, mock_eco, _mock, analyzer
    ):
        mock_chain.get_program_info = AsyncMock(return_value={
            "executable": True,
            "address": "prog1",
            "owner": "BPFLoaderUpgradeab1e",
            "lamports": 1000000,
            "data_len": 500,
        })
        mock_chain.get_token_info = AsyncMock(return_value=None)
        mock_chain.get_program_authority = AsyncMock(return_value={
            "upgradeable": True,
            "authority": "auth1",
        })
        mock_fetch_idl.return_value = {"version": "0.1.0", "instructions": []}
        mock_idl_sec.return_value = {
            "has_idl": True,
            "instruction_count": 5,
            "missing_signer_checks": 0,
            "unsafe_cpi_calls": 0,
            "unvalidated_accounts": 0,
        }
        mock_known.return_value = "Token Program"
        mock_eco.return_value = {
            "jupiter_strict_list": True,
            "known_program": "Token Program",
            "age_days": 365,
            "ecosystem_score": 18.0,
        }

        with patch("nile.services.program_analyzer._load_exploit_patterns", return_value=[]):
            result = await analyzer.analyze("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        assert result["analysis_type"] == "program"
        assert "score" in result


class TestAssessors:
    def test_assess_image(self):
        analyzer = SolanaProgramAnalyzer()
        result = analyzer._assess_image({
            "missing_signer_checks": 2,
            "unsafe_cpi_calls": 1,
            "unvalidated_accounts": 3,
        })
        assert result.missing_signer_checks == 2
        assert result.unsafe_cpi_calls == 1
        assert result.unvalidated_accounts == 3

    def test_assess_likeness(self):
        analyzer = SolanaProgramAnalyzer()
        matches = [{"pattern_id": "p1", "confidence": 0.8}]
        result = analyzer._assess_likeness(matches, {"instruction_count": 10})
        assert result.exploit_pattern_matches == matches

    def test_assess_essence_with_authority(self):
        analyzer = SolanaProgramAnalyzer()
        result = analyzer._assess_essence(
            {"instruction_count": 10, "unsafe_cpi_calls": 2},
            {"upgradeable": True},
        )
        assert result.upgrade_authority_active is True
        assert result.has_timelock is False

    def test_assess_essence_without_authority(self):
        analyzer = SolanaProgramAnalyzer()
        result = analyzer._assess_essence({"instruction_count": 5, "unsafe_cpi_calls": 0}, None)
        assert result.upgrade_authority_active is False


class TestPatternMatching:
    def test_access_control_match(self):
        analyzer = SolanaProgramAnalyzer()
        patterns = [
            {
                "id": "p1",
                "name": "Missing Signer",
                "category": "access_control",
                "severity": "high",
                "indicators": ["Missing signer check"],
            }
        ]
        with patch("nile.services.program_analyzer._load_exploit_patterns", return_value=patterns):
            matches = analyzer._match_exploit_patterns(
                {"missing_signer_checks": 2, "has_idl": True}, None
            )
        assert len(matches) == 1
        assert matches[0]["category"] == "access_control"
        assert matches[0]["confidence"] > 0.3

    def test_rug_pull_match(self):
        analyzer = SolanaProgramAnalyzer()
        patterns = [
            {
                "id": "p2",
                "name": "Rug Pull Risk",
                "category": "rug_pull",
                "severity": "critical",
                "indicators": [],
            }
        ]
        with patch("nile.services.program_analyzer._load_exploit_patterns", return_value=patterns):
            matches = analyzer._match_exploit_patterns(
                {"has_idl": False, "missing_signer_checks": 0}, {"upgradeable": True}
            )
        assert len(matches) == 1
        assert matches[0]["category"] == "rug_pull"

    def test_no_match_below_threshold(self):
        analyzer = SolanaProgramAnalyzer()
        patterns = [
            {
                "id": "p3",
                "name": "Oracle Manipulation",
                "category": "oracle_manipulation",
                "severity": "high",
                "indicators": [],
            }
        ]
        with patch("nile.services.program_analyzer._load_exploit_patterns", return_value=patterns):
            matches = analyzer._match_exploit_patterns(
                {"missing_signer_checks": 0, "has_idl": True}, None
            )
        assert len(matches) == 0


class TestTokenPatterns:
    def test_token_rug_confidence_mint_active(self):
        analyzer = SolanaProgramAnalyzer()
        conf = analyzer._compute_token_rug_confidence({"mint_authority_active": True})
        assert conf >= 0.3

    def test_token_rug_confidence_both_active(self):
        analyzer = SolanaProgramAnalyzer()
        conf = analyzer._compute_token_rug_confidence({
            "mint_authority_active": True,
            "freeze_authority_active": True,
        })
        assert conf >= 0.5

    def test_rug_similarity_clean_token(self):
        analyzer = SolanaProgramAnalyzer()
        score = analyzer._compute_rug_similarity({
            "mint_authority_active": False,
            "freeze_authority_active": False,
        })
        assert score == 0.0

    def test_rug_similarity_suspicious_token(self):
        analyzer = SolanaProgramAnalyzer()
        score = analyzer._compute_rug_similarity({
            "mint_authority_active": True,
            "freeze_authority_active": True,
            "supply": 100,
            "decimals": 9,
        })
        assert score > 0.5
