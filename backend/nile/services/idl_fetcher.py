"""IDL fetcher — retrieves Anchor IDL for a Solana program from on-chain or registry."""

import json
import logging

from nile.services.chain_service import chain_service, validate_solana_address

logger = logging.getLogger(__name__)

# Anchor IDL account discriminator (first 8 bytes)
IDL_ACCOUNT_DISCRIMINATOR = bytes([0x18, 0x46, 0xBB, 0xCA, 0xBF, 0x5B, 0x5D, 0xD1])


async def fetch_idl(program_address: str) -> dict | None:
    """Fetch Anchor IDL for a Solana program.

    Tries in order:
    1. On-chain IDL account (standard Anchor IDL PDA)
    2. Returns None if not found
    """
    if not validate_solana_address(program_address):
        return None

    # Try on-chain IDL account
    idl = await _fetch_onchain_idl(program_address)
    if idl:
        return idl

    logger.info("No IDL found for program: %s", program_address)
    return None


async def _fetch_onchain_idl(program_address: str) -> dict | None:
    """Fetch IDL from the on-chain Anchor IDL account.

    Anchor stores IDL at a PDA derived from:
    seeds = [b"anchor:idl", program_id]
    program = program_id
    """
    try:
        from solders.pubkey import Pubkey

        program_pubkey = Pubkey.from_string(program_address)

        # Derive the IDL account PDA
        idl_address, _ = Pubkey.find_program_address(
            [b"anchor:idl", bytes(program_pubkey)],
            program_pubkey,
        )

        resp = await chain_service.async_client.get_account_info(idl_address)
        if resp.value is None:
            return None

        data = resp.value.data
        if len(data) < 44:
            return None

        # Skip 8-byte discriminator + 4-byte authority option + 32-byte authority
        # Then 4-byte data length prefix + compressed IDL data
        import struct
        import zlib

        offset = 44  # 8 + 4 + 32
        if len(data) < offset + 4:
            return None

        data_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        if len(data) < offset + data_len:
            return None

        compressed = data[offset : offset + data_len]

        try:
            idl_json = zlib.decompress(compressed)
        except zlib.error:
            # Might not be compressed (older Anchor versions)
            idl_json = compressed

        return json.loads(idl_json)  # type: ignore[no-any-return]

    except Exception:
        logger.debug("Failed to fetch on-chain IDL for %s", program_address)
        return None


def analyze_idl_security(idl: dict) -> dict:
    """Analyze an Anchor IDL for security signals.

    Returns counts of potential issues:
    - missing_signer_checks: accounts without signer constraint
    - unvalidated_accounts: accounts without owner/seeds constraints
    - unsafe_cpi_calls: invoke calls without program validation
    - instruction_count: total instructions
    - account_validation_rate: % of accounts with proper constraints
    """
    if not idl:
        return {
            "instruction_count": 0,
            "missing_signer_checks": 0,
            "unvalidated_accounts": 0,
            "unsafe_cpi_calls": 0,
            "account_validation_rate": 0.0,
            "has_idl": False,
        }

    instructions = idl.get("instructions", [])
    total_accounts = 0
    validated_accounts = 0
    missing_signers = 0
    unvalidated = 0
    cpi_targets = set()

    for ix in instructions:
        accounts = ix.get("accounts", [])
        for acc in accounts:
            total_accounts += 1
            is_signer = acc.get("isSigner", False)
            is_mut = acc.get("isMut", False)

            # Check if account has proper constraints
            has_constraint = False
            if is_signer:
                has_constraint = True
            # In IDL, account types like "Account" vs "UncheckedAccount" indicate validation
            acc_type = acc.get("type", {})
            if isinstance(acc_type, dict):
                kind = acc_type.get("kind", "")
                if kind in ("account", "program"):
                    has_constraint = True

            if has_constraint:
                validated_accounts += 1
            else:
                unvalidated += 1

            # Mutable accounts without signer = potential issue
            if is_mut and not is_signer and not has_constraint:
                missing_signers += 1

    # Check for CPI-related instructions
    for ix in instructions:
        args = ix.get("args", [])
        for arg in args:
            if "program" in arg.get("name", "").lower():
                cpi_targets.add(ix.get("name", ""))

    validation_rate = (validated_accounts / total_accounts * 100) if total_accounts > 0 else 0.0

    return {
        "instruction_count": len(instructions),
        "missing_signer_checks": missing_signers,
        "unvalidated_accounts": unvalidated,
        "unsafe_cpi_calls": len(cpi_targets),
        "account_validation_rate": round(validation_rate, 1),
        "total_accounts": total_accounts,
        "has_idl": True,
    }
