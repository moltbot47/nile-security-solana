"""Extended tests for benchmark endpoints — create and get by ID."""

import pytest

from nile.models.benchmark_run import BenchmarkRun


@pytest.mark.asyncio
class TestCreateBenchmark:
    async def test_create(self, client, db_session):
        resp = await client.post(
            "/api/v1/benchmarks/run",
            json={
                "mode": "detect",
                "agent": "claude-opus-4-6",
                "split": "all",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["mode"] == "detect"
        assert data["agent"] == "claude-opus-4-6"
        assert data["status"] == "running"

    async def test_create_with_baseline(self, client, db_session):
        resp = await client.post(
            "/api/v1/benchmarks/run",
            json={
                "mode": "exploit",
                "agent": "test-agent",
                "baseline_agent": "gpt-5",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["baseline_agent"] == "gpt-5"


@pytest.mark.asyncio
class TestGetBenchmarkById:
    async def test_found(self, client, db_session):
        run = BenchmarkRun(
            split="all",
            mode="detect",
            agent="test-agent",
            status="succeeded",
        )
        db_session.add(run)
        await db_session.flush()

        resp = await client.get(f"/api/v1/benchmarks/{run.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "detect"
        assert data["status"] == "succeeded"
