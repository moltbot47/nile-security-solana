"""Scan worker — processes queued scan jobs using Solana Program Analyzer."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import async_session
from nile.core.event_bus import publish_event
from nile.models.contract import Contract
from nile.models.nile_score import NileScore
from nile.models.scan_job import ScanJob
from nile.services.onchain_writer import submit_score_onchain
from nile.services.program_analyzer import program_analyzer

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5


async def process_scan_job(db: AsyncSession, job: ScanJob) -> None:
    """Process a single scan job — run Solana program analysis and persist results."""
    job.status = "running"
    job.started_at = datetime.now(UTC)
    await db.flush()

    try:
        # Load the contract
        result = await db.execute(select(Contract).where(Contract.id == job.contract_id))
        contract = result.scalar_one_or_none()
        if not contract:
            raise ValueError(f"Contract {job.contract_id} not found")

        if not contract.address:
            raise ValueError(f"Contract {job.contract_id} has no address")

        # Run the Solana Program Analyzer
        analysis = await program_analyzer.analyze(contract.address)

        if "error" in analysis:
            raise ValueError(f"Analysis failed: {analysis['error']}")

        score_result = analysis["score"]

        # Update contract metadata with analysis results
        contract.metadata_ = {
            **(contract.metadata_ or {}),
            "analysis_type": analysis.get("analysis_type"),
            "idl_analysis": analysis.get("idl_analysis"),
            "ecosystem": analysis.get("ecosystem"),
            "exploit_matches": [
                {
                    "pattern_id": m["pattern_id"],
                    "name": m["name"],
                    "severity": m["severity"],
                    "confidence": m["confidence"],
                }
                for m in analysis.get("exploit_matches", [])
            ],
            "last_scanned_at": datetime.now(UTC).isoformat(),
        }

        # Persist score
        nile_score = NileScore(
            contract_id=contract.id,
            total_score=score_result.total_score,
            name_score=score_result.name_score,
            image_score=score_result.image_score,
            likeness_score=score_result.likeness_score,
            essence_score=score_result.essence_score,
            score_details=score_result.details,
            trigger_type="scan",
            trigger_id=job.id,
        )
        db.add(nile_score)

        # Update job
        job.status = "succeeded"
        job.result = {
            "nile_score": score_result.total_score,
            "grade": score_result.grade,
            "analysis_type": analysis.get("analysis_type"),
            "sub_scores": {
                "name": score_result.name_score,
                "image": score_result.image_score,
                "likeness": score_result.likeness_score,
                "essence": score_result.essence_score,
            },
            "exploit_match_count": len(analysis.get("exploit_matches", [])),
        }
        job.finished_at = datetime.now(UTC)
        await db.flush()

        # Optionally persist score on-chain (feature-flagged)
        tx_sig = await submit_score_onchain(
            program_address=contract.address,
            name_score=int(score_result.name_score),
            image_score=int(score_result.image_score),
            likeness_score=int(score_result.likeness_score),
            essence_score=int(score_result.essence_score),
            details_uri=f"nile://{job.id}",
        )
        if tx_sig:
            job.result["onchain_tx"] = tx_sig

        await publish_event(
            event_type="scan.completed",
            target_id=str(contract.id),
            metadata={
                "scan_job_id": str(job.id),
                "nile_score": score_result.total_score,
                "grade": score_result.grade,
                "onchain_tx": tx_sig,
            },
            db=db,
        )

        logger.info(
            "Scan job %s completed: score=%.2f grade=%s (%s)",
            job.id,
            score_result.total_score,
            score_result.grade,
            analysis.get("analysis_type"),
        )

    except Exception as e:
        job.status = "failed"
        job.result_error = str(e)
        job.finished_at = datetime.now(UTC)
        await db.flush()
        logger.exception("Scan job %s failed: %s", job.id, e)


async def poll_and_process() -> None:
    """Poll for queued scan jobs and process them."""
    async with async_session() as db:
        result = await db.execute(
            select(ScanJob).where(ScanJob.status == "queued").order_by(ScanJob.created_at).limit(5)
        )
        jobs = list(result.scalars().all())

        for job in jobs:
            await process_scan_job(db, job)

        await db.commit()


async def run_worker() -> None:
    """Main worker loop — polls for jobs continuously."""
    logger.info("NILE scan worker starting...")
    while True:
        try:
            await poll_and_process()
        except Exception:
            logger.exception("Worker poll cycle failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
