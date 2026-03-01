"""Solana Program Analyzer — the core NILE Security product.

Takes a Solana program or token address, queries on-chain data,
runs pattern matching against known exploits, and produces
NILE scoring inputs across all four dimensions (Name, Image, Likeness, Essence).
"""

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

        # Determine if this is a program or token
        program_info = await chain_service.get_program_info(address)
        token_info = await chain_service.get_token_info(address)

        if program_info and program_info.get("executable"):
            return await self._analyze_program(address, program_info)
        elif token_info and token_info.get("exists", False):
            return await self._analyze_token(address, token_info)
        else:
            return {"error": "Address is not a recognized program or token", "address": address}

    async def _analyze_program(self, address: str, program_info: dict) -> dict:
        """Analyze an executable Solana program."""
        # Fetch IDL
        idl = await fetch_idl(address)
        idl_analysis = analyze_idl_security(idl) if idl else analyze_idl_security({})

        # Get upgrade authority info
        authority_info = await chain_service.get_program_authority(address)

        # Ecosystem checks
        ecosystem = await assess_ecosystem_presence(address)

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
        """Analyze an SPL token mint."""
        ecosystem = await assess_ecosystem_presence(address)

        # Token-specific exploit matching
        exploit_matches = self._match_token_exploit_patterns(token_info)

        # Build scoring inputs for a token
        name_inputs = NameInputs(
            is_verified=ecosystem.get("jupiter_strict_list", False),
            audit_count=0,
            age_days=ecosystem.get("age_days", 0),
            team_identified=bool(ecosystem.get("known_program")),
            ecosystem_score=ecosystem.get("ecosystem_score", 0.0),
        )

        # Token security assessment
        image_inputs = ImageInputs(
            missing_signer_checks=0,
            missing_owner_checks=1 if token_info.get("mint_authority_active") else 0,
        )

        likeness_inputs = LikenessInputs(
            exploit_pattern_matches=exploit_matches,
            rug_pattern_similarity=self._compute_rug_similarity(token_info),
        )

        essence_inputs = EssenceInputs(
            upgrade_authority_active=token_info.get("mint_authority_active", False),
        )

        score = compute_nile_score(name_inputs, image_inputs, likeness_inputs, essence_inputs)

        return {
            "address": address,
            "analysis_type": "token",
            "score": score,
            "token_info": token_info,
            "ecosystem": ecosystem,
            "exploit_matches": exploit_matches,
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

    def _match_token_exploit_patterns(self, token_info: dict) -> list[dict]:
        """Match token against rug pull patterns."""
        patterns = _load_exploit_patterns()
        matches = []

        for pattern in patterns:
            if pattern.get("category") != "rug_pull":
                continue

            confidence = self._compute_token_rug_confidence(token_info)
            if confidence > 0.3:
                indicators = []
                if token_info.get("mint_authority_active"):
                    indicators.append("Mint authority not revoked")
                if token_info.get("freeze_authority_active"):
                    indicators.append("Freeze authority active")

                matches.append(
                    {
                        "pattern_id": pattern["id"],
                        "name": pattern["name"],
                        "category": "rug_pull",
                        "severity": "critical",
                        "confidence": round(confidence, 2),
                        "cwe": pattern.get("cwe"),
                        "indicators_matched": indicators,
                    }
                )

        return matches

    def _compute_token_rug_confidence(self, token_info: dict) -> float:
        """Compute rug pull risk for an SPL token."""
        confidence = 0.0

        if token_info.get("mint_authority_active"):
            confidence += 0.3  # Can mint unlimited tokens
        if token_info.get("freeze_authority_active"):
            confidence += 0.2  # Can freeze user accounts

        return min(1.0, confidence)

    def _compute_rug_similarity(self, token_info: dict) -> float:
        """Compute similarity to known rug pull token patterns (0-1)."""
        score = 0.0

        if token_info.get("mint_authority_active"):
            score += 0.35
        if token_info.get("freeze_authority_active"):
            score += 0.25
        # Low supply with active authorities is a red flag
        supply = token_info.get("supply", 0)
        decimals = token_info.get("decimals", 0)
        if supply > 0 and decimals > 0:
            normalized = supply / (10**decimals)
            if normalized < 1000:
                score += 0.1

        return min(1.0, score)


# Singleton
program_analyzer = SolanaProgramAnalyzer()
