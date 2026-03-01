"""Tests for KPI asset-health grade boundaries — A+, B, C, D, F."""

import pytest

from nile.models.contract import Contract
from nile.models.nile_score import NileScore


@pytest.mark.asyncio
class TestAssetHealthGrades:
    async def test_grade_a_plus(self, client, db_session):
        contract = Contract(name="A+ Program", chain="solana")
        db_session.add(contract)
        await db_session.flush()
        db_session.add(
            NileScore(
                contract_id=contract.id,
                total_score=95.0,
                name_score=95.0,
                image_score=95.0,
                likeness_score=95.0,
                essence_score=95.0,
                trigger_type="scan",
            )
        )
        await db_session.flush()

        resp = await client.get("/api/v1/kpis/asset-health")
        data = resp.json()
        assert data["items"][0]["grade"] == "A+"

    async def test_grade_b(self, client, db_session):
        contract = Contract(name="B Program", chain="solana")
        db_session.add(contract)
        await db_session.flush()
        db_session.add(
            NileScore(
                contract_id=contract.id,
                total_score=75.0,
                name_score=75.0,
                image_score=75.0,
                likeness_score=75.0,
                essence_score=75.0,
                trigger_type="scan",
            )
        )
        await db_session.flush()

        resp = await client.get("/api/v1/kpis/asset-health")
        data = resp.json()
        grades = [i["grade"] for i in data["items"]]
        assert "B" in grades

    async def test_grade_c(self, client, db_session):
        contract = Contract(name="C Program", chain="solana")
        db_session.add(contract)
        await db_session.flush()
        db_session.add(
            NileScore(
                contract_id=contract.id,
                total_score=65.0,
                name_score=65.0,
                image_score=65.0,
                likeness_score=65.0,
                essence_score=65.0,
                trigger_type="scan",
            )
        )
        await db_session.flush()

        resp = await client.get("/api/v1/kpis/asset-health")
        data = resp.json()
        grades = [i["grade"] for i in data["items"]]
        assert "C" in grades

    async def test_grade_d(self, client, db_session):
        contract = Contract(name="D Program", chain="solana")
        db_session.add(contract)
        await db_session.flush()
        db_session.add(
            NileScore(
                contract_id=contract.id,
                total_score=55.0,
                name_score=55.0,
                image_score=55.0,
                likeness_score=55.0,
                essence_score=55.0,
                trigger_type="scan",
            )
        )
        await db_session.flush()

        resp = await client.get("/api/v1/kpis/asset-health")
        data = resp.json()
        grades = [i["grade"] for i in data["items"]]
        assert "D" in grades

    async def test_grade_f(self, client, db_session):
        contract = Contract(name="F Program", chain="solana")
        db_session.add(contract)
        await db_session.flush()
        db_session.add(
            NileScore(
                contract_id=contract.id,
                total_score=30.0,
                name_score=30.0,
                image_score=30.0,
                likeness_score=30.0,
                essence_score=30.0,
                trigger_type="scan",
            )
        )
        await db_session.flush()

        resp = await client.get("/api/v1/kpis/asset-health")
        data = resp.json()
        grades = [i["grade"] for i in data["items"]]
        assert "F" in grades
