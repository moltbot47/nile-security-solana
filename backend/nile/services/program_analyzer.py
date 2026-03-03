"""Solana Program Analyzer — the core NILE Security product.

Takes a Solana program or token address, queries on-chain data,
runs pattern matching against known exploits, and produces
NILE scoring inputs across all four dimensions (Name, Image, Likeness, Essence).
"""

import asyncio
import json
import logging
from pathlib import Path

from nile.services.chain_service import chain_service, validate_solana_address
from nile.services.ecosystem_checker import assess_ecosystem_presence, check_known_program
from nile.services.idl_fetcher import analyze_idl_security, fetch_idl
from nile.services.nile_scorer import (
    EssenceInputs,
    ImageInputs,
    LikenessInputs,
    NameInputs,
    compute_nile_score,
)
from nile.services.pumpfun_analyzer import PumpFunAnalysis, pumpfun_analyzer

logger = logging.getLogger(__name__)

# Load exploit patterns once at module level
_EXPLOIT_PATTERNS_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "exploit_patterns"
    / "solana_exploits.json"
)
_EXPLOIT_PATTERNS: list[dict] = []


def _load_exploit_patterns() -> list[dict]:
    global _EXPLOIT_PATTERNS
    if _EXPLOIT_PATTERNS:
        return _EXPLOIT_PATTERNS
    try:
        data = json.loads(_EXPLOIT_PATTERNS_PATH.read_text())
        _EXPLOIT_PATTERNS = data.get("patterns", [])
        logger.info("Loaded %d exploit patterns", len(_EXPLOIT_PATTERNS))
    except Exception:
        logger.warning("Failed to load exploit patterns from %s", _EXPLOIT_PATTERNS_PATH)
        _EXPLOIT_PATTERNS = []
    return _EXPLOIT_PATTERNS


class SolanaProgramAnalyzer:
    """Analyzes a Solana program address and produces a full NILE security score."""

    async def analyze(self, address: str) -> dict:
        """Full analysis pipeline for a Solana program or token.

        Returns:
            dict with keys: score (NileScoreResult), program_info, idl_analysis,
            ecosystem, exploit_matches, analysis_type ("program" or "token")
        """
        if not validate_solana_address(address):
            return {"error": "Invalid Solana address", "address": address}

        # Determine if this is a program or token (parallel RPC)
        program_info, token_info = await asyncio.gather(
            chain_service.get_program_info(address),
            chain_service.get_token_info(address),
        )

        if program_info and program_info.get("executable"):
            return await self._analyze_program(address, program_info)
        elif token_info and token_info.get("exists", False):
            return await self._analyze_token(address, token_info)
        else:
            return {"error": "Address is not a recognized program or token", "address": address}

    async def _analyze_program(self, address: str, program_info: dict) -> dict:
        """Analyze an executable Solana program."""
        # Parallel RPC: IDL, authority, and ecosystem checks
        idl, authority_info, ecosystem = await asyncio.gather(
            fetch_idl(address),
            chain_service.get_program_authority(address),
            assess_ecosystem_presence(address),
        )
        idl_analysis = analyze_idl_security(idl) if idl else analyze_idl_security({})

        # Pattern matching
        exploit_matches = self._match_exploit_patterns(idl_analysis, authority_info)

        # Build scoring inputs
        name_inputs = await self._assess_name(address, idl, ecosystem)
        image_inputs = self._assess_image(idl_analysis)
        likeness_inputs = self._assess_likeness(exploit_matches, idl_analysis)
        essence_inputs = self._assess_essence(idl_analysis, authority_info)

        # Compute final score
        score = compute_nile_score(name_inputs, image_inputs, likeness_inputs, essence_inputs)

        return {
            "address": address,
            "analysis_type": "program",
            "score": score,
            "program_info": program_info,
            "authority_info": authority_info,
            "idl_analysis": idl_analysis,
            "ecosystem": ecosystem,
            "exploit_matches": exploit_matches,
        }

    async def _analyze_token(self, address: str, token_info: dict) -> dict:
        """Analyze an SPL token mint with pump.fun-specific heuristics."""
        # Parallel: ecosystem check + pump.fun analysis
        ecosystem, pf = await asyncio.gather(
            assess_ecosystem_presence(address),
            pumpfun_analyzer.analyze(address, token_info),
        )

        # Token-specific exploit matching (enhanced with pumpfun signals)
        exploit_matches = self._match_token_exploit_patterns(token_info, pf)

        # Build scoring inputs enriched with pump.fun signals
        age_days = ecosystem.get("age_days", 0) or int(pf.mint_age_days)
        name_inputs = NameInputs(
            is_verified=ecosystem.get("jupiter_strict_list", False),
            audit_count=0,
            age_days=age_days,
            team_identified=bool(ecosystem.get("known_program")) and not pf.serial_deployer,
            ecosystem_score=ecosystem.get("ecosystem_score", 0.0),
        )

        # Token security — freeze auth + no LP treated as unsafe CPI risk
        image_inputs = ImageInputs(
            missing_signer_checks=0,
            missing_owner_checks=1 if token_info.get("mint_authority_active") else 0,
            unsafe_cpi_calls=(
                1
                if token_info.get("freeze_authority_active") and not pf.lp_detected
                else 0
            ),
        )

        likeness_inputs = LikenessInputs(
            exploit_pattern_matches=exploit_matches,
            rug_pattern_similarity=self._compute_enhanced_rug_similarity(token_info, pf),
        )

        essence_inputs = EssenceInputs(
            upgrade_authority_active=token_info.get("mint_authority_active", False),
            cpi_call_count=pf.whale_count,  # Centralization penalty
        )

        score = compute_nile_score(name_inputs, image_inputs, likeness_inputs, essence_inputs)

        return {
            "address": address,
            "analysis_type": "token",
            "score": score,
            "token_info": token_info,
            "ecosystem": ecosystem,
            "exploit_matches": exploit_matches,
            "holder_analysis": {
                "top_holders": pf.top_holders[:5],
                "top5_concentration_pct": pf.top5_concentration_pct,
                "top10_concentration_pct": pf.top10_concentration_pct,
                "whale_count": pf.whale_count,
            },
            "liquidity_analysis": {
                "lp_detected": pf.lp_detected,
                "has_raydium_lp": pf.has_raydium_lp,
                "has_orca_lp": pf.has_orca_lp,
            },
            "creator_analysis": {
                "creator_address": pf.creator_address,
                "tokens_created": pf.creator_token_count,
                "serial_deployer": pf.serial_deployer,
            },
            "pumpfun_risk_flags": pf.risk_flags,
        }

    async def _assess_name(self, address: str, idl: dict | None, ecosystem: dict) -> NameInputs:
        """Build Name dimension inputs."""
        is_known = bool(await check_known_program(address))
        return NameInputs(
            is_verified=idl is not None,
            audit_count=3 if is_known else 0,  # Known programs assumed audited
            age_days=ecosystem.get("age_days", 0),
            team_identified=is_known,
            ecosystem_score=ecosystem.get("ecosystem_score", 0.0),
            on_security_txt=ecosystem.get("has_security_txt", False),
        )

    def _assess_image(self, idl_analysis: dict) -> ImageInputs:
        """Build Image dimension inputs from IDL analysis."""
        return ImageInputs(
            missing_signer_checks=idl_analysis.get("missing_signer_checks", 0),
            pda_seed_collisions=0,  # Requires deeper static analysis
            unchecked_arithmetic=0,  # Requires bytecode analysis
            missing_owner_checks=0,  # Partially covered by unvalidated_accounts
            unsafe_cpi_calls=idl_analysis.get("unsafe_cpi_calls", 0),
            unvalidated_accounts=idl_analysis.get("unvalidated_accounts", 0),
        )

    def _assess_likeness(self, exploit_matches: list[dict], idl_analysis: dict) -> LikenessInputs:
        """Build Likeness dimension inputs from pattern matching."""
        return LikenessInputs(
            static_analysis_findings=[],  # Soteria integration deferred (requires local binary)
            exploit_pattern_matches=exploit_matches,
            rug_pattern_similarity=0.0,
        )

    def _assess_essence(self, idl_analysis: dict, authority_info: dict | None) -> EssenceInputs:
        """Build Essence dimension inputs."""
        upgrade_active = False
        if authority_info:
            upgrade_active = authority_info.get("upgradeable", False)

        return EssenceInputs(
            test_coverage_pct=0.0,  # Can't determine from on-chain
            avg_instruction_complexity=max(5.0, idl_analysis.get("instruction_count", 0) * 0.8),
            upgrade_authority_active=upgrade_active,
            upgrade_authority_is_multisig=authority_info.get("is_multisig", False)
            if authority_info
            else False,
            has_timelock=not upgrade_active,  # Conservative: assume no timelock if upgradeable
            cpi_call_count=idl_analysis.get("unsafe_cpi_calls", 0),
        )

    def _match_exploit_patterns(
        self, idl_analysis: dict, authority_info: dict | None
    ) -> list[dict]:
        """Match program against known Solana exploit patterns."""
        patterns = _load_exploit_patterns()
        matches = []

        for pattern in patterns:
            confidence = self._compute_pattern_confidence(pattern, idl_analysis, authority_info)
            if confidence > 0.3:
                matches.append(
                    {
                        "pattern_id": pattern["id"],
                        "name": pattern["name"],
                        "category": pattern["category"],
                        "severity": pattern.get("severity", "medium"),
                        "confidence": round(confidence, 2),
                        "cwe": pattern.get("cwe"),
                        "indicators_matched": self._matched_indicators(
                            pattern, idl_analysis, authority_info
                        ),
                    }
                )

        return matches

    def _compute_pattern_confidence(
        self, pattern: dict, idl_analysis: dict, authority_info: dict | None
    ) -> float:
        """Compute confidence that a program matches an exploit pattern."""
        category = pattern.get("category", "")
        confidence = 0.0

        if category == "access_control" and idl_analysis.get("missing_signer_checks", 0) > 0:
            confidence = 0.6 + min(0.3, idl_analysis["missing_signer_checks"] * 0.1)

        elif category == "account_validation" and idl_analysis.get("unvalidated_accounts", 0) > 0:
            confidence = 0.5 + min(0.3, idl_analysis["unvalidated_accounts"] * 0.08)

        elif category == "cross_program" and idl_analysis.get("unsafe_cpi_calls", 0) > 0:
            confidence = 0.5 + min(0.3, idl_analysis["unsafe_cpi_calls"] * 0.1)

        elif category == "rug_pull":
            if authority_info and authority_info.get("upgradeable"):
                confidence += 0.3
            if not idl_analysis.get("has_idl", False):
                confidence += 0.2

        elif (
            category == "signature_verification"
            and idl_analysis.get("missing_signer_checks", 0) > 1
        ):
            confidence = 0.4

        elif category == "oracle_manipulation":
            # Can only detect if IDL shows oracle account usage without aggregation
            confidence = 0.0  # Requires deeper analysis

        return min(1.0, confidence)

    def _matched_indicators(
        self, pattern: dict, idl_analysis: dict, authority_info: dict | None
    ) -> list[str]:
        """Return which indicators from the pattern were matched."""
        matched = []
        indicators = pattern.get("indicators", [])
        category = pattern.get("category", "")

        if category == "access_control" and idl_analysis.get("missing_signer_checks", 0) > 0:
            for ind in indicators:
                if "signer" in ind.lower():
                    matched.append(ind)

        if category == "account_validation" and idl_analysis.get("unvalidated_accounts", 0) > 0:
            for ind in indicators:
                if "validation" in ind.lower() or "owner" in ind.lower() or "check" in ind.lower():
                    matched.append(ind)

        if category == "rug_pull":
            if authority_info and authority_info.get("upgradeable"):
                matched.append("Upgrade authority active (single signer)")
            if not idl_analysis.get("has_idl", False):
                matched.append("No verified source")

        return matched

    def _match_token_exploit_patterns(
        self, token_info: dict, pf: PumpFunAnalysis | None = None
    ) -> list[dict]:
        """Match token against rug pull patterns including pump.fun-specific ones."""
        patterns = _load_exploit_patterns()
        matches = []

        for pattern in patterns:
            if pattern.get("category") != "rug_pull":
                continue

            pattern_id = pattern.get("id", "")
            confidence = 0.0
            indicators: list[str] = []

            if pattern_id == "SOL-011" and pf:
                # Supply concentration rug
                if pf.top5_concentration_pct > 80:
                    confidence = 0.8
                    indicators.append("Top 5 wallets hold >80% of total supply")
                elif pf.top5_concentration_pct > 60:
                    confidence = 0.5
                    indicators.append("Top 5 wallets hold >60% of total supply")
                if pf.top_holders:
                    max_pct = max(h.get("pct", 0) for h in pf.top_holders)
                    if max_pct > 50:
                        confidence = max(confidence, 0.7)
                        indicators.append("Single wallet holds >50% of supply")

            elif pattern_id == "SOL-012" and pf:
                # Serial deployer
                if pf.serial_deployer:
                    confidence = 0.6
                    indicators.append(
                        f"Creator wallet holds {pf.creator_token_count}+ different token positions"
                    )

            elif pattern_id == "SOL-013" and pf:
                # Illiquid token
                if not pf.lp_detected:
                    confidence = 0.5
                    indicators.append("Not listed on Jupiter strict list")
                    if not pf.has_raydium_lp:
                        indicators.append("No Raydium AMM v4 pool detected")
                    if not pf.has_orca_lp:
                        indicators.append("No Orca Whirlpool pool detected")

            elif pattern_id == "SOL-014" and pf:
                # Honeypot
                if token_info.get("freeze_authority_active") and not (pf.lp_detected):
                    confidence = 0.7
                    indicators.append("Freeze authority active (can freeze any token account)")
                    indicators.append("No LP lock detected")
                    if token_info.get("mint_authority_active"):
                        confidence = 0.85
                        indicators.append("Mint authority also active (double risk)")

            else:
                # Generic rug pull pattern (SOL-006 or any other rug_pull category)
                confidence = self._compute_token_rug_confidence(token_info)
                if token_info.get("mint_authority_active"):
                    indicators.append("Mint authority not revoked")
                if token_info.get("freeze_authority_active"):
                    indicators.append("Freeze authority active")

            if confidence > 0.3:
                matches.append(
                    {
                        "pattern_id": pattern_id,
                        "name": pattern["name"],
                        "category": "rug_pull",
                        "severity": pattern.get("severity", "critical"),
                        "confidence": round(confidence, 2),
                        "cwe": pattern.get("cwe"),
                        "indicators_matched": indicators,
                    }
                )

        return matches

    def _compute_token_rug_confidence(self, token_info: dict) -> float:
        """Compute rug pull risk for an SPL token (basic authority checks)."""
        confidence = 0.0

        if token_info.get("mint_authority_active"):
            confidence += 0.3
        if token_info.get("freeze_authority_active"):
            confidence += 0.2

        return min(1.0, confidence)

    def _compute_enhanced_rug_similarity(
        self, token_info: dict, pf: PumpFunAnalysis
    ) -> float:
        """Enhanced rug similarity incorporating holder concentration, LP, and creator history."""
        score = 0.0

        # Original authority signals
        if token_info.get("mint_authority_active"):
            score += 0.20
        if token_info.get("freeze_authority_active"):
            score += 0.15

        # Holder concentration
        if pf.top5_concentration_pct > 80:
            score += 0.20
        elif pf.top5_concentration_pct > 60:
            score += 0.10

        # No LP
        if not pf.lp_detected:
            score += 0.15

        # Serial deployer
        if pf.serial_deployer:
            score += 0.15

        # Young token with mint authority
        if pf.mint_age_days < 1 and token_info.get("mint_authority_active"):
            score += 0.15
        elif pf.mint_age_days < 7:
            score += 0.05

        return min(1.0, round(score, 3))


# Singleton
program_analyzer = SolanaProgramAnalyzer()
