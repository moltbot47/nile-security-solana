"""Scan job endpoints — includes Solana-native instant scan."""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import get_db
from nile.core.exceptions import AnalysisError, InvalidAddressError, NotFoundError
from nile.core.rate_limit import RateLimiter
from nile.models.scan_job import ScanJob
from nile.schemas.scan import ScanCreate, ScanResponse
from nile.schemas.solana_scan import (
    ExploitMatch,
    SolanaScanRequest,
    SolanaScanResponse,
    SolanaScanScoreBreakdown,
)
from nile.services.chain_service import validate_solana_address
from nile.services.program_analyzer import program_analyzer

router = APIRouter()

# 10 scans per minute per IP — prevents abuse of the heavy analysis endpoint
scan_limiter = RateLimiter(max_requests=10, window_seconds=60)


@router.post("/solana", response_model=SolanaScanResponse)
async def scan_solana_program(req: SolanaScanRequest, request: Request):
    """Instantly scan a Solana program or token address and return NILE score.

    This is the hero endpoint — paste an address, get a security score.
    No database record required; runs analysis in real-time.
    """
    scan_limiter.check(request)

    if not validate_solana_address(req.program_address):
        raise InvalidAddressError()

    analysis = await program_analyzer.analyze(req.program_address)

    if "error" in analysis:
        raise AnalysisError(analysis["error"])

    score = analysis["score"]

    return SolanaScanResponse(
        address=req.program_address,
        analysis_type=analysis["analysis_type"],
        total_score=score.total_score,
        grade=score.grade,
        scores=SolanaScanScoreBreakdown(
            name=score.name_score,
            image=score.image_score,
            likeness=score.likeness_score,
            essence=score.essence_score,
        ),
        details=score.details,
        exploit_matches=[
            ExploitMatch(**m) for m in analysis.get("exploit_matches", [])
        ],
        program_info=analysis.get("program_info"),
        token_info=analysis.get("token_info"),
        ecosystem=analysis.get("ecosystem"),
        idl_analysis=analysis.get("idl_analysis"),
    )


@router.get("", response_model=list[ScanResponse])
async def list_scans(
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ScanJob).order_by(ScanJob.created_at.desc())
    if status:
        query = query.where(ScanJob.status == status)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("", response_model=ScanResponse, status_code=201)
async def create_scan(data: ScanCreate, db: AsyncSession = Depends(get_db)):
    scan = ScanJob(
        contract_id=data.contract_id,
        mode=data.mode,
        agent=data.agent,
        config=data.config,
        hint_level=data.hint_level,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScanJob).where(ScanJob.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise NotFoundError("Scan not found")
    return scan
