"""Extended tests for scan endpoints — scan_solana_program and list filter."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from nile.models.contract import Contract
from nile.models.scan_job import ScanJob


@pytest.mark.asyncio
class TestScanSolanaProgram:
    @patch("nile.routers.v1.scans.program_analyzer")
    @patch("nile.routers.v1.scans.validate_solana_address", return_value=True)
    async def test_successful_scan(self, mock_validate, mock_analyzer, client):
        mock_score = SimpleNamespace(
            total_score=82.0,
            grade="A",
            name_score=85.0,
            image_score=80.0,
            likeness_score=82.0,
            essence_score=78.0,
            details={"name": {}, "image": {}, "likeness": {}, "essence": {}},
        )
        mock_analyzer.analyze = AsyncMock(
            return_value={
                "score": mock_score,
                "analysis_type": "program",
                "program_info": {"address": "Test", "executable": True},
                "idl_analysis": {"has_idl": False},
                "ecosystem": {},
                "exploit_matches": [],
            }
        )

        resp = await client.post(
            "/api/v1/scans/solana",
            json={"program_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] == 82.0
        assert data["grade"] == "A"
        assert data["analysis_type"] == "program"

    @patch("nile.routers.v1.scans.validate_solana_address", return_value=False)
    async def test_invalid_address(self, mock_validate, client):
        resp = await client.post(
            "/api/v1/scans/solana",
            json={"program_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
        )
        assert resp.status_code == 400

    @patch("nile.routers.v1.scans.program_analyzer")
    @patch("nile.routers.v1.scans.validate_solana_address", return_value=True)
    async def test_analysis_error(self, mock_validate, mock_analyzer, client):
        mock_analyzer.analyze = AsyncMock(
            return_value={"error": "Cannot reach RPC node"}
        )

        resp = await client.post(
            "/api/v1/scans/solana",
            json={"program_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
        )
        assert resp.status_code == 422

    @patch("nile.routers.v1.scans.program_analyzer")
    @patch("nile.routers.v1.scans.validate_solana_address", return_value=True)
    async def test_scan_with_exploits(self, mock_validate, mock_analyzer, client):
        mock_score = SimpleNamespace(
            total_score=45.0,
            grade="F",
            name_score=30.0,
            image_score=40.0,
            likeness_score=50.0,
            essence_score=55.0,
            details={},
        )
        mock_analyzer.analyze = AsyncMock(
            return_value={
                "score": mock_score,
                "analysis_type": "token",
                "token_info": {"mint": "Test"},
                "ecosystem": {},
                "exploit_matches": [
                    {
                        "pattern_id": "SOL-001",
                        "name": "Reentrancy",
                        "category": "logic",
                        "severity": "critical",
                        "confidence": 0.85,
                    }
                ],
            }
        )

        resp = await client.post(
            "/api/v1/scans/solana",
            json={"program_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["exploit_matches"]) == 1
        assert data["exploit_matches"][0]["severity"] == "critical"


@pytest.mark.asyncio
class TestListScansFilter:
    async def test_filter_by_status(self, client, db_session):
        contract = Contract(name="Filter Test", chain="solana")
        db_session.add(contract)
        await db_session.flush()

        for status in ("queued", "running", "succeeded"):
            db_session.add(
                ScanJob(
                    contract_id=contract.id,
                    mode="detect",
                    agent="test",
                    status=status,
                )
            )
        await db_session.flush()

        resp = await client.get("/api/v1/scans?status=queued")
        assert resp.status_code == 200
        data = resp.json()
        assert all(s["status"] == "queued" for s in data)
        assert len(data) == 1
