"""Test configuration and shared fixtures for NILE Security tests.

Provides:
- Async SQLite in-memory DB with per-test isolation (savepoint + rollback)
- httpx AsyncClient wired to the FastAPI app with DB override
- Scorer input fixtures for unit tests
- IDL and token info fixtures
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from nile.app import create_app
from nile.core.database import get_db
from nile.models.base import Base
from nile.services.nile_scorer import (
    EssenceInputs,
    ImageInputs,
    LikenessInputs,
    NameInputs,
)

# ---------------------------------------------------------------------------
# Database fixtures — async SQLite with per-test savepoint isolation
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def engine():
    """Create a single async engine for the entire test session."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test async session with savepoint rollback for isolation.

    Each test gets a nested transaction (SAVEPOINT) that is rolled back
    after the test completes, so no test data leaks between tests.
    """
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = session_factory(bind=conn)

        # Use nested transactions so session.commit() creates SAVEPOINTs
        nested = await conn.begin_nested()

        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(sess, transaction):
            nonlocal nested
            if transaction.nested and not transaction._parent.nested:
                nested = conn.sync_connection.begin_nested()

        yield session

        await session.close()
        await trans.rollback()


# ---------------------------------------------------------------------------
# HTTP client fixture — wired to FastAPI with DB override
# ---------------------------------------------------------------------------


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient with the test DB session injected."""
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_contract_data():
    """Dict suitable for creating a Contract via API or ORM."""
    return {
        "name": "Test Token Program",
        "address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "chain": "solana",
        "is_verified": True,
    }


@pytest.fixture
def sample_agent_data():
    """Dict suitable for creating an Agent via ORM."""
    return {
        "name": f"test-agent-{uuid.uuid4().hex[:8]}",
        "owner_id": "test-owner",
        "capabilities": ["detect"],
        "status": "active",
        "api_key_hash": "fakehash",
    }


# ---------------------------------------------------------------------------
# Scorer fixtures (unit tests, no DB needed)
# ---------------------------------------------------------------------------


@pytest.fixture
def safe_name_inputs():
    """Name inputs for a well-known verified program."""
    return NameInputs(
        is_verified=True,
        audit_count=3,
        age_days=730,
        team_identified=True,
        ecosystem_score=18.0,
        on_security_txt=True,
    )


@pytest.fixture
def risky_name_inputs():
    """Name inputs for an anonymous unverified program."""
    return NameInputs(
        is_verified=False,
        audit_count=0,
        age_days=2,
        team_identified=False,
        ecosystem_score=0.0,
    )


@pytest.fixture
def clean_image_inputs():
    """Image inputs for a program with no vulnerabilities."""
    return ImageInputs(
        missing_signer_checks=0,
        pda_seed_collisions=0,
        unchecked_arithmetic=0,
        missing_owner_checks=0,
        unsafe_cpi_calls=0,
        unvalidated_accounts=0,
        trend=5.0,
    )


@pytest.fixture
def vuln_image_inputs():
    """Image inputs for a program with multiple vulnerabilities."""
    return ImageInputs(
        missing_signer_checks=2,
        pda_seed_collisions=1,
        unsafe_cpi_calls=2,
        unvalidated_accounts=3,
    )


@pytest.fixture
def safe_likeness_inputs():
    """Likeness inputs with no exploit matches."""
    return LikenessInputs()


@pytest.fixture
def risky_likeness_inputs():
    """Likeness inputs with high-confidence exploit matches."""
    return LikenessInputs(
        exploit_pattern_matches=[
            {"confidence": 0.9},
            {"confidence": 0.75},
        ],
        rug_pattern_similarity=0.6,
        static_analysis_findings=[
            {"severity": "critical"},
            {"severity": "high"},
        ],
    )


@pytest.fixture
def safe_essence_inputs():
    """Essence inputs for a well-tested, non-upgradeable program."""
    return EssenceInputs(
        test_coverage_pct=90.0,
        avg_instruction_complexity=3.0,
        upgrade_authority_active=False,
        has_timelock=True,
        cpi_call_count=1,
    )


@pytest.fixture
def risky_essence_inputs():
    """Essence inputs for an upgradeable, untested, complex program."""
    return EssenceInputs(
        test_coverage_pct=5.0,
        avg_instruction_complexity=18.0,
        upgrade_authority_active=True,
        upgrade_authority_is_multisig=False,
        has_timelock=False,
        cpi_call_count=12,
    )


# ---------------------------------------------------------------------------
# IDL fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_idl():
    """A basic Anchor IDL for testing."""
    return {
        "instructions": [
            {
                "name": "initialize",
                "accounts": [
                    {"name": "authority", "isMut": True, "isSigner": True},
                    {
                        "name": "state",
                        "isMut": True,
                        "isSigner": False,
                        "type": {"kind": "account"},
                    },
                    {
                        "name": "systemProgram",
                        "isMut": False,
                        "isSigner": False,
                        "type": {"kind": "program"},
                    },
                ],
                "args": [],
            },
            {
                "name": "transfer",
                "accounts": [
                    {"name": "from", "isMut": True, "isSigner": False},
                    {"name": "to", "isMut": True, "isSigner": False},
                    {"name": "authority", "isMut": False, "isSigner": True},
                ],
                "args": [{"name": "amount", "type": "u64"}],
            },
        ],
    }


@pytest.fixture
def unsafe_idl():
    """An IDL with multiple security issues."""
    return {
        "instructions": [
            {
                "name": "withdraw",
                "accounts": [
                    {"name": "vault", "isMut": True, "isSigner": False},
                    {"name": "destination", "isMut": True, "isSigner": False},
                ],
                "args": [{"name": "amount", "type": "u64"}],
            },
            {
                "name": "admin_action",
                "accounts": [
                    {"name": "config", "isMut": True, "isSigner": False},
                ],
                "args": [],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Token info fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def safe_token_info():
    """Token info for a safe, authority-revoked token."""
    return {
        "mint_authority_active": False,
        "freeze_authority_active": False,
        "supply": 1_000_000_000_000,
        "decimals": 9,
    }


@pytest.fixture
def risky_token_info():
    """Token info for a rug-risk token."""
    return {
        "mint_authority_active": True,
        "freeze_authority_active": True,
        "supply": 100,
        "decimals": 6,
    }
