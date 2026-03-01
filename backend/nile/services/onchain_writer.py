"""On-chain writer — submits NILE scores to the Solana program after off-chain computation.

Feature-flagged: only writes on-chain if NILE_PROGRAM_ID is configured.
"""

import json
import logging
from pathlib import Path

from nile.config import settings

logger = logging.getLogger(__name__)

# Load IDL for program interaction
_IDL_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "target" / "idl" / "nile_security.json"
)


def _is_enabled() -> bool:
    return bool(settings.program_id and settings.deployer_private_key)


def _load_idl() -> dict | None:
    if not _IDL_PATH.exists():
        logger.warning("NILE program IDL not found at %s", _IDL_PATH)
        return None
    return json.loads(_IDL_PATH.read_text())  # type: ignore[no-any-return]


async def submit_score_onchain(
    program_address: str,
    name_score: int,
    image_score: int,
    likeness_score: int,
    essence_score: int,
    details_uri: str = "",
) -> str | None:
    """Submit a NILE score on-chain for a registered program.

    Returns the transaction signature on success, None if disabled or failed.
    """
    if not _is_enabled():
        logger.debug("On-chain writing disabled (no program_id or deployer key)")
        return None

    try:
        import base58
        from solana.rpc.async_api import AsyncClient
        from solders.keypair import Keypair as SoldersKeypair
        from solders.pubkey import Pubkey

        # Load deployer keypair
        key_bytes = base58.b58decode(settings.deployer_private_key)
        deployer = SoldersKeypair.from_bytes(key_bytes[:64])
        program_id = Pubkey.from_string(settings.program_id)
        target = Pubkey.from_string(program_address)

        # Derive PDAs
        authority_pda, _ = Pubkey.find_program_address([b"nile_authority"], program_id)
        profile_pda, _ = Pubkey.find_program_address([b"program", bytes(target)], program_id)
        agent_pda, _ = Pubkey.find_program_address([b"agent", bytes(deployer.pubkey())], program_id)

        # Build instruction data using Anchor discriminator
        # submit_score discriminator: first 8 bytes of sha256("global:submit_score")
        import hashlib

        disc = hashlib.sha256(b"global:submit_score").digest()[:8]

        # Encode args: u8 x4 + string (4-byte len prefix + utf8)
        uri_bytes = details_uri.encode("utf-8")
        import struct

        data = (
            disc
            + struct.pack("<B", min(100, max(0, name_score)))
            + struct.pack("<B", min(100, max(0, image_score)))
            + struct.pack("<B", min(100, max(0, likeness_score)))
            + struct.pack("<B", min(100, max(0, essence_score)))
            + struct.pack("<I", len(uri_bytes))
            + uri_bytes
        )

        # Build transaction with AccountMeta
        from solders.instruction import AccountMeta, Instruction

        ix = Instruction(
            program_id,
            data,
            [
                AccountMeta(profile_pda, is_signer=False, is_writable=True),
                AccountMeta(agent_pda, is_signer=False, is_writable=True),
                AccountMeta(authority_pda, is_signer=False, is_writable=True),
                AccountMeta(deployer.pubkey(), is_signer=True, is_writable=False),
            ],
        )

        client = AsyncClient(settings.solana_rpc_url)
        try:
            blockhash_resp = await client.get_latest_blockhash()
            blockhash = blockhash_resp.value.blockhash

            from solders.message import Message
            from solders.transaction import Transaction as SoldersTx

            msg = Message.new_with_blockhash([ix], deployer.pubkey(), blockhash)
            tx = SoldersTx.new([deployer], msg, blockhash)

            result = await client.send_transaction(tx)
            sig = str(result.value)

            logger.info(
                "Score submitted on-chain: %s → tx %s (N=%d I=%d L=%d E=%d)",
                program_address,
                sig,
                name_score,
                image_score,
                likeness_score,
                essence_score,
            )
            return sig
        finally:
            await client.close()

    except ImportError:
        logger.warning("solders/solana not installed — on-chain writing unavailable")
        return None
    except Exception:
        logger.exception("Failed to submit score on-chain for %s", program_address)
        return None


async def register_program_onchain(
    program_address: str,
    name: str,
) -> str | None:
    """Register a program on-chain for NILE scoring.

    Returns the transaction signature on success, None if disabled or failed.
    """
    if not _is_enabled():
        return None

    try:
        import hashlib
        import struct

        import base58
        from solana.rpc.async_api import AsyncClient
        from solders.keypair import Keypair as SoldersKeypair
        from solders.pubkey import Pubkey

        key_bytes = base58.b58decode(settings.deployer_private_key)
        deployer = SoldersKeypair.from_bytes(key_bytes[:64])
        program_id = Pubkey.from_string(settings.program_id)
        target = Pubkey.from_string(program_address)

        profile_pda, _ = Pubkey.find_program_address([b"program", bytes(target)], program_id)

        disc = hashlib.sha256(b"global:register_program").digest()[:8]
        name_bytes = name.encode("utf-8")
        data = disc + bytes(target) + struct.pack("<I", len(name_bytes)) + name_bytes

        from solders.instruction import AccountMeta, Instruction
        from solders.system_program import ID as SYS_PROGRAM_ID

        ix = Instruction(
            program_id,
            data,
            [
                AccountMeta(profile_pda, is_signer=False, is_writable=True),
                AccountMeta(deployer.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
        )

        client = AsyncClient(settings.solana_rpc_url)
        try:
            blockhash_resp = await client.get_latest_blockhash()
            blockhash = blockhash_resp.value.blockhash

            from solders.message import Message
            from solders.transaction import Transaction as SoldersTx

            msg = Message.new_with_blockhash([ix], deployer.pubkey(), blockhash)
            tx = SoldersTx.new([deployer], msg, blockhash)

            result = await client.send_transaction(tx)
            sig = str(result.value)

            logger.info(
                "Program registered on-chain: %s (%s) → tx %s",
                program_address,
                name,
                sig,
            )
            return sig
        finally:
            await client.close()

    except Exception:
        logger.exception("Failed to register program on-chain: %s", program_address)
        return None
