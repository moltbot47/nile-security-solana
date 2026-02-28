"""Tests for KPI dashboard API endpoints."""

import pytest

from nile.models.contract import Contract
from nile.models.nile_score import NileScore
from nile.models.scan_job import ScanJob


@pytest.mark.asyncio
class TestAttackerKPIs:
    async def test_empty_returns_zero_rate(self, client):
        resp = await client.get("/api/v1/kpis/attacker")
        assert resp.status_code == 200
        data = resp.json()
        assert data["exploit_success_rate"] == 0.0

    async def test_with_exploit_jobs(self, client, db_session):
        contract = Contract(name="Test", chain="solana")
        db_session.add(contract)
        await db_session.flush()

        for status in ("succeeded", "failed", "succeeded"):
            db_session.add(
                ScanJob(
                    contract_id=contract.id,
                    mode="exploit",
                    agent="test",
                    status=status,
                )
            )
        await db_session.flush()

        resp = await client.get("/api/v1/kpis/attacker")
        assert resp.status_code == 200
        data = resp.json()
        assert data["exploit_success_rate"] > 0


@pytest.mark.asyncio
class TestDefenderKPIs:
    async def test_empty_returns_zero_rate(self, client):
        resp = await client.get("/api/v1/kpis/defender")
        assert resp.status_code == 200
        data = resp.json()
        assert data["detection_recall"] == 0.0
        assert data["patch_success_rate"] == 0.0


@pytest.mark.asyncio
class TestAssetHealth:
    async def test_empty_returns_no_items(self, client):
        resp = await client.get("/api/v1/kpis/asset-health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_contracts"] == 0
        assert data["items"] == []

    async def test_with_contracts_and_scores(self, client, db_session):
        contract = Contract(name="Scored Program", chain="solana")
        db_session.add(contract)
        await db_session.flush()

        db_session.add(
            NileScore(
                contract_id=contract.id,
                total_score=85.0,
                name_score=90.0,
                image_score=80.0,
                likeness_score=85.0,
                essence_score=82.0,
                trigger_type="scan",
            )
        )
        await db_session.flush()

        resp = await client.get("/api/v1/kpis/asset-health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_contracts"] == 1
        assert data["items"][0]["grade"] == "A"


@pytest.mark.asyncio
class TestKPITrends:
    async def test_empty_trends(self, client):
        resp = await client.get("/api/v1/kpis/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []
