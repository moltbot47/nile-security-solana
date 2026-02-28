"""NILE Scoring Engine — composite security scoring for Solana programs.

Each program receives a 0-100 score across four equally-weighted dimensions:
  Name (25%):     Source verification, audit history, program age, team identity
  Image (25%):    Security posture — signer checks, PDA safety, CPI risks
  Likeness (25%): Pattern matching against known Solana exploit signatures
  Essence (25%):  Test coverage, complexity, upgrade authority risk, CPI count
"""

from dataclasses import dataclass, field


@dataclass
class NameInputs:
    """Identity & provenance signals for a Solana program."""

    is_verified: bool = False  # Anchor IDL published / source verified on Solscan
    audit_count: int = 0  # Audits by OtterSec, Sec3, Neodyme, Halborn, etc.
    age_days: int = 0  # Days since program deployment
    team_identified: bool = False  # Known team with public identity
    ecosystem_score: float = 0.0  # 0-20: Jupiter strict list, Birdeye verified, DeFi Llama listed
    on_security_txt: bool = False  # Has security.txt (Solana security contact standard)


@dataclass
class ImageInputs:
    """Security posture signals — Solana-specific vulnerability categories."""

    missing_signer_checks: int = 0  # Instructions that don't verify signers
    pda_seed_collisions: int = 0  # Potential PDA seed collision vectors
    unchecked_arithmetic: int = 0  # Arithmetic without overflow checks
    missing_owner_checks: int = 0  # Missing account owner validation
    unsafe_cpi_calls: int = 0  # CPI calls without proper validation
    unvalidated_accounts: int = 0  # Accounts not validated against expected programs
    avg_patch_time_days: float | None = None  # Average time to patch after disclosure
    trend: float = 0.0  # -10 to +10: improving or declining security posture


@dataclass
class LikenessInputs:
    """Pattern matching against known Solana exploit signatures."""

    # Static analysis findings (from custom Rust/Anchor analyzer or Soteria)
    static_analysis_findings: list[dict] = field(default_factory=list)
    # Pattern matches against known Solana exploits (Wormhole, Mango, Cashio, Crema)
    exploit_pattern_matches: list[dict] = field(default_factory=list)
    # Similarity to known rug pull program binaries
    rug_pattern_similarity: float = 0.0  # 0-1: how similar to known rug pull programs


@dataclass
class EssenceInputs:
    """Code quality & complexity signals for Solana programs."""

    test_coverage_pct: float = 0.0  # 0-100: Anchor test coverage
    avg_instruction_complexity: float = 5.0  # Average cyclomatic complexity per ix handler
    upgrade_authority_active: bool = False  # True = program is upgradeable (risk)
    upgrade_authority_is_multisig: bool = False  # Mitigates upgrade risk
    has_timelock: bool = True  # Upgrade timelock present
    cpi_call_count: int = 0  # Number of Cross-Program Invocations
    has_close_account: bool = False  # Whether accounts can be closed (rent reclaim)


@dataclass
class NileScoreResult:
    total_score: float
    name_score: float
    image_score: float
    likeness_score: float
    essence_score: float
    grade: str
    details: dict


GRADE_MAP = [
    (90, "A+"),
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
    (0, "F"),
]


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def compute_name_score(inputs: NameInputs) -> tuple[float, dict]:
    source_score = 20.0 if inputs.is_verified else 0.0
    audit_score = min(20.0, inputs.audit_count * 6.67)
    maturity_score = min(20.0, inputs.age_days / 365 * 20) if inputs.age_days > 0 else 0.0
    team_score = 20.0 if inputs.team_identified else 5.0
    ecosystem = min(20.0, inputs.ecosystem_score)

    # Bonus for security.txt (Solana standard)
    security_txt_bonus = 2.0 if inputs.on_security_txt else 0.0

    subtotal = source_score + audit_score + maturity_score + team_score + ecosystem
    total = _clamp(subtotal + security_txt_bonus)
    details = {
        "source_verified": source_score,
        "audit_history": audit_score,
        "maturity": maturity_score,
        "team_identification": team_score,
        "ecosystem_presence": ecosystem,
        "security_txt": security_txt_bonus,
    }
    return total, details


def compute_image_score(inputs: ImageInputs) -> tuple[float, dict]:
    base = 100.0
    # Solana-specific vulnerability penalties
    base -= inputs.missing_signer_checks * 20  # Critical — enables unauthorized access
    base -= inputs.pda_seed_collisions * 15  # High — enables account confusion
    base -= inputs.unchecked_arithmetic * 10  # High — enables overflow exploits
    base -= inputs.missing_owner_checks * 12  # High — enables spoofed accounts
    base -= inputs.unsafe_cpi_calls * 15  # High — enables CPI exploitation
    base -= inputs.unvalidated_accounts * 8  # Medium — enables account substitution

    patch_bonus = 0.0
    if inputs.avg_patch_time_days is not None:
        patch_bonus = max(0.0, 10 - inputs.avg_patch_time_days)

    total = _clamp(base + patch_bonus + inputs.trend)
    details = {
        "base_from_vulns": base,
        "patch_cadence_bonus": patch_bonus,
        "trend_adjustment": inputs.trend,
        "missing_signer_checks": inputs.missing_signer_checks,
        "pda_seed_collisions": inputs.pda_seed_collisions,
        "unchecked_arithmetic": inputs.unchecked_arithmetic,
        "missing_owner_checks": inputs.missing_owner_checks,
        "unsafe_cpi_calls": inputs.unsafe_cpi_calls,
        "unvalidated_accounts": inputs.unvalidated_accounts,
    }
    return total, details


def compute_likeness_score(inputs: LikenessInputs) -> tuple[float, dict]:
    score = 100.0
    severity_penalty = {"critical": 20, "high": 15, "medium": 8, "low": 3, "info": 0}

    static_deductions = 0.0
    for finding in inputs.static_analysis_findings:
        sev = finding.get("severity", "info")
        static_deductions += severity_penalty.get(sev, 0)

    pattern_deductions = 0.0
    for match in inputs.exploit_pattern_matches:
        confidence = match.get("confidence", 0.0)
        if confidence > 0.8:
            pattern_deductions += 20
        elif confidence > 0.6:
            pattern_deductions += 10
        elif confidence > 0.4:
            pattern_deductions += 5

    # Rug pull similarity penalty (0-30 points)
    rug_deduction = inputs.rug_pattern_similarity * 30

    total = _clamp(score - static_deductions - pattern_deductions - rug_deduction)
    details = {
        "static_analysis_deductions": static_deductions,
        "exploit_pattern_deductions": pattern_deductions,
        "rug_similarity_deduction": round(rug_deduction, 2),
        "static_finding_count": len(inputs.static_analysis_findings),
        "exploit_match_count": len(inputs.exploit_pattern_matches),
        "rug_similarity": inputs.rug_pattern_similarity,
    }
    return total, details


def compute_essence_score(inputs: EssenceInputs) -> tuple[float, dict]:
    coverage = min(25.0, inputs.test_coverage_pct * 0.25)
    complexity_score = max(0.0, 25 - (inputs.avg_instruction_complexity - 5) * 2.5)
    complexity_score = min(25.0, complexity_score)

    # Upgrade authority risk (Solana-specific)
    upgrade_score = 25.0
    if inputs.upgrade_authority_active:
        upgrade_score -= 10  # Upgradeable = risk
        if not inputs.upgrade_authority_is_multisig:
            upgrade_score -= 5  # Single signer upgrade = higher risk
        if not inputs.has_timelock:
            upgrade_score -= 5  # No timelock = instant rug potential

    dep_score = max(0.0, 25 - inputs.cpi_call_count * 2)

    total = _clamp(coverage + complexity_score + upgrade_score + dep_score)
    details = {
        "test_coverage": coverage,
        "complexity": complexity_score,
        "upgrade_risk": upgrade_score,
        "dependency_risk": dep_score,
        "upgrade_authority_active": inputs.upgrade_authority_active,
        "upgrade_authority_is_multisig": inputs.upgrade_authority_is_multisig,
    }
    return total, details


def compute_nile_score(
    name_inputs: NameInputs,
    image_inputs: ImageInputs,
    likeness_inputs: LikenessInputs,
    essence_inputs: EssenceInputs,
    weights: dict[str, float] | None = None,
) -> NileScoreResult:
    w = weights or {"name": 0.25, "image": 0.25, "likeness": 0.25, "essence": 0.25}

    name_score, name_details = compute_name_score(name_inputs)
    image_score, image_details = compute_image_score(image_inputs)
    likeness_score, likeness_details = compute_likeness_score(likeness_inputs)
    essence_score, essence_details = compute_essence_score(essence_inputs)

    total = (
        name_score * w["name"]
        + image_score * w["image"]
        + likeness_score * w["likeness"]
        + essence_score * w["essence"]
    )
    total = round(total, 2)

    grade = "F"
    for threshold, g in GRADE_MAP:
        if total >= threshold:
            grade = g
            break

    return NileScoreResult(
        total_score=total,
        name_score=round(name_score, 2),
        image_score=round(image_score, 2),
        likeness_score=round(likeness_score, 2),
        essence_score=round(essence_score, 2),
        grade=grade,
        details={
            "name": name_details,
            "image": image_details,
            "likeness": likeness_details,
            "essence": essence_details,
        },
    )
