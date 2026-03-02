"""Pydantic schemas for Solana program scanning."""

from pydantic import BaseModel, Field


class SolanaScanRequest(BaseModel):
    """Request to scan a Solana program or token address."""

    program_address: str = Field(
        ...,
        min_length=32,
        max_length=48,
        description="Solana program or token mint address (base58)",
    )


class SolanaScanScoreBreakdown(BaseModel):
    name: float
    image: float
    likeness: float
    essence: float


class ExploitMatch(BaseModel):
    pattern_id: str
    name: str
    category: str
    severity: str
    confidence: float
    cwe: str | None = None
    indicators_matched: list[str] = []


class TopHolder(BaseModel):
    address: str
    amount: int
    pct: float


class HolderAnalysis(BaseModel):
    """Token holder concentration analysis."""

    top_holders: list[TopHolder] = []
    top5_concentration_pct: float = 0.0
    top10_concentration_pct: float = 0.0
    whale_count: int = 0


class LiquidityAnalysis(BaseModel):
    """DEX liquidity pool detection."""

    lp_detected: bool = False
    has_raydium_lp: bool = False
    has_orca_lp: bool = False


class CreatorAnalysis(BaseModel):
    """Token creator wallet analysis."""

    creator_address: str | None = None
    tokens_created: int = 0
    serial_deployer: bool = False


class SolanaScanResponse(BaseModel):
    """Full scan result for a Solana program or token.

    The hero response — everything a wallet needs to show a pre-transaction warning.
    """

    address: str = Field(description="Scanned Solana address (base58)")
    analysis_type: str = Field(
        description="'program' for executable programs, 'token' for SPL mints"
    )
    total_score: float = Field(description="Composite security score (0-100, higher is safer)")
    grade: str = Field(description="Letter grade: A (90+), B (80+), C (70+), D (50+), F (<50)")
    scores: SolanaScanScoreBreakdown = Field(description="Per-dimension breakdown (N/I/L/E)")
    details: dict = Field(description="Human-readable scoring explanations")
    exploit_matches: list[ExploitMatch] = Field(
        default=[], description="Matched exploit patterns with confidence scores"
    )
    program_info: dict | None = Field(default=None, description="On-chain program account data")
    token_info: dict | None = Field(default=None, description="SPL token mint data")
    ecosystem: dict | None = Field(default=None, description="Ecosystem presence (Jupiter, etc.)")
    idl_analysis: dict | None = Field(
        default=None, description="IDL security analysis (programs only)"
    )
    holder_analysis: HolderAnalysis | None = Field(
        default=None, description="Token holder concentration (tokens only)"
    )
    liquidity_analysis: LiquidityAnalysis | None = Field(
        default=None, description="DEX liquidity pool detection (tokens only)"
    )
    creator_analysis: CreatorAnalysis | None = Field(
        default=None, description="Creator wallet behavior analysis (tokens only)"
    )
    pumpfun_risk_flags: list[str] = Field(
        default=[],
        description=(
            "Risk flags: supply_concentration_extreme, "
            "serial_deployer, honeypot_token, etc."
        ),
    )
