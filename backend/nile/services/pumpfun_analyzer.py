"""Pump.fun token heuristic analyzer — deep on-chain risk signals for SPL tokens.

Analyzes holder concentration, creator wallet behavior, liquidity pool existence,
and token age to produce pump.fun-specific risk flags that feed into the NILE
scoring pipeline.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Thresholds
CONCENTRATION_EXTREME_PCT = 80.0  # Top-5 wallets hold >80% supply
CONCENTRATION_HIGH_PCT = 60.0
SINGLE_WHALE_PCT = 50.0  # One holder >50%
WHALE_THRESHOLD_PCT = 5.0  # >5% supply = whale
SERIAL_DEPLOYER_MIN_TOKENS = 5
VERY_YOUNG_TOKEN_DAYS = 1.0
YOUNG_TOKEN_DAYS = 7.0


@dataclass
class PumpFunAnalysis:
    """Results from pump.fun token heuristic analysis."""

    # Holder concentration
    top_holders: list[dict] = field(default_factory=list)
    top5_concentration_pct: float = 0.0
    top10_concentration_pct: float = 0.0
    whale_count: int = 0

    # Creator analysis
    creator_address: str | None = None
    creator_token_count: int = 0
    serial_deployer: bool = False

    # Liquidity analysis
    has_raydium_lp: bool = False
    has_orca_lp: bool = False
    lp_detected: bool = False

    # Token age
    mint_age_seconds: int | None = None
    mint_age_days: float = 0.0

    # Composite risk
    risk_flags: list[str] = field(default_factory=list)
    risk_score: float = 0.0


class PumpFunTokenAnalyzer:
    """Analyzes SPL tokens for pump.fun-specific rug pull risk signals."""

    async def analyze(self, mint_address: str, token_info: dict) -> PumpFunAnalysis:
        """Run all pump.fun heuristic checks on a token mint.

        Args:
            mint_address: The SPL token mint address.
            token_info: Token info dict from chain_service.get_token_info().

        Returns:
            PumpFunAnalysis with all risk signals populated.
        """
        supply = token_info.get("supply", 0)
        decimals = token_info.get("decimals", 0)

        holder_data = await self._analyze_holder_concentration(mint_address, supply, decimals)
        creator_data = await self._analyze_creator_wallet(token_info, mint_address)
        lp_data = await self._detect_liquidity_pools(mint_address)
        age_data = await self._estimate_token_age(mint_address)

        # Check if token is on Jupiter (used for stablecoin exception)
        from nile.services.ecosystem_checker import check_jupiter_strict_list

        on_jupiter = await check_jupiter_strict_list(mint_address)

        risk_flags = self._compute_risk_flags(
            token_info=token_info,
            holder_data=holder_data,
            creator_data=creator_data,
            lp_data=lp_data,
            age_data=age_data,
            on_jupiter=on_jupiter,
        )
        risk_score = self._compute_risk_score(
            token_info=token_info,
            holder_data=holder_data,
            creator_data=creator_data,
            lp_data=lp_data,
            age_data=age_data,
        )

        return PumpFunAnalysis(
            # Holder concentration
            top_holders=holder_data.get("top_holders", []),
            top5_concentration_pct=holder_data.get("top5_pct", 0.0),
            top10_concentration_pct=holder_data.get("top10_pct", 0.0),
            whale_count=holder_data.get("whale_count", 0),
            # Creator
            creator_address=creator_data.get("creator_address"),
            creator_token_count=creator_data.get("token_count", 0),
            serial_deployer=creator_data.get("serial_deployer", False),
            # Liquidity
            has_raydium_lp=lp_data.get("has_raydium_lp", False),
            has_orca_lp=lp_data.get("has_orca_lp", False),
            lp_detected=lp_data.get("lp_detected", False),
            # Age
            mint_age_seconds=age_data.get("age_seconds"),
            mint_age_days=age_data.get("age_days", 0.0),
            # Risk
            risk_flags=risk_flags,
            risk_score=risk_score,
        )

    async def _analyze_holder_concentration(
        self, mint_address: str, supply: int, decimals: int
    ) -> dict:
        """Analyze token holder concentration from top accounts."""
        from nile.services.chain_service import chain_service

        result: dict = {
            "top_holders": [],
            "top5_pct": 0.0,
            "top10_pct": 0.0,
            "whale_count": 0,
        }

        accounts = await chain_service.get_token_largest_accounts(mint_address)
        if not accounts:
            return result

        # Compute total from top holders (use raw amounts)
        if supply <= 0:
            return result

        top_holders = []
        for acc in accounts:
            amount = acc.get("amount", 0)
            pct = (amount / supply) * 100 if supply > 0 else 0.0
            top_holders.append(
                {
                    "address": acc.get("address", ""),
                    "amount": amount,
                    "pct": round(pct, 2),
                }
            )

        result["top_holders"] = top_holders

        # Top-5 and top-10 concentration
        sorted_holders = sorted(top_holders, key=lambda h: h["pct"], reverse=True)
        result["top5_pct"] = round(sum(h["pct"] for h in sorted_holders[:5]), 2)
        result["top10_pct"] = round(sum(h["pct"] for h in sorted_holders[:10]), 2)

        # Whale count (>5% supply)
        result["whale_count"] = sum(
            1 for h in sorted_holders if h["pct"] > WHALE_THRESHOLD_PCT
        )

        return result

    async def _analyze_creator_wallet(self, token_info: dict, mint_address: str) -> dict:
        """Analyze the token creator's wallet for serial deployment patterns."""
        from nile.services.chain_service import chain_service

        result: dict = {
            "creator_address": None,
            "token_count": 0,
            "serial_deployer": False,
        }

        # Use mint authority as creator address
        creator = token_info.get("mint_authority")

        # Fallback: first transaction signer on the mint
        if not creator:
            history = await chain_service.get_transaction_history(mint_address, limit=1)
            if history:
                # Oldest transaction is last in list (sorted desc by default)
                # but with limit=1 we get only the most recent — use it as fallback
                pass  # Cannot determine creator from signature alone without full tx parsing

        if not creator:
            return result

        result["creator_address"] = creator

        # Count token accounts owned by creator
        token_accounts = await chain_service.get_token_accounts_by_owner(creator)
        result["token_count"] = len(token_accounts)
        result["serial_deployer"] = len(token_accounts) >= SERIAL_DEPLOYER_MIN_TOKENS

        return result

    async def _detect_liquidity_pools(self, mint_address: str) -> dict:
        """Detect if token has liquidity pools on major Solana DEXes.

        For MVP, uses Jupiter strict list as proxy — tokens listed on Jupiter
        must have active LP pools (Raydium, Orca, or other supported DEXes).
        """
        from nile.services.ecosystem_checker import check_dex_pool_exists

        return await check_dex_pool_exists(mint_address)

    async def _estimate_token_age(self, mint_address: str) -> dict:
        """Estimate token age from first transaction on the mint account."""
        from nile.services.ecosystem_checker import check_program_age_days

        age_days = await check_program_age_days(mint_address)

        return {
            "age_seconds": int(age_days * 86400) if age_days > 0 else None,
            "age_days": float(age_days),
        }

    def _compute_risk_flags(
        self,
        *,
        token_info: dict,
        holder_data: dict,
        creator_data: dict,
        lp_data: dict,
        age_data: dict,
        on_jupiter: bool,
    ) -> list[str]:
        """Apply heuristic rules to produce human-readable risk flags."""
        flags: list[str] = []

        top5_pct = holder_data.get("top5_pct", 0.0)
        top_holders = holder_data.get("top_holders", [])
        lp_detected = lp_data.get("lp_detected", False)
        age_days = age_data.get("age_days", 0.0)
        mint_auth = token_info.get("mint_authority_active", False)
        freeze_auth = token_info.get("freeze_authority_active", False)

        # Supply concentration
        if top5_pct > CONCENTRATION_EXTREME_PCT:
            flags.append("supply_concentration_extreme")
        elif top5_pct > CONCENTRATION_HIGH_PCT:
            flags.append("supply_concentration_high")

        # Single whale dominance
        if top_holders:
            max_pct = max((h.get("pct", 0.0) for h in top_holders), default=0.0)
            if max_pct > SINGLE_WHALE_PCT:
                flags.append("single_whale_dominance")

        # Serial deployer
        if creator_data.get("serial_deployer", False):
            flags.append("serial_deployer")

        # No liquidity pool
        if not lp_detected:
            flags.append("no_liquidity_pool")

        # Honeypot: freeze authority + no LP (skip for Jupiter-listed tokens / stablecoins)
        if freeze_auth and not lp_detected and not on_jupiter:
            flags.append("honeypot_token")

        # Token age
        if age_days < VERY_YOUNG_TOKEN_DAYS:
            if mint_auth:
                flags.append("young_token_with_mint_authority")
            else:
                flags.append("very_young_token")
        elif age_days < YOUNG_TOKEN_DAYS and mint_auth:
            flags.append("young_token_with_mint_authority")

        return flags

    def _compute_risk_score(
        self,
        *,
        token_info: dict,
        holder_data: dict,
        creator_data: dict,
        lp_data: dict,
        age_data: dict,
    ) -> float:
        """Compute weighted risk score from all signals. 0 = safe, 1 = max risk."""
        score = 0.0

        top5_pct = holder_data.get("top5_pct", 0.0)
        top_holders = holder_data.get("top_holders", [])
        lp_detected = lp_data.get("lp_detected", False)
        age_days = age_data.get("age_days", 0.0)
        mint_auth = token_info.get("mint_authority_active", False)
        freeze_auth = token_info.get("freeze_authority_active", False)

        # Holder concentration
        if top5_pct > CONCENTRATION_EXTREME_PCT:
            score += 0.25
        elif top5_pct > CONCENTRATION_HIGH_PCT:
            score += 0.15

        # Single whale
        if top_holders:
            max_pct = max((h.get("pct", 0.0) for h in top_holders), default=0.0)
            if max_pct > SINGLE_WHALE_PCT:
                score += 0.15

        # Serial deployer
        if creator_data.get("serial_deployer", False):
            score += 0.15

        # No liquidity pool
        if not lp_detected:
            score += 0.20

        # Freeze authority + no LP (honeypot)
        if freeze_auth and not lp_detected:
            score += 0.10

        # Young token with mint authority
        if age_days < VERY_YOUNG_TOKEN_DAYS and mint_auth:
            score += 0.20
        elif age_days < VERY_YOUNG_TOKEN_DAYS or (age_days < YOUNG_TOKEN_DAYS and mint_auth):
            score += 0.10

        return min(1.0, round(score, 3))


# Singleton
pumpfun_analyzer = PumpFunTokenAnalyzer()
