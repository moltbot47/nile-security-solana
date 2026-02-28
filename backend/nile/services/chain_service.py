"""Chain integration service — Solana interactions for NILE Security ecosystem."""

import json
import logging
from pathlib import Path

import base58

from nile.config import settings

logger = logging.getLogger(__name__)

# Anchor IDL paths (loaded from Anchor build output)
IDL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "target" / "idl"


def _load_idl(program_name: str) -> dict | None:
    """Load IDL from Anchor build artifacts."""
    idl_path = IDL_DIR / f"{program_name}.json"
    if not idl_path.exists():
        logger.warning("IDL not found: %s", idl_path)
        return None
    return json.loads(idl_path.read_text())


def validate_solana_address(address: str) -> bool:
    """Validate a Solana base58 public key."""
    try:
        decoded = base58.b58decode(address)
        return len(decoded) == 32
    except Exception:
        return False


class SolanaChainService:
    """Handles all Solana RPC interactions for NILE Security."""

    def __init__(self) -> None:
        self._client = None
        self._async_client = None
        self._program = None

    @property
    def client(self):
        """Lazy synchronous Solana RPC client."""
        if self._client is None:
            try:
                from solders.rpc.api import Client
                self._client = Client(settings.solana_rpc_url)
            except ImportError:
                logger.error("solders not installed — run: pip install solders")
                raise
        return self._client

    @property
    def async_client(self):
        """Lazy async Solana RPC client."""
        if self._async_client is None:
            try:
                from solders.rpc.async_api import AsyncClient
                self._async_client = AsyncClient(settings.solana_rpc_url)
            except ImportError:
                logger.error("solders not installed — run: pip install solders")
                raise
        return self._async_client

    # --- Read Operations ---

    async def get_program_info(self, program_address: str) -> dict | None:
        """Get on-chain info about a Solana program."""
        if not validate_solana_address(program_address):
            logger.error("Invalid Solana address: %s", program_address)
            return None
        try:
            from solders.pubkey import Pubkey
            pubkey = Pubkey.from_string(program_address)
            resp = await self.async_client.get_account_info(pubkey)

            if resp.value is None:
                return None

            account = resp.value
            return {
                "address": program_address,
                "executable": account.executable,
                "owner": str(account.owner),
                "lamports": account.lamports,
                "data_len": len(account.data),
            }
        except Exception:
            logger.exception("Failed to get program info: %s", program_address)
            return None

    async def get_program_authority(self, program_address: str) -> dict | None:
        """Check if a program's upgrade authority is active or revoked."""
        if not validate_solana_address(program_address):
            return None
        try:
            from solders.pubkey import Pubkey
            pubkey = Pubkey.from_string(program_address)

            # Programs on Solana have a programdata account that holds the upgrade authority
            # The programdata address is derived from the program address
            resp = await self.async_client.get_account_info(pubkey)
            if resp.value is None:
                return None

            account_data = resp.value.data
            if len(account_data) < 4:
                return {"upgradeable": False, "authority": None}

            # BPF Upgradeable Loader program data account structure:
            # Bytes 0-3: account type (3 = ProgramData)
            # Bytes 4-11: slot deployed
            # Bytes 12: option<authority> (1 = Some, 0 = None)
            # Bytes 13-44: authority pubkey (if Some)

            # First, find the programdata account
            from solders.pubkey import Pubkey as Pk
            bpf_loader = Pk.from_string("BPFLoaderUpgradeab1e11111111111111111111111")

            # Derive programdata address
            programdata_addr, _ = Pk.find_program_address(
                [bytes(pubkey)], bpf_loader
            )
            pd_resp = await self.async_client.get_account_info(programdata_addr)

            if pd_resp.value is None:
                return {"upgradeable": False, "authority": None}

            pd_data = pd_resp.value.data
            if len(pd_data) < 45:
                return {"upgradeable": False, "authority": None}

            has_authority = pd_data[12] == 1
            authority = None
            if has_authority and len(pd_data) >= 45:
                authority_bytes = pd_data[13:45]
                authority = str(Pk.from_bytes(authority_bytes))

            return {
                "upgradeable": has_authority,
                "authority": authority,
                "programdata_address": str(programdata_addr),
            }
        except Exception:
            logger.exception("Failed to check program authority: %s", program_address)
            return None

    async def get_token_info(self, mint_address: str) -> dict | None:
        """Get SPL token mint info (supply, decimals, authorities)."""
        if not validate_solana_address(mint_address):
            return None
        try:
            from solders.pubkey import Pubkey
            pubkey = Pubkey.from_string(mint_address)
            resp = await self.async_client.get_account_info(pubkey)

            if resp.value is None:
                return None

            data = resp.value.data
            if len(data) < 82:
                return None

            # SPL Token Mint layout (82 bytes):
            # 0-3:   mint_authority option (4 bytes: 1=Some/0=None)
            # 4-35:  mint_authority pubkey (32 bytes)
            # 36-43: supply (u64 LE)
            # 44:    decimals (u8)
            # 45:    is_initialized (bool)
            # 46-49: freeze_authority option
            # 50-81: freeze_authority pubkey

            import struct
            has_mint_auth = struct.unpack("<I", data[0:4])[0] == 1
            mint_authority = None
            if has_mint_auth:
                mint_authority = str(Pubkey.from_bytes(data[4:36]))

            supply = struct.unpack("<Q", data[36:44])[0]
            decimals = data[44]

            has_freeze_auth = struct.unpack("<I", data[46:50])[0] == 1
            freeze_authority = None
            if has_freeze_auth:
                freeze_authority = str(Pubkey.from_bytes(data[50:82]))

            return {
                "mint": mint_address,
                "supply": supply,
                "decimals": decimals,
                "mint_authority": mint_authority,
                "mint_authority_active": has_mint_auth,
                "freeze_authority": freeze_authority,
                "freeze_authority_active": has_freeze_auth,
            }
        except Exception:
            logger.exception("Failed to get token info: %s", mint_address)
            return None

    async def get_sol_price_usd(self) -> float | None:
        """Get SOL/USD price from Pyth Network."""
        try:
            from solders.pubkey import Pubkey
            feed_pubkey = Pubkey.from_string(settings.pyth_sol_usd_feed)
            resp = await self.async_client.get_account_info(feed_pubkey)

            if resp.value is None:
                logger.warning("Pyth feed account not found")
                return None

            # Pyth price account parsing (simplified)
            # Full parsing requires pyth-sdk-solana, but we can extract price directly
            data = resp.value.data
            if len(data) < 208:
                return None

            import struct
            # Price is at offset 208 in the Pyth price account (i64)
            # Exponent is at offset 20 (i32)
            exponent = struct.unpack_from("<i", data, 20)[0]
            price = struct.unpack_from("<q", data, 208)[0]

            return price * (10 ** exponent)
        except Exception:
            logger.exception("Failed to get SOL price from Pyth")
            return None

    async def get_transaction_history(
        self, address: str, limit: int = 20
    ) -> list[dict]:
        """Get recent transaction signatures for an address."""
        if not validate_solana_address(address):
            return []
        try:
            from solders.pubkey import Pubkey
            pubkey = Pubkey.from_string(address)
            resp = await self.async_client.get_signatures_for_address(
                pubkey, limit=limit
            )
            return [
                {
                    "signature": str(sig.signature),
                    "slot": sig.slot,
                    "err": sig.err,
                    "block_time": sig.block_time,
                }
                for sig in resp.value
            ]
        except Exception:
            logger.exception("Failed to get tx history: %s", address)
            return []

    # --- Scoring Helpers ---

    async def assess_program_security(self, program_address: str) -> dict:
        """Gather on-chain signals for NILE scoring of a Solana program."""
        result = {
            "address": program_address,
            "exists": False,
            "executable": False,
            "upgrade_authority_active": False,
            "upgrade_authority": None,
            "data_size": 0,
            "age_slots": 0,
        }

        info = await self.get_program_info(program_address)
        if info is None:
            return result

        result["exists"] = True
        result["executable"] = info["executable"]
        result["data_size"] = info["data_len"]

        authority = await self.get_program_authority(program_address)
        if authority:
            result["upgrade_authority_active"] = authority["upgradeable"]
            result["upgrade_authority"] = authority.get("authority")

        return result

    async def assess_token_security(self, mint_address: str) -> dict:
        """Gather on-chain signals for NILE scoring of an SPL token."""
        result = {
            "address": mint_address,
            "exists": False,
            "mint_authority_active": False,
            "freeze_authority_active": False,
            "supply": 0,
            "decimals": 0,
        }

        token_info = await self.get_token_info(mint_address)
        if token_info is None:
            return result

        result.update({
            "exists": True,
            "mint_authority_active": token_info["mint_authority_active"],
            "mint_authority": token_info["mint_authority"],
            "freeze_authority_active": token_info["freeze_authority_active"],
            "freeze_authority": token_info["freeze_authority"],
            "supply": token_info["supply"],
            "decimals": token_info["decimals"],
        })
        return result


# Singleton instance
chain_service = SolanaChainService()
