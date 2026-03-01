"""Tests for scan job API endpoints."""

import uuid

import pytest

from nile.models.contract import Contract
from nile.models.scan_job import ScanJob


@pytest.mark.asyncio
class TestListScans:
    async def test_empty_list(self, client):
        resp = await client.get("/api/v1/scans")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_with_scans(self, client, db_session):
        contract = Contract(name="Test", chain="solana")
        db_session.add(contract)
        await db_session.flush()

        db_session.add(
            ScanJob(
                contract_id=contract.id,
                mode="detect",
                agent="test-agent",
                status="queued",
            )
        )
        await db_session.flush()

        resp = await client.get("/api/v1/scans")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
class TestCreateScan:
    async def test_create_scan_unauthenticated(self, client, db_session):
        contract = Contract(name="Test", chain="solana")
        db_session.add(contract)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/scans",
            json={
                "contract_id": str(contract.id),
                "mode": "detect",
                "agent": "test-agent",
            },
        )
        assert resp.status_code == 401

    async def test_create_scan(self, client, auth_headers, db_session):
        contract = Contract(name="Test", chain="solana")
        db_session.add(contract)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/scans",
            json={
                "contract_id": str(contract.id),
                "mode": "detect",
                "agent": "test-agent",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201


@pytest.mark.asyncio
class TestGetScan:
    async def test_not_found(self, client):
        resp = await client.get(f"/api/v1/scans/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_get_existing(self, client, db_session):
        contract = Contract(name="Test", chain="solana")
        db_session.add(contract)
        await db_session.flush()

        job = ScanJob(
            contract_id=contract.id,
            mode="detect",
            agent="test-agent",
            status="queued",
        )
        db_session.add(job)
        await db_session.flush()

        resp = await client.get(f"/api/v1/scans/{job.id}")
        assert resp.status_code == 200
