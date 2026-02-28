"""Tests for Solana Program Analyzer — the core NILE product."""

import pytest

from nile.services.idl_fetcher import analyze_idl_security
from nile.services.program_analyzer import SolanaProgramAnalyzer

# --- IDL Security Analysis tests ---


def test_analyze_idl_no_idl():
    result = analyze_idl_security(None)
    assert result["has_idl"] is False
    assert result["instruction_count"] == 0


def test_analyze_idl_empty():
    result = analyze_idl_security({})
    assert result["instruction_count"] == 0
    assert result["account_validation_rate"] == 0.0


def test_analyze_idl_basic_program():
    idl = {
        "instructions": [
            {
                "name": "initialize",
                "accounts": [
                    {"name": "authority", "isMut": True, "isSigner": True},
                    {
                        "name": "state",
                        "isMut": True,
                        "isSigner": False,
                        "type": {"kind": "account"},
                    },
                    {
                        "name": "systemProgram",
                        "isMut": False,
                        "isSigner": False,
                        "type": {"kind": "program"},
                    },
                ],
                "args": [],
            },
        ],
    }
    result = analyze_idl_security(idl)
    assert result["has_idl"] is True
    assert result["instruction_count"] == 1
    assert result["total_accounts"] == 3
    assert result["missing_signer_checks"] == 0
    assert result["account_validation_rate"] == 100.0


def test_analyze_idl_unvalidated_accounts():
    idl = {
        "instructions": [
            {
                "name": "transfer",
                "accounts": [
                    {"name": "from", "isMut": True, "isSigner": False},
                    {"name": "to", "isMut": True, "isSigner": False},
                ],
                "args": [],
            },
        ],
    }
    result = analyze_idl_security(idl)
    assert result["unvalidated_accounts"] == 2
    assert result["missing_signer_checks"] == 2  # Mutable but no signer


# --- Analyzer unit tests ---


@pytest.mark.asyncio
async def test_analyzer_invalid_address():
    analyzer = SolanaProgramAnalyzer()
    result = await analyzer.analyze("not-a-valid-address")
    assert "error" in result


@pytest.mark.asyncio
async def test_analyzer_rejects_eth_address():
    analyzer = SolanaProgramAnalyzer()
    result = await analyzer.analyze("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD08")
    assert "error" in result
    assert "Invalid" in result["error"]


# --- Exploit pattern matching tests ---


def test_rug_pull_confidence_mint_authority():
    analyzer = SolanaProgramAnalyzer()
    token_info = {
        "mint_authority_active": True,
        "freeze_authority_active": True,
    }
    confidence = analyzer._compute_token_rug_confidence(token_info)
    assert confidence == 0.5  # 0.3 + 0.2


def test_rug_pull_confidence_safe_token():
    analyzer = SolanaProgramAnalyzer()
    token_info = {
        "mint_authority_active": False,
        "freeze_authority_active": False,
    }
    confidence = analyzer._compute_token_rug_confidence(token_info)
    assert confidence == 0.0


def test_rug_similarity_high_risk():
    analyzer = SolanaProgramAnalyzer()
    token_info = {
        "mint_authority_active": True,
        "freeze_authority_active": True,
        "supply": 100,
        "decimals": 6,
    }
    similarity = analyzer._compute_rug_similarity(token_info)
    assert similarity >= 0.6  # mint + freeze + low supply


def test_rug_similarity_safe():
    analyzer = SolanaProgramAnalyzer()
    token_info = {
        "mint_authority_active": False,
        "freeze_authority_active": False,
        "supply": 1_000_000_000_000,
        "decimals": 9,
    }
    similarity = analyzer._compute_rug_similarity(token_info)
    assert similarity == 0.0


# --- Pattern matching integration ---


def test_pattern_confidence_access_control():
    analyzer = SolanaProgramAnalyzer()
    pattern = {"category": "access_control", "indicators": ["Missing #[account(signer)] in Anchor"]}
    idl_analysis = {"missing_signer_checks": 2}
    authority_info = None

    confidence = analyzer._compute_pattern_confidence(pattern, idl_analysis, authority_info)
    assert confidence >= 0.6


def test_pattern_confidence_no_match():
    analyzer = SolanaProgramAnalyzer()
    pattern = {"category": "access_control", "indicators": []}
    idl_analysis = {"missing_signer_checks": 0}
    authority_info = None

    confidence = analyzer._compute_pattern_confidence(pattern, idl_analysis, authority_info)
    assert confidence == 0.0


def test_pattern_confidence_rug_pull():
    analyzer = SolanaProgramAnalyzer()
    pattern = {"category": "rug_pull", "indicators": ["Upgrade authority active"]}
    idl_analysis = {"has_idl": False}
    authority_info = {"upgradeable": True}

    confidence = analyzer._compute_pattern_confidence(pattern, idl_analysis, authority_info)
    assert confidence >= 0.5  # upgradeable + no IDL
