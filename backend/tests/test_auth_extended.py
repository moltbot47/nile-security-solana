"""Extended tests for auth module — API key, optional agent, token helpers."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import jwt as pyjwt
import pytest

from nile.core.auth import (
    create_agent_token,
    decode_agent_token,
    generate_api_key,
    get_optional_agent,
    hash_api_key,
)
from nile.models.agent import Agent


class TestHashApiKey:
    def test_consistent(self):
        assert hash_api_key("test") == hash_api_key("test")

    def test_different_keys(self):
        assert hash_api_key("a") != hash_api_key("b")


class TestGenerateApiKey:
    def test_starts_with_nile(self):
        key = generate_api_key()
        assert key.startswith("nile_")

    def test_unique(self):
        assert generate_api_key() != generate_api_key()


class TestCreateDecodeToken:
    def test_roundtrip(self):
        agent_id = str(uuid.uuid4())
        token = create_agent_token(agent_id)
        payload = decode_agent_token(token)
        assert payload["sub"] == agent_id

    def test_expired_token(self):
        import time

        from nile.core.auth import JWT_ALGORITHM, JWT_SECRET

        payload = {
            "sub": str(uuid.uuid4()),
            "exp": int(time.time()) - 3600,
            "iat": int(time.time()) - 7200,
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_agent_token(token)


@pytest.mark.asyncio
class TestGetOptionalAgent:
    async def test_no_credentials_returns_none(self):
        mock_db = AsyncMock()
        result = await get_optional_agent(db=mock_db, api_key=None, bearer=None)
        assert result is None

    async def test_invalid_bearer_returns_none(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        mock_bearer = MagicMock()
        mock_bearer.credentials = "invalid-token"
        result = await get_optional_agent(
            db=mock_db, api_key=None, bearer=mock_bearer
        )
        assert result is None

    async def test_valid_api_key(self, db_session):
        agent = Agent(
            name=f"auth-test-{uuid.uuid4().hex[:8]}",
            owner_id="test",
            capabilities=[],
            status="active",
            api_key_hash=hash_api_key("test-key-123"),
        )
        db_session.add(agent)
        await db_session.flush()

        result = await get_optional_agent(
            db=db_session, api_key="test-key-123", bearer=None
        )
        assert result is not None
        assert result.name == agent.name
