"""Tests for the Solana scan API endpoint schemas."""

from nile.schemas.solana_scan import (
    ExploitMatch,
    SolanaScanRequest,
    SolanaScanResponse,
    SolanaScanScoreBreakdown,
)
from nile.services.chain_service import validate_solana_address


def test_scan_request_valid():
    req = SolanaScanRequest(program_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    assert req.program_address == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def test_scan_request_rejects_short():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SolanaScanRequest(program_address="abc")


def test_scan_response_construction():
    resp = SolanaScanResponse(
        address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        analysis_type="program",
        total_score=85.5,
        grade="A",
        scores=SolanaScanScoreBreakdown(name=80, image=90, likeness=85, essence=87),
        details={"name": {}, "image": {}, "likeness": {}, "essence": {}},
        exploit_matches=[],
    )
    assert resp.total_score == 85.5
    assert resp.grade == "A"
    assert resp.scores.name == 80


def test_exploit_match_schema():
    match = ExploitMatch(
        pattern_id="SOL-008",
        name="Missing Signer Check",
        category="access_control",
        severity="critical",
        confidence=0.75,
        cwe="CWE-862",
        indicators_matched=["Missing #[account(signer)] in Anchor"],
    )
    assert match.confidence == 0.75
    assert match.severity == "critical"


def test_address_validation_in_scan_context():
    # Valid Solana addresses that the scan endpoint should accept
    assert validate_solana_address("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA") is True
    assert validate_solana_address("11111111111111111111111111111111") is True

    # Invalid addresses that the scan endpoint should reject
    assert validate_solana_address("0xdead") is False
    assert validate_solana_address("") is False
