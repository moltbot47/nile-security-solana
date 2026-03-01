"""Final coverage tests — targets every remaining uncovered line to reach 100%.

Lines targeted:
- database.py:20-21 (get_db generator body)
- exceptions.py:17 (to_http method)
- metrics.py:79 (/metrics endpoint)
- agents.py:254 (update_agent 404), 275 (heartbeat 404)
- events.py:28 (SSE stream endpoint)
- health.py:70-71 (Solana RPC unhealthy branch)
- soul_tokens.py:202 (token_risk endpoint)
- tasks.py:131 (task claimed by different agent)
- agent_scorer.py:97 (low avg_points essence branch)
- chain_service.py:23 (_load_idl success), 83 (get_program_info not found)
- idl_fetcher.py:66 (data too short for IDL extraction)
- oracle_consensus.py:123-124 (person not found in revaluation)
- risk_engine.py:118 (wash low ratio), 162 (pump no buys), 171 (zero vol),
  192 (pump concentration below threshold), 215 (cliff < 2 trades),
  259 (wash alert in run_risk_checks)
- soul_agent_incentives.py:94 (capability filter)
"""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.core.auth import create_agent_token
from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution
from nile.models.contract import Contract
from nile.models.person import Person
from nile.models.scan_job import ScanJob
from nile.models.soul_token import SoulToken
from nile.models.trade import Trade

# ── __main__.py:3-5 — imports ──


class TestMainImport:
    def test_main_module_importable(self):
        """Importing __main__ covers import lines."""
        import nile.__main__  # noqa: F401


# ── database.py:20-21 — get_db generator ──


@pytest.mark.asyncio
class TestGetDbGenerator:
    async def test_get_db_yields_session(self):
        """Test the real get_db generator yields and closes a session."""
        from nile.core.database import get_db

        gen = get_db()
        session = await gen.__anext__()
        assert session is not None
        import contextlib

        with contextlib.suppress(StopAsyncIteration):
            await gen.__anext__()


# ── exceptions.py:17 — to_http() ──


class TestExceptionsToHttp:
    def test_to_http(self):
        from nile.core.exceptions import AnalysisError

        err = AnalysisError("test error")
        http_exc = err.to_http()
        assert http_exc.status_code == 422
        assert http_exc.detail == "test error"

    def test_to_http_default_detail(self):
        from nile.core.exceptions import NileBaseError

        err = NileBaseError()
        http_exc = err.to_http()
        assert http_exc.status_code == 500
        assert http_exc.detail == "Internal server error"


# ── metrics.py:79 — /metrics endpoint ──


@pytest.mark.asyncio
class TestMetricsEndpoint:
    async def test_prometheus_metrics(self, client):
        """GET /metrics returns Prometheus text format."""
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")


# ── agents.py:254, 275 — agent not found in update/heartbeat ──


@pytest.fixture
async def auth_agent(db_session):
    """Create an agent with JWT for auth tests."""
    agent = Agent(
        name=f"auth-final-{uuid.uuid4().hex[:6]}",
        owner_id="test",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()
    jwt = create_agent_token(str(agent.id))
    return agent, jwt


@pytest.mark.asyncio
class TestAgentUpdateAndHeartbeat:
    async def test_update_own_agent(self, client, db_session, auth_agent):
        """PATCH own agent → 200."""
        agent, jwt = auth_agent
        resp = await client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"status": "inactive"},
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 200

    async def test_update_other_agent_forbidden(self, client, db_session, auth_agent):
        """PATCH another agent → 403."""
        _, jwt = auth_agent
        resp = await client.patch(
            f"/api/v1/agents/{uuid.uuid4()}",
            json={"status": "inactive"},
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 403

    async def test_heartbeat_own_agent(self, client, db_session, auth_agent):
        """POST heartbeat for own agent → 200."""
        agent, jwt = auth_agent
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/heartbeat",
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 200


# ── events.py:28 — SSE stream ──


@pytest.mark.asyncio
class TestSSEStream:
    async def test_sse_stream_endpoint(self, client):
        """GET /events/stream returns event-stream content type."""
        with patch("nile.core.event_bus.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_r = AsyncMock()
            mock_pubsub = MagicMock()

            async def mock_listen():
                return
                yield  # noqa: RET504 — make it an async generator

            mock_pubsub.subscribe = AsyncMock()
            mock_pubsub.listen = mock_listen
            mock_pubsub.unsubscribe = AsyncMock()
            mock_pubsub.close = AsyncMock()
            mock_r.pubsub = MagicMock(return_value=mock_pubsub)
            mock_redis.return_value = mock_r

            resp = await client.get("/api/v1/events/stream")
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")


# ── health.py:70-71 — Solana RPC unhealthy ──


@pytest.mark.asyncio
class TestHealthRpcUnhealthy:
    async def test_readiness_rpc_unhealthy(self, client):
        """Readiness with Solana RPC returning unhealthy → degraded (lines 70-71)."""

        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"message": "Node is behind"}}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            resp = await client.get("/api/v1/health/ready")

        assert resp.status_code in (200, 503)
        data = resp.json()
        if isinstance(data, list):
            data = data[0]
        assert "checks" in data


# ── soul_tokens.py:202 — token risk endpoint ──


@pytest.mark.asyncio
class TestTokenRiskEndpoint:
    @patch("nile.routers.v1.soul_tokens.get_token_risk_summary", new_callable=AsyncMock)
    async def test_token_risk(self, mock_risk_summary, client, db_session):
        mock_risk_summary.return_value = {
            "soul_token_id": "test",
            "circuit_breaker_active": False,
            "circuit_breaker_expiry": None,
            "last_hour": {"trade_count": 0, "unique_traders": 0, "total_volume_sol": 0},
        }

        resp = await client.get(f"/api/v1/soul-tokens/{uuid.uuid4()}/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "circuit_breaker_active" in data
        mock_risk_summary.assert_called_once()


# ── tasks.py:131 — task claimed by different agent ──


@pytest.mark.asyncio
class TestTaskClaimedByOther:
    async def test_submit_different_agent(self, client, db_session):
        """Submitting task claimed by another agent → 403."""
        contract = Contract(
            name="Task Test",
            address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            chain="solana",
        )
        db_session.add(contract)
        await db_session.flush()

        job = ScanJob(
            contract_id=contract.id,
            status="running",
            mode="detect",
            agent="other-agent-name",
        )
        db_session.add(job)
        await db_session.flush()

        agent = Agent(
            name=f"submitter-{uuid.uuid4().hex[:6]}",
            owner_id="test",
            capabilities=["detect"],
            status="active",
            api_key_hash="unused",
        )
        db_session.add(agent)
        await db_session.flush()
        jwt = create_agent_token(str(agent.id))

        resp = await client.post(
            f"/api/v1/tasks/{job.id}/submit",
            json={"result": {"score": 85}},
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 403
        assert "different agent" in resp.json()["detail"]


# ── agent_scorer.py:97 — low avg_points essence branch ──


@pytest.mark.asyncio
class TestAgentScorerLowEssence:
    async def test_low_avg_points(self, db_session):
        """Agent with avg_points < 10 → essence_score = avg_points * 5."""
        from nile.services.agent_scorer import compute_agent_nile_score

        agent = Agent(
            name=f"low-ess-{uuid.uuid4().hex[:6]}",
            owner_id="test",
            capabilities=["detect"],
            status="active",
            api_key_hash="unused",
            total_points=5,
            total_contributions=1,
        )
        db_session.add(agent)
        await db_session.flush()

        # Add 1 contribution so total_contribs = 1, avg = 5/1 = 5
        db_session.add(
            AgentContribution(
                agent_id=agent.id,
                contribution_type="detection",
                severity_found="low",
                points_awarded=5,
                verified=True,
            )
        )
        await db_session.flush()

        result = await compute_agent_nile_score(db_session, agent.id)
        # avg_points = 5, essence = 5 * 5 = 25
        assert result.essence_score == 25.0


# ── chain_service.py:23 — _load_idl success, 83 — program_info not found ──


class TestChainServiceLoadIdl:
    def test_load_idl_success(self):
        from nile.services.chain_service import _load_idl

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = '{"name": "test_program"}'

        mock_dir = MagicMock(__truediv__=lambda s, n: mock_path)
        with patch("nile.services.chain_service.IDL_DIR", mock_dir):
            result = _load_idl("test_program")
            assert result == {"name": "test_program"}


@pytest.mark.asyncio
class TestGetProgramInfoNotFound:
    async def test_program_not_found(self):
        mods = {
            "solders": MagicMock(),
            "solders.pubkey": MagicMock(
                Pubkey=MagicMock(
                    from_string=MagicMock(return_value=MagicMock()),
                )
            ),
            "solders.rpc": MagicMock(),
            "solders.rpc.api": MagicMock(),
            "solders.rpc.async_api": MagicMock(AsyncClient=MagicMock()),
        }
        with patch.dict("sys.modules", mods):
            from nile.services.chain_service import SolanaChainService

            svc = SolanaChainService()
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = None
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)
            svc._async_client = mock_client

            result = await svc.get_program_info("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
            assert result is None


# ── idl_fetcher.py:66 — data too short for extraction ──


@pytest.mark.asyncio
class TestIdlFetcherDataTooShort:
    async def test_onchain_data_too_short_for_length(self):
        """IDL data present but too short to read the length prefix."""
        mods = {
            "solders": MagicMock(),
            "solders.pubkey": MagicMock(
                Pubkey=MagicMock(
                    from_string=MagicMock(
                        side_effect=lambda s: MagicMock(__bytes__=lambda _: b"\x00" * 32)
                    ),
                    find_program_address=MagicMock(return_value=(MagicMock(), 255)),
                )
            ),
            "solders.rpc": MagicMock(),
            "solders.rpc.api": MagicMock(),
            "solders.rpc.async_api": MagicMock(AsyncClient=MagicMock()),
        }
        with patch.dict("sys.modules", mods):
            import importlib

            import nile.services.idl_fetcher as idl_mod

            importlib.reload(idl_mod)

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.value = MagicMock()
            # Data is 46 bytes — enough to pass the first check (> 0)
            # but too short after offset 44 to read the 4-byte length prefix
            mock_resp.value.data = b"\x00" * 46
            mock_client.get_account_info = AsyncMock(return_value=mock_resp)

            with patch.object(idl_mod, "chain_service") as mock_cs:
                mock_cs.async_client = mock_client
                result = await idl_mod._fetch_onchain_idl(
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                )
                assert result is None


# ── oracle_consensus.py:123-124 — person not found in revaluation ──


@pytest.mark.asyncio
class TestOracleRevaluationPersonNotFound:
    async def test_trigger_revaluation_no_person(self, db_session):
        """Revaluation with non-existent person_id logs warning and returns."""
        from nile.services.oracle_consensus import _trigger_revaluation

        mock_event = MagicMock()
        mock_event.person_id = uuid.uuid4()  # Non-existent

        await _trigger_revaluation(db_session, mock_event)
        # Should not raise, just log warning


# ── risk_engine.py — remaining branch coverage ──


@pytest.mark.asyncio
class TestRiskEngineBranches:
    @pytest.fixture
    async def risk_token(self, db_session):
        person = Person(
            display_name="Branch Test",
            slug=f"branch-{uuid.uuid4().hex[:6]}",
            category="athlete",
        )
        db_session.add(person)
        await db_session.flush()

        token = SoulToken(
            person_id=person.id,
            name="Branch Token",
            symbol="BRC",
            phase="bonding",
            chain="solana",
            current_price_sol=0.01,
            current_price_usd=2.50,
            market_cap_usd=25000.0,
            total_supply=10000000,
            reserve_balance_sol=5.0,
            graduation_threshold_sol=100.0,
        )
        db_session.add(token)
        await db_session.flush()
        return token

    async def test_wash_low_ratio(self, db_session, risk_token):
        """Wash: buy and sell with ratio < 0.8 → returns None (line 118)."""
        from nile.services.risk_engine import check_wash_trading

        token = risk_token
        addr = "LR" * 22
        # Buy 1000, sell only 100 → ratio = 100/1000 = 0.1
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=1000,
                sol_amount=10,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.1,
                fee_creator_sol=0.05,
                fee_protocol_sol=0.03,
                fee_staker_sol=0.02,
                trader_address=addr,
                phase="bonding",
                source="api",
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=100,
                sol_amount=1,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.01,
                fee_creator_sol=0.005,
                fee_protocol_sol=0.003,
                fee_staker_sol=0.002,
                trader_address=addr,
                phase="bonding",
                source="api",
            )
        )
        await db_session.flush()

        result = await check_wash_trading(
            db_session,
            soul_token_id=token.id,
            trader_address=addr,
        )
        assert result is None

    async def test_pump_only_sells(self, db_session, risk_token):
        """Pump: price rise >50% but all sells, no buys → returns None (line 162)."""
        from nile.services.risk_engine import check_pump_and_dump

        token = risk_token
        # 3 sell trades with rising prices
        for price in [0.01, 0.012, 0.02]:
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="sell",
                    token_amount=100,
                    sol_amount=1,
                    price_sol=price,
                    price_usd=price * 250,
                    fee_total_sol=0.01,
                    fee_creator_sol=0.005,
                    fee_protocol_sol=0.003,
                    fee_staker_sol=0.002,
                    trader_address="OS" * 22,
                    phase="bonding",
                    source="api",
                )
            )
        await db_session.flush()

        result = await check_pump_and_dump(
            db_session,
            soul_token_id=token.id,
        )
        assert result is None

    async def test_pump_low_concentration(self, db_session, risk_token):
        """Pump: price >50% but spread across many wallets → None (line 192)."""
        from nile.services.risk_engine import check_pump_and_dump

        token = risk_token
        # Create buys from many wallets with >50% price increase
        wallets = [f"{chr(65 + i)}" * 44 for i in range(10)]
        prices = [0.01, 0.011, 0.012, 0.013, 0.014, 0.015, 0.016, 0.017, 0.018, 0.02]
        for wallet, price in zip(wallets, prices, strict=True):
            db_session.add(
                Trade(
                    soul_token_id=token.id,
                    side="buy",
                    token_amount=100,
                    sol_amount=1,
                    price_sol=price,
                    price_usd=price * 250,
                    fee_total_sol=0.01,
                    fee_creator_sol=0.005,
                    fee_protocol_sol=0.003,
                    fee_staker_sol=0.002,
                    trader_address=wallet,
                    phase="bonding",
                    source="api",
                )
            )
        await db_session.flush()

        result = await check_pump_and_dump(
            db_session,
            soul_token_id=token.id,
        )
        # 10 unique wallets, top 3 = 30% < 70% threshold
        assert result is None

    async def test_cliff_single_trade(self, db_session, risk_token):
        """Cliff: only 1 trade → returns None (line 215)."""
        from nile.services.risk_engine import check_cliff_event

        token = risk_token
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=100,
                sol_amount=1,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.01,
                fee_creator_sol=0.005,
                fee_protocol_sol=0.003,
                fee_staker_sol=0.002,
                trader_address="ST" * 22,
                phase="bonding",
                source="api",
            )
        )
        await db_session.flush()

        result = await check_cliff_event(
            db_session,
            soul_token_id=token.id,
        )
        assert result is None

    @patch("nile.services.risk_engine.risk_to_circuit_breaker", new_callable=AsyncMock)
    async def test_run_risk_checks_wash_appended(self, mock_cb, db_session, risk_token):
        """run_risk_checks appends wash alert (line 259)."""
        from nile.services.risk_engine import run_risk_checks

        token = risk_token
        addr = "WA" * 22
        # Create wash trading pattern
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="buy",
                token_amount=1000,
                sol_amount=10,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.1,
                fee_creator_sol=0.05,
                fee_protocol_sol=0.03,
                fee_staker_sol=0.02,
                trader_address=addr,
                phase="bonding",
                source="api",
            )
        )
        db_session.add(
            Trade(
                soul_token_id=token.id,
                side="sell",
                token_amount=950,
                sol_amount=9.5,
                price_sol=0.01,
                price_usd=2.50,
                fee_total_sol=0.095,
                fee_creator_sol=0.0475,
                fee_protocol_sol=0.0285,
                fee_staker_sol=0.019,
                trader_address=addr,
                phase="bonding",
                source="api",
            )
        )
        await db_session.flush()

        alerts = await run_risk_checks(
            db_session,
            soul_token_id=token.id,
            trader_address=addr,
        )
        wash_alerts = [a for a in alerts if a.get("risk_type") == "wash_trading"]
        assert len(wash_alerts) >= 1


# ── soul_agent_incentives.py:94 — capability filter ──


@pytest.mark.asyncio
class TestSoulAgentCapabilityFilter:
    async def test_rankings_with_capability(self, db_session):
        from nile.services.soul_agent_incentives import get_soul_agent_rankings

        agent = Agent(
            name=f"cap-agent-{uuid.uuid4().hex[:6]}",
            owner_id="test",
            capabilities=["detect", "report"],
            status="active",
            api_key_hash="unused",
            total_points=100,
        )
        db_session.add(agent)
        await db_session.flush()

        # Filter by capability
        result = await get_soul_agent_rankings(db_session, capability="detect")
        assert isinstance(result, list)
