"""Tests for IDL security analysis — deeper coverage of the idl_fetcher module."""

from nile.services.idl_fetcher import analyze_idl_security


def test_single_instruction_all_validated():
    """All accounts have types or signer constraints."""
    idl = {
        "instructions": [
            {
                "name": "init",
                "accounts": [
                    {"name": "admin", "isMut": True, "isSigner": True},
                    {
                        "name": "config", "isMut": True, "isSigner": False,
                        "type": {"kind": "account"},
                    },
                    {
                        "name": "system", "isMut": False, "isSigner": False,
                        "type": {"kind": "program"},
                    },
                ],
                "args": [],
            }
        ],
    }
    result = analyze_idl_security(idl)
    assert result["has_idl"] is True
    assert result["instruction_count"] == 1
    assert result["total_accounts"] == 3
    assert result["missing_signer_checks"] == 0
    assert result["account_validation_rate"] == 100.0


def test_multiple_instructions():
    """IDL with multiple instructions aggregates correctly."""
    idl = {
        "instructions": [
            {
                "name": "init",
                "accounts": [
                    {"name": "admin", "isMut": True, "isSigner": True},
                ],
                "args": [],
            },
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
    assert result["instruction_count"] == 2
    assert result["total_accounts"] == 3
    assert result["missing_signer_checks"] == 2  # from + to are mutable non-signers
    assert result["unvalidated_accounts"] == 2


def test_no_instructions():
    """IDL with empty instructions list."""
    idl = {"instructions": []}
    result = analyze_idl_security(idl)
    assert result["instruction_count"] == 0
    assert result["total_accounts"] == 0


def test_instruction_with_cpi_target():
    """Instructions referencing external programs should flag CPI."""
    idl = {
        "instructions": [
            {
                "name": "swap",
                "accounts": [
                    {"name": "user", "isMut": True, "isSigner": True},
                    {
                        "name": "token_program", "isMut": False,
                        "isSigner": False, "type": {"kind": "program"},
                    },
                    {"name": "dex_program", "isMut": False, "isSigner": False},
                ],
                "args": [],
            }
        ],
    }
    result = analyze_idl_security(idl)
    assert result["instruction_count"] == 1
    # dex_program is a non-typed, non-signer account → unvalidated
    assert result["unvalidated_accounts"] >= 1


def test_validation_rate_calculation():
    """Validation rate should be percentage of validated accounts."""
    idl = {
        "instructions": [
            {
                "name": "action",
                "accounts": [
                    {"name": "a", "isMut": True, "isSigner": True},
                    {
                        "name": "b", "isMut": True, "isSigner": False,
                        "type": {"kind": "account"},
                    },
                    {"name": "c", "isMut": True, "isSigner": False},
                    {"name": "d", "isMut": False, "isSigner": False},
                ],
                "args": [],
            }
        ],
    }
    result = analyze_idl_security(idl)
    assert result["total_accounts"] == 4
    assert result["unvalidated_accounts"] == 2
    assert result["account_validation_rate"] == 50.0
