"""Tests for the NILE Discord bot — unit tests with mocked discord.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We need to mock discord before importing the bot module
# since discord may not be installed in test env


@pytest.fixture
def mock_discord():
    """Set up mock discord module and import the bot."""
    with patch.dict("sys.modules", {
        "discord": MagicMock(),
        "discord.ext": MagicMock(),
        "discord.ext.commands": MagicMock(),
    }):
        import importlib

        import nile.discord.bot as bot_mod

        importlib.reload(bot_mod)
        yield bot_mod


@pytest.fixture
def bot():
    """Create a NileBot instance with mocked discord internals."""
    from nile.discord.bot import NileBot

    with patch("nile.discord.bot.discord.Client.__init__", return_value=None):
        b = NileBot.__new__(NileBot)
        b.tree = MagicMock()
        b.redis = AsyncMock()
        b._listener_task = None
        b._screenshot_task = None
        b._target_guild = None
        b._channels = {}
        return b


class TestChannelTopic:
    def test_feed(self, bot):
        assert "ecosystem events" in bot._channel_topic("nile-feed").lower()

    def test_dashboard(self, bot):
        assert "dashboard" in bot._channel_topic("nile-dashboard").lower()

    def test_ecosystem(self, bot):
        assert "ecosystem" in bot._channel_topic("nile-ecosystem").lower()

    def test_agents(self, bot):
        assert "leaderboard" in bot._channel_topic("nile-agents").lower()

    def test_attacker(self, bot):
        assert "attacker" in bot._channel_topic("nile-attacker").lower()

    def test_defender(self, bot):
        assert "defender" in bot._channel_topic("nile-defender").lower()

    def test_alerts(self, bot):
        assert "alert" in bot._channel_topic("nile-alerts").lower()

    def test_unknown(self, bot):
        assert bot._channel_topic("unknown-channel") == "NILE Security"


class TestEventTitle:
    def test_agent_joined(self, bot):
        assert bot._event_title("agent.joined") == "New Agent Joined"

    def test_detection(self, bot):
        assert bot._event_title("contribution.detection") == "Vulnerability Detected"

    def test_patch(self, bot):
        assert bot._event_title("contribution.patch") == "Patch Submitted"

    def test_exploit(self, bot):
        assert bot._event_title("contribution.exploit") == "Exploit Verified"

    def test_scan_completed(self, bot):
        assert bot._event_title("scan.completed") == "Scan Completed"

    def test_task_claimed(self, bot):
        assert bot._event_title("task.claimed") == "Task Claimed"

    def test_false_positive(self, bot):
        assert bot._event_title("contribution.false_positive") == "False Positive"

    def test_verification(self, bot):
        assert bot._event_title("contribution.verification") == "Cross-Verification"

    def test_unknown(self, bot):
        assert bot._event_title("some.unknown") == "some.unknown"


class TestEventDescription:
    def test_agent_joined(self, bot):
        desc = bot._event_description(
            "agent.joined",
            {"name": "TestAgent", "capabilities": ["detect", "patch"]},
        )
        assert "TestAgent" in desc
        assert "detect" in desc

    def test_scan_completed(self, bot):
        desc = bot._event_description(
            "scan.completed", {"nile_score": 85, "grade": "A"}
        )
        assert "85" in desc
        assert "A" in desc

    def test_contribution(self, bot):
        desc = bot._event_description(
            "contribution.detection", {"points": 100, "severity": "critical"}
        )
        assert "100" in desc
        assert "critical" in desc

    def test_contribution_no_severity(self, bot):
        desc = bot._event_description(
            "contribution.patch", {"points": 75}
        )
        assert "75" in desc

    def test_unknown_with_metadata(self, bot):
        desc = bot._event_description(
            "some.unknown", {"key": "value"}
        )
        assert "key" in desc

    def test_unknown_empty_metadata(self, bot):
        desc = bot._event_description("some.unknown", {})
        assert desc == ""


class TestEventColor:
    def test_joined_green(self, bot):
        assert bot._event_color("agent.joined") == 0x22C55E

    def test_detection_red(self, bot):
        assert bot._event_color("contribution.detection") == 0xEF4444

    def test_exploit_red(self, bot):
        assert bot._event_color("contribution.exploit") == 0xEF4444

    def test_patch_blue(self, bot):
        assert bot._event_color("contribution.patch") == 0x3B82F6

    def test_false_positive_yellow(self, bot):
        assert bot._event_color("contribution.false_positive") == 0xF59E0B

    def test_risk_alert_red(self, bot):
        assert bot._event_color("soul.risk_alert") == 0xDC2626

    def test_default_purple(self, bot):
        assert bot._event_color("scan.completed") == 0x6366F1


@pytest.mark.asyncio
class TestRouteEvent:
    async def test_soul_event_dispatches(self, bot):
        bot._handle_soul_event = AsyncMock()
        await bot._route_event({
            "event_type": "soul.risk_alert",
            "metadata": {"severity": "critical"},
        })
        bot._handle_soul_event.assert_called_once()

    async def test_critical_event_goes_to_alerts(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-alerts": mock_channel}
        await bot._route_event({
            "event_type": "scan.completed",
            "metadata": {"severity": "critical"},
        })
        mock_channel.send.assert_called_once()

    async def test_normal_event_goes_to_feed(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-feed": mock_channel}
        await bot._route_event({
            "event_type": "agent.joined",
            "metadata": {"name": "TestBot"},
        })
        mock_channel.send.assert_called_once()

    async def test_no_channel_skips(self, bot):
        bot._channels = {}
        # Should not raise
        await bot._route_event({
            "event_type": "agent.joined",
            "metadata": {},
        })

    async def test_scan_completed_triggers_screenshot(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-feed": mock_channel}
        bot._post_screenshot_to = AsyncMock()
        with patch("nile.discord.bot.asyncio") as mock_asyncio:
            await bot._route_event({
                "event_type": "scan.completed",
                "metadata": {},
            })
            mock_asyncio.create_task.assert_called_once()


@pytest.mark.asyncio
class TestHandleSoulEvent:
    async def test_risk_alert(self, bot):
        bot._post_risk_alert = AsyncMock()
        await bot._handle_soul_event("soul.risk_alert", {"severity": "critical"})
        bot._post_risk_alert.assert_called_once()

    async def test_token_graduated(self, bot):
        bot._post_graduation = AsyncMock()
        await bot._handle_soul_event("soul.token_graduated", {})
        bot._post_graduation.assert_called_once()

    async def test_oracle_confirmed(self, bot):
        bot._post_oracle_confirmed = AsyncMock()
        await bot._handle_soul_event("soul.oracle_confirmed", {})
        bot._post_oracle_confirmed.assert_called_once()

    async def test_oracle_pending(self, bot):
        bot._post_oracle_pending = AsyncMock()
        await bot._handle_soul_event("soul.oracle_report_pending", {})
        bot._post_oracle_pending.assert_called_once()

    async def test_valuation_changed(self, bot):
        bot._post_valuation_change = AsyncMock()
        await bot._handle_soul_event("soul.valuation_changed", {})
        bot._post_valuation_change.assert_called_once()

    async def test_generic_soul_event(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-feed": mock_channel}
        await bot._handle_soul_event("soul.unknown_event", {"key": "val"})
        mock_channel.send.assert_called_once()

    async def test_generic_soul_event_no_channel(self, bot):
        bot._channels = {}
        # Should not raise
        await bot._handle_soul_event("soul.unknown_event", {})


@pytest.mark.asyncio
class TestPostRiskAlert:
    async def test_posts_to_alerts_channel(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-alerts": mock_channel}
        await bot._post_risk_alert({
            "severity": "critical",
            "risk_type": "wash_trading",
            "token_id": "tok123",
            "action": "pause",
            "pause_minutes": 30,
            "details": {"volume": 1000},
        })
        mock_channel.send.assert_called_once()

    async def test_no_channel_returns(self, bot):
        bot._channels = {}
        await bot._post_risk_alert({"severity": "warning"})

    async def test_warning_severity_color(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-alerts": mock_channel}
        await bot._post_risk_alert({
            "severity": "warning",
            "risk_type": "unusual_volume",
        })
        mock_channel.send.assert_called_once()


@pytest.mark.asyncio
class TestPostGraduation:
    async def test_posts_graduation(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-feed": mock_channel}
        await bot._post_graduation({
            "token_symbol": "SOUL",
            "reserve_sol": 42.5,
        })
        mock_channel.send.assert_called_once()

    async def test_no_channel(self, bot):
        bot._channels = {}
        await bot._post_graduation({})


@pytest.mark.asyncio
class TestPostOracleConfirmed:
    async def test_posts_oracle(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-feed": mock_channel}
        await bot._post_oracle_confirmed({
            "person_id": "p1",
            "impact_score": 50,
            "event_type": "sports_win",
        })
        mock_channel.send.assert_called_once()

    async def test_no_channel(self, bot):
        bot._channels = {}
        await bot._post_oracle_confirmed({})


@pytest.mark.asyncio
class TestPostOraclePending:
    async def test_posts_pending(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-feed": mock_channel}
        await bot._post_oracle_pending({
            "headline": "Player wins championship",
            "source": "twitter",
        })
        mock_channel.send.assert_called_once()

    async def test_no_channel(self, bot):
        bot._channels = {}
        await bot._post_oracle_pending({})


@pytest.mark.asyncio
class TestPostValuationChange:
    async def test_posts_increase(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-feed": mock_channel}
        await bot._post_valuation_change({
            "person_id": "p1",
            "old_score": 50.0,
            "new_score": 75.0,
            "change_pct": 50.0,
            "fair_value_usd": 12.50,
        })
        mock_channel.send.assert_called_once()

    async def test_posts_decrease(self, bot):
        mock_channel = AsyncMock()
        bot._channels = {"nile-feed": mock_channel}
        await bot._post_valuation_change({
            "person_id": "p1",
            "old_score": 75.0,
            "new_score": 50.0,
            "change_pct": -33.3,
            "fair_value_usd": 8.00,
        })
        mock_channel.send.assert_called_once()

    async def test_no_channel(self, bot):
        bot._channels = {}
        await bot._post_valuation_change({})


class TestRunBot:
    @patch("nile.discord.bot.settings")
    def test_no_token_logs_error(self, mock_settings):
        mock_settings.discord_token = ""
        from nile.discord.bot import run_bot

        # Should return early without calling bot.run
        with patch("nile.discord.bot.bot") as mock_bot:
            run_bot()
            mock_bot.run.assert_not_called()

    @patch("nile.discord.bot.settings")
    def test_with_token_runs(self, mock_settings):
        mock_settings.discord_token = "test-token"
        from nile.discord.bot import run_bot

        with patch("nile.discord.bot.bot") as mock_bot:
            run_bot()
            mock_bot.run.assert_called_once_with("test-token")


class TestManagedChannels:
    def test_channel_list_has_7(self):
        from nile.discord.bot import MANAGED_CHANNELS

        assert len(MANAGED_CHANNELS) == 7

    def test_screenshot_interval(self):
        from nile.discord.bot import SCREENSHOT_INTERVAL

        assert SCREENSHOT_INTERVAL == 3600
