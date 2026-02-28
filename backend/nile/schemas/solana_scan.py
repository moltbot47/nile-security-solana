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
