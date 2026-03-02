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
    """Full scan result for a Solana program or token."""

    address: str
    analysis_type: str  # "program" or "token"
    total_score: float
    grade: str
    scores: SolanaScanScoreBreakdown
    details: dict
    exploit_matches: list[ExploitMatch] = []
    program_info: dict | None = None
    token_info: dict | None = None
    ecosystem: dict | None = None
    idl_analysis: dict | None = None
    # pump.fun-specific analysis (token scans only)
    holder_analysis: HolderAnalysis | None = None
    liquidity_analysis: LiquidityAnalysis | None = None
    creator_analysis: CreatorAnalysis | None = None
    pumpfun_risk_flags: list[str] = []
