"""Smoke test to verify the test DB fixtures work correctly."""

from nile.models.contract import Contract


async def test_db_session_creates_tables(db_session):
    """Verify that the in-memory SQLite DB has all tables."""
    contract = Contract(
        name="Test Program",
        address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        chain="solana",
        is_verified=True,
    )
    db_session.add(contract)
    await db_session.flush()
    assert contract.id is not None


async def test_db_session_isolation(db_session):
    """Verify that previous test's data is not visible (rollback isolation)."""
    from sqlalchemy import select

    result = await db_session.execute(select(Contract))
    contracts = result.scalars().all()
    assert len(contracts) == 0, "Previous test data should have been rolled back"


async def test_client_health_endpoint(client):
    """Verify the httpx client can hit the FastAPI app."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
