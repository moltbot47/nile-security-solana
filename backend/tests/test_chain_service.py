"""Tests for Solana chain service — address validation and helper functions."""

from nile.services.chain_service import validate_solana_address

# --- Address validation tests ---

def test_valid_solana_address():
    # SPL Token Program
    assert validate_solana_address("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA") is True


def test_valid_system_program():
    assert validate_solana_address("11111111111111111111111111111111") is True


def test_invalid_too_short():
    assert validate_solana_address("abc") is False


def test_invalid_empty():
    assert validate_solana_address("") is False


def test_invalid_eth_address():
    # Ethereum addresses should fail Solana validation
    assert validate_solana_address("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD08") is False


def test_invalid_non_base58():
    # Contains 'O' and 'I' which aren't in base58
    assert validate_solana_address("OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO") is False


def test_invalid_wrong_length_decoded():
    # Valid base58 but decodes to wrong length (not 32 bytes)
    assert validate_solana_address("1") is False
