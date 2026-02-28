"""Tests for chain_service — Solana address validation and chain service init."""

from nile.services.chain_service import SolanaChainService, validate_solana_address


class TestValidateSolanaAddress:
    def test_valid_base58_32_bytes(self):
        assert validate_solana_address("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA") is True

    def test_system_program(self):
        assert validate_solana_address("11111111111111111111111111111111") is True

    def test_empty_string(self):
        assert validate_solana_address("") is False

    def test_invalid_characters(self):
        assert validate_solana_address("0OIl_not_base58!") is False

    def test_too_short(self):
        assert validate_solana_address("abc") is False

    def test_too_long(self):
        assert validate_solana_address("A" * 100) is False


class TestSolanaChainServiceInit:
    def test_creates_instance(self):
        service = SolanaChainService()
        assert service._client is None
        assert service._async_client is None
        assert service._program is None
