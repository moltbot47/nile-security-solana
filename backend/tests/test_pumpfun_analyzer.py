"""Tests for pump.fun-specific token heuristic analysis."""

from unittest.mock import AsyncMock, patch

import pytest

from nile.services.pumpfun_analyzer import (
    CONCENTRATION_EXTREME_PCT,
    CONCENTRATION_HIGH_PCT,
    SERIAL_DEPLOYER_MIN_TOKENS,
    SINGLE_WHALE_PCT,
    PumpFunAnalysis,
    PumpFunTokenAnalyzer,
)


@pytest.fixture
def analyzer():
    return PumpFunTokenAnalyzer()


@pytest.fixture
def clean_token_info():
    return {
        "mint": "TokenMint1111111111111111111111111111111111",
        "supply": 1_000_000_000_000,
        "decimals": 6,
        "mint_authority_active": False,
        "mint_authority": None,
        "freeze_authority_active": False,
        "freeze_authority": None,
    }


@pytest.fixture
def scam_token_info():
    return {
        "mint": "ScamMint1111111111111111111111111111111111",
        "supply": 1_000_000_000_000,
        "decimals": 6,
        "mint_authority_active": True,
        "mint_authority": "Creator11111111111111111111111111111111111",
        "freeze_authority_active": True,
        "freeze_authority": "Creator11111111111111111111111111111111111",
    }


# --- Holder Concentration Tests ---


class TestHolderConcentration:
    @pytest.mark.anyio
    async def test_extreme_concentration(self, analyzer):
        """Top 5 wallets holding >80% triggers extreme flag."""
        mock_accounts = [
            {"address": f"Holder{i}", "amount": 250_000_000_000, "decimals": 6, "ui_amount": 250_000.0}
            for i in range(4)
        ]
        with patch(
            "nile.services.chain_service.chain_service.get_token_largest_accounts",
            new_callable=AsyncMock,
            return_value=mock_accounts,
        ):
            result = await analyzer._analyze_holder_concentration(
                "TokenMint1111111111111111111111111111111111",
                1_000_000_000_000,
                6,
            )

        assert result["top5_pct"] == 100.0
        assert result["whale_count"] == 4

    @pytest.mark.anyio
    async def test_moderate_concentration(self, analyzer):
        """50% concentration should not trigger extreme flag."""
        mock_accounts = [
            {"address": "Holder1", "amount": 500_000_000_000, "decimals": 6, "ui_amount": 500_000.0},
            {"address": "Holder2", "amount": 100_000_000_000, "decimals": 6, "ui_amount": 100_000.0},
        ]
        with patch(
            "nile.services.chain_service.chain_service.get_token_largest_accounts",
            new_callable=AsyncMock,
            return_value=mock_accounts,
        ):
            result = await analyzer._analyze_holder_concentration(
                "TokenMint1111111111111111111111111111111111",
                1_000_000_000_000,
                6,
            )

        assert result["top5_pct"] == 60.0
        assert result["whale_count"] == 2

    @pytest.mark.anyio
    async def test_single_whale(self, analyzer):
        """One holder with >50% supply."""
        mock_accounts = [
            {"address": "Whale1", "amount": 600_000_000_000, "decimals": 6, "ui_amount": 600_000.0},
            {"address": "Holder2", "amount": 50_000_000_000, "decimals": 6, "ui_amount": 50_000.0},
        ]
        with patch(
            "nile.services.chain_service.chain_service.get_token_largest_accounts",
            new_callable=AsyncMock,
            return_value=mock_accounts,
        ):
            result = await analyzer._analyze_holder_concentration(
                "TokenMint1111111111111111111111111111111111",
                1_000_000_000_000,
                6,
            )

        assert result["top_holders"][0]["pct"] == 60.0
        assert result["whale_count"] == 1  # Only Whale1 > 5%

    @pytest.mark.anyio
    async def test_empty_holders(self, analyzer):
        """RPC returns None — graceful degradation."""
        with patch(
            "nile.services.chain_service.chain_service.get_token_largest_accounts",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await analyzer._analyze_holder_concentration(
                "TokenMint1111111111111111111111111111111111",
                1_000_000_000_000,
                6,
            )

        assert result["top5_pct"] == 0.0
        assert result["whale_count"] == 0

    @pytest.mark.anyio
    async def test_zero_supply(self, analyzer):
        """Zero supply — no division error."""
        with patch(
            "nile.services.chain_service.chain_service.get_token_largest_accounts",
            new_callable=AsyncMock,
            return_value=[{"address": "H1", "amount": 100, "decimals": 6, "ui_amount": 0.0001}],
        ):
            result = await analyzer._analyze_holder_concentration(
                "TokenMint1111111111111111111111111111111111",
                0,
                6,
            )

        assert result["top5_pct"] == 0.0


# --- Creator Analysis Tests ---


class TestCreatorAnalysis:
    @pytest.mark.anyio
    async def test_serial_deployer(self, analyzer):
        """Creator with 10 token accounts flagged as serial deployer."""
        mock_accounts = [
            {"pubkey": f"Acct{i}", "mint": f"Mint{i}", "amount": 1000, "decimals": 6}
            for i in range(10)
        ]
        with patch(
            "nile.services.chain_service.chain_service.get_token_accounts_by_owner",
            new_callable=AsyncMock,
            return_value=mock_accounts,
        ):
            result = await analyzer._analyze_creator_wallet(
                {"mint_authority": "Creator11111111111111111111111111111111111"},
                "TokenMint1111111111111111111111111111111111",
            )

        assert result["serial_deployer"] is True
        assert result["token_count"] == 10
        assert result["creator_address"] == "Creator11111111111111111111111111111111111"

    @pytest.mark.anyio
    async def test_legitimate_creator(self, analyzer):
        """Creator with 2 token accounts is normal."""
        mock_accounts = [
            {"pubkey": "Acct1", "mint": "Mint1", "amount": 1000, "decimals": 6},
            {"pubkey": "Acct2", "mint": "Mint2", "amount": 1000, "decimals": 6},
        ]
        with patch(
            "nile.services.chain_service.chain_service.get_token_accounts_by_owner",
            new_callable=AsyncMock,
            return_value=mock_accounts,
        ):
            result = await analyzer._analyze_creator_wallet(
                {"mint_authority": "Creator11111111111111111111111111111111111"},
                "TokenMint1111111111111111111111111111111111",
            )

        assert result["serial_deployer"] is False
        assert result["token_count"] == 2

    @pytest.mark.anyio
    async def test_no_creator(self, analyzer):
        """No mint authority and no fallback — creator is None."""
        result = await analyzer._analyze_creator_wallet(
            {"mint_authority": None},
            "TokenMint1111111111111111111111111111111111",
        )

        assert result["creator_address"] is None
        assert result["serial_deployer"] is False


# --- Liquidity Detection Tests ---


class TestLiquidityDetection:
    @pytest.mark.anyio
    async def test_token_on_jupiter(self, analyzer):
        """Token on Jupiter strict list → LP detected."""
        with patch(
            "nile.services.ecosystem_checker.check_jupiter_strict_list",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await analyzer._detect_liquidity_pools("TokenMint1111111111111111111111111111111111")

        assert result["lp_detected"] is True
        assert result["has_raydium_lp"] is True

    @pytest.mark.anyio
    async def test_token_not_on_jupiter(self, analyzer):
        """Token not on Jupiter → no LP detected."""
        with patch(
            "nile.services.ecosystem_checker.check_jupiter_strict_list",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await analyzer._detect_liquidity_pools("TokenMint1111111111111111111111111111111111")

        assert result["lp_detected"] is False


# --- Token Age Tests ---


class TestTokenAge:
    @pytest.mark.anyio
    async def test_very_young_token(self, analyzer):
        """Token created hours ago."""
        with patch(
            "nile.services.ecosystem_checker.check_program_age_days",
            new_callable=AsyncMock,
            return_value=0,
        ):
            result = await analyzer._estimate_token_age("TokenMint1111111111111111111111111111111111")

        assert result["age_days"] == 0.0
        assert result["age_seconds"] is None

    @pytest.mark.anyio
    async def test_mature_token(self, analyzer):
        """90-day-old token."""
        with patch(
            "nile.services.ecosystem_checker.check_program_age_days",
            new_callable=AsyncMock,
            return_value=90,
        ):
            result = await analyzer._estimate_token_age("TokenMint1111111111111111111111111111111111")

        assert result["age_days"] == 90.0
        assert result["age_seconds"] == 90 * 86400


# --- Risk Flags Tests ---


class TestRiskFlags:
    def test_clean_token_no_flags(self, analyzer):
        """Clean token with good metrics has no risk flags."""
        flags = analyzer._compute_risk_flags(
            token_info={"mint_authority_active": False, "freeze_authority_active": False},
            holder_data={"top5_pct": 30.0, "top_holders": [{"pct": 20.0}]},
            creator_data={"serial_deployer": False},
            lp_data={"lp_detected": True},
            age_data={"age_days": 365.0},
            on_jupiter=True,
        )
        assert flags == []

    def test_all_red_flags(self, analyzer):
        """Maximum risk token triggers all flags."""
        flags = analyzer._compute_risk_flags(
            token_info={"mint_authority_active": True, "freeze_authority_active": True},
            holder_data={
                "top5_pct": 90.0,
                "top_holders": [{"pct": 60.0}, {"pct": 20.0}],
            },
            creator_data={"serial_deployer": True},
            lp_data={"lp_detected": False},
            age_data={"age_days": 0.5},
            on_jupiter=False,
        )
        assert "supply_concentration_extreme" in flags
        assert "single_whale_dominance" in flags
        assert "serial_deployer" in flags
        assert "no_liquidity_pool" in flags
        assert "honeypot_token" in flags
        assert "young_token_with_mint_authority" in flags

    def test_stablecoin_exception(self, analyzer):
        """Jupiter-listed token with freeze authority should NOT get honeypot flag."""
        flags = analyzer._compute_risk_flags(
            token_info={"mint_authority_active": False, "freeze_authority_active": True},
            holder_data={"top5_pct": 30.0, "top_holders": []},
            creator_data={"serial_deployer": False},
            lp_data={"lp_detected": False},
            age_data={"age_days": 365.0},
            on_jupiter=True,
        )
        assert "honeypot_token" not in flags

    def test_concentration_high_but_not_extreme(self, analyzer):
        """65% concentration triggers high flag, not extreme."""
        flags = analyzer._compute_risk_flags(
            token_info={"mint_authority_active": False, "freeze_authority_active": False},
            holder_data={"top5_pct": 65.0, "top_holders": [{"pct": 30.0}]},
            creator_data={"serial_deployer": False},
            lp_data={"lp_detected": True},
            age_data={"age_days": 30.0},
            on_jupiter=True,
        )
        assert "supply_concentration_high" in flags
        assert "supply_concentration_extreme" not in flags


# --- Risk Score Tests ---


class TestRiskScore:
    def test_clean_token_low_risk(self, analyzer):
        flags = analyzer._compute_risk_score(
            token_info={"mint_authority_active": False, "freeze_authority_active": False},
            holder_data={"top5_pct": 20.0, "top_holders": [{"pct": 10.0}]},
            creator_data={"serial_deployer": False},
            lp_data={"lp_detected": True},
            age_data={"age_days": 365.0},
        )
        assert flags == 0.0

    def test_all_red_flags_max_risk(self, analyzer):
        score = analyzer._compute_risk_score(
            token_info={"mint_authority_active": True, "freeze_authority_active": True},
            holder_data={
                "top5_pct": 95.0,
                "top_holders": [{"pct": 60.0}],
            },
            creator_data={"serial_deployer": True},
            lp_data={"lp_detected": False},
            age_data={"age_days": 0.5},
        )
        # 0.25 + 0.15 + 0.15 + 0.20 + 0.10 + 0.20 = 1.05 → clamped to 1.0
        assert score == 1.0

    def test_partial_risk(self, analyzer):
        score = analyzer._compute_risk_score(
            token_info={"mint_authority_active": True, "freeze_authority_active": False},
            holder_data={"top5_pct": 40.0, "top_holders": [{"pct": 20.0}]},
            creator_data={"serial_deployer": False},
            lp_data={"lp_detected": False},
            age_data={"age_days": 3.0},
        )
        # no LP: 0.20, age < 7 + mint: 0.10 = 0.30
        assert 0.2 <= score <= 0.4


# --- Full Analyze Integration Tests ---


class TestFullAnalyze:
    @pytest.mark.anyio
    async def test_analyze_safe_token(self, analyzer, clean_token_info):
        """Safe token with good signals produces low risk."""
        with (
            patch(
                "nile.services.chain_service.chain_service.get_token_largest_accounts",
                new_callable=AsyncMock,
                return_value=[
                    {"address": f"H{i}", "amount": 100_000_000_000, "decimals": 6, "ui_amount": 100_000.0}
                    for i in range(10)
                ],
            ),
            patch(
                "nile.services.ecosystem_checker.check_jupiter_strict_list",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "nile.services.ecosystem_checker.check_program_age_days",
                new_callable=AsyncMock,
                return_value=365,
            ),
        ):
            result = await analyzer.analyze(
                "TokenMint1111111111111111111111111111111111",
                clean_token_info,
            )

        assert isinstance(result, PumpFunAnalysis)
        assert result.risk_score < 0.3
        assert result.lp_detected is True
        assert len(result.risk_flags) == 0

    @pytest.mark.anyio
    async def test_analyze_scam_token(self, analyzer, scam_token_info):
        """Scam token with all bad signals produces high risk."""
        with (
            patch(
                "nile.services.chain_service.chain_service.get_token_largest_accounts",
                new_callable=AsyncMock,
                return_value=[
                    {"address": "Whale1", "amount": 900_000_000_000, "decimals": 6, "ui_amount": 900_000.0},
                ],
            ),
            patch(
                "nile.services.chain_service.chain_service.get_token_accounts_by_owner",
                new_callable=AsyncMock,
                return_value=[{"pubkey": f"T{i}", "mint": f"M{i}", "amount": 1, "decimals": 6} for i in range(10)],
            ),
            patch(
                "nile.services.ecosystem_checker.check_jupiter_strict_list",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "nile.services.ecosystem_checker.check_program_age_days",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            result = await analyzer.analyze(
                "ScamMint1111111111111111111111111111111111",
                scam_token_info,
            )

        assert result.risk_score >= 0.8
        assert result.serial_deployer is True
        assert result.lp_detected is False
        assert "supply_concentration_extreme" in result.risk_flags
        assert "serial_deployer" in result.risk_flags
        assert "no_liquidity_pool" in result.risk_flags


# --- Enhanced Rug Similarity Tests (via program_analyzer) ---


class TestEnhancedRugSimilarity:
    def test_max_risk_all_signals(self):
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        pf = PumpFunAnalysis(
            top5_concentration_pct=95.0,
            lp_detected=False,
            serial_deployer=True,
            mint_age_days=0.1,
        )
        score = analyzer._compute_enhanced_rug_similarity(
            {"mint_authority_active": True, "freeze_authority_active": True},
            pf,
        )
        assert score == 1.0

    def test_no_risk_clean_signals(self):
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        pf = PumpFunAnalysis(
            top5_concentration_pct=20.0,
            lp_detected=True,
            serial_deployer=False,
            mint_age_days=365.0,
        )
        score = analyzer._compute_enhanced_rug_similarity(
            {"mint_authority_active": False, "freeze_authority_active": False},
            pf,
        )
        assert score == 0.0

    def test_concentration_only(self):
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        pf = PumpFunAnalysis(
            top5_concentration_pct=85.0,
            lp_detected=True,
            mint_age_days=30.0,
        )
        score = analyzer._compute_enhanced_rug_similarity(
            {"mint_authority_active": False, "freeze_authority_active": False},
            pf,
        )
        # Only concentration: 0.20
        assert score == 0.2


# --- New Exploit Pattern Matching Tests ---


class TestNewExploitPatterns:
    def test_sol011_supply_concentration(self):
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        pf = PumpFunAnalysis(
            top5_concentration_pct=85.0,
            top_holders=[{"pct": 55.0}, {"pct": 15.0}, {"pct": 10.0}],
        )
        matches = analyzer._match_token_exploit_patterns(
            {"mint_authority_active": False, "freeze_authority_active": False},
            pf,
        )
        sol011 = [m for m in matches if m["pattern_id"] == "SOL-011"]
        assert len(sol011) == 1
        assert sol011[0]["confidence"] >= 0.7

    def test_sol012_serial_deployer(self):
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        pf = PumpFunAnalysis(serial_deployer=True, creator_token_count=10)
        matches = analyzer._match_token_exploit_patterns(
            {"mint_authority_active": False, "freeze_authority_active": False},
            pf,
        )
        sol012 = [m for m in matches if m["pattern_id"] == "SOL-012"]
        assert len(sol012) == 1
        assert sol012[0]["confidence"] >= 0.5

    def test_sol013_illiquid(self):
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        pf = PumpFunAnalysis(lp_detected=False, has_raydium_lp=False, has_orca_lp=False)
        matches = analyzer._match_token_exploit_patterns(
            {"mint_authority_active": False, "freeze_authority_active": False},
            pf,
        )
        sol013 = [m for m in matches if m["pattern_id"] == "SOL-013"]
        assert len(sol013) == 1

    def test_sol014_honeypot(self):
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        pf = PumpFunAnalysis(lp_detected=False)
        matches = analyzer._match_token_exploit_patterns(
            {"mint_authority_active": True, "freeze_authority_active": True},
            pf,
        )
        sol014 = [m for m in matches if m["pattern_id"] == "SOL-014"]
        assert len(sol014) == 1
        assert sol014[0]["confidence"] >= 0.8

    def test_no_pumpfun_data_generic_match(self):
        """Without pumpfun analysis, all rug_pull patterns use generic confidence."""
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        matches = analyzer._match_token_exploit_patterns(
            {"mint_authority_active": True, "freeze_authority_active": True},
        )
        pattern_ids = [m["pattern_id"] for m in matches]
        assert "SOL-006" in pattern_ids
        # All rug_pull patterns match via generic branch (mint + freeze = 0.5 confidence)
        for m in matches:
            assert m["confidence"] == 0.5  # Generic: 0.3 (mint) + 0.2 (freeze)

    def test_safe_token_no_matches_without_pf(self):
        """Safe token without pf data should have no rug matches."""
        from nile.services.program_analyzer import SolanaProgramAnalyzer

        analyzer = SolanaProgramAnalyzer()
        matches = analyzer._match_token_exploit_patterns(
            {"mint_authority_active": False, "freeze_authority_active": False},
        )
        assert len(matches) == 0
