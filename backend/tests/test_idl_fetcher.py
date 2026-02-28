"""Tests for idl_fetcher — Anchor IDL security analysis."""

from nile.services.idl_fetcher import analyze_idl_security


class TestAnalyzeIdlSecurity:
    def test_none_idl(self):
        result = analyze_idl_security(None)
        assert result["has_idl"] is False
        assert result["instruction_count"] == 0

    def test_empty_idl(self):
        result = analyze_idl_security({})
        assert result["has_idl"] is False

    def test_sample_idl(self, sample_idl):
        result = analyze_idl_security(sample_idl)
        assert result["has_idl"] is True
        assert result["instruction_count"] == 2
        assert result["total_accounts"] == 6

    def test_unsafe_idl(self, unsafe_idl):
        result = analyze_idl_security(unsafe_idl)
        assert result["has_idl"] is True
        assert result["missing_signer_checks"] > 0
        assert result["unvalidated_accounts"] > 0

    def test_validation_rate_calculated(self, sample_idl):
        result = analyze_idl_security(sample_idl)
        assert result["account_validation_rate"] > 0
        assert result["total_accounts"] == 6

    def test_cpi_detection(self):
        idl = {
            "instructions": [
                {
                    "name": "cross_invoke",
                    "accounts": [
                        {"name": "source", "isMut": True, "isSigner": True}
                    ],
                    "args": [{"name": "target_program", "type": "pubkey"}],
                }
            ]
        }
        result = analyze_idl_security(idl)
        assert result["unsafe_cpi_calls"] == 1

    def test_account_types_recognized(self):
        idl = {
            "instructions": [
                {
                    "name": "test",
                    "accounts": [
                        {
                            "name": "validated",
                            "isMut": True,
                            "isSigner": False,
                            "type": {"kind": "account"},
                        },
                        {
                            "name": "unvalidated",
                            "isMut": True,
                            "isSigner": False,
                        },
                    ],
                    "args": [],
                }
            ]
        }
        result = analyze_idl_security(idl)
        assert result["unvalidated_accounts"] == 1
        assert result["account_validation_rate"] == 50.0
