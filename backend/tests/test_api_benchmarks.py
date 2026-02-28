"""Tests for benchmark API endpoints."""

import uuid

import pytest


@pytest.mark.asyncio
class TestBenchmarks:
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/benchmarks")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_baselines(self, client):
        resp = await client.get("/api/v1/benchmarks/baselines")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["agent"] == "gpt-5.3-codex"

    async def test_get_not_found(self, client):
        resp = await client.get(f"/api/v1/benchmarks/{uuid.uuid4()}")
        assert resp.status_code == 404
