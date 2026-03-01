"""Tests for NileBot async methods — setup_hook, on_ready, _ensure_channels, etc."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nile.discord.bot import NileBot


@pytest.fixture
def bot():
    """Create a NileBot with all internals mocked."""
    with patch("nile.discord.bot.discord.Client.__init__", return_value=None):
        b = NileBot.__new__(NileBot)
        b.tree = MagicMock()
        b.tree.sync = AsyncMock()
        b.tree.copy_global_to = MagicMock()
        b.redis = AsyncMock()
        # redis.pubsub() is a sync call that returns an async pubsub object
        b.redis.pubsub = MagicMock(return_value=AsyncMock())
        b._listener_task = None
        b._screenshot_task = None
        b._target_guild = None
        b._channels = {}
        # 'user' and 'guilds' are read-only properties on discord.Client
        mock_user = MagicMock()
        mock_user.__str__ = lambda s: "NileBot#1234"
        b._guilds = []  # internal storage for our mock
        with (
            patch.object(type(b), "user", new_callable=lambda: property(lambda self: mock_user)),
            patch.object(
                type(b),
                "guilds",
                new_callable=lambda: property(lambda self: self._guilds),
            ),
        ):
            yield b


@pytest.mark.asyncio
class TestSetupHook:
    @patch("nile.discord.bot.settings")
    @patch("nile.discord.bot.aioredis")
    async def test_with_guild_id(self, mock_aioredis, mock_settings, bot):
        mock_settings.redis_url = "redis://localhost"
        mock_settings.discord_guild_id = "123456"
        mock_redis = AsyncMock()
        mock_aioredis.from_url.return_value = mock_redis

        mock_guild = MagicMock()
        with patch("nile.discord.bot.discord.Object", return_value=mock_guild):
            await bot.setup_hook()

        bot.tree.copy_global_to.assert_called_once()
        bot.tree.sync.assert_called_once()

    @patch("nile.discord.bot.settings")
    @patch("nile.discord.bot.aioredis")
    async def test_without_guild_id(self, mock_aioredis, mock_settings, bot):
        mock_settings.redis_url = "redis://localhost"
        mock_settings.discord_guild_id = ""
        mock_aioredis.from_url.return_value = AsyncMock()

        await bot.setup_hook()

        bot.tree.copy_global_to.assert_not_called()
        bot.tree.sync.assert_called_once_with()


@pytest.mark.asyncio
class TestOnReady:
    @patch("nile.discord.bot.settings")
    async def test_with_guild_id(self, mock_settings, bot):
        mock_settings.discord_guild_id = "123456"
        mock_guild = MagicMock()
        mock_guild.name = "Test Guild"
        mock_guild.id = 123456
        bot.get_guild = MagicMock(return_value=mock_guild)
        bot._ensure_channels = AsyncMock()

        with patch("nile.discord.bot.asyncio") as mock_asyncio:
            mock_asyncio.create_task = MagicMock()
            await bot.on_ready()

        assert bot._target_guild == mock_guild
        bot._ensure_channels.assert_called_once()

    @patch("nile.discord.bot.settings")
    async def test_no_guild_returns(self, mock_settings, bot):
        mock_settings.discord_guild_id = ""
        bot.get_guild = MagicMock(return_value=None)
        bot._guilds = []

        await bot.on_ready()

        assert bot._target_guild is None

    @patch("nile.discord.bot.settings")
    async def test_falls_back_to_first_guild(self, mock_settings, bot):
        mock_settings.discord_guild_id = ""
        bot.get_guild = MagicMock(return_value=None)
        mock_guild = MagicMock()
        mock_guild.name = "Fallback"
        mock_guild.id = 999
        bot._guilds = [mock_guild]
        bot._ensure_channels = AsyncMock()

        with patch("nile.discord.bot.asyncio") as mock_asyncio:
            mock_asyncio.create_task = MagicMock()
            await bot.on_ready()

        assert bot._target_guild == mock_guild

    @patch("nile.discord.bot.settings")
    async def test_posts_startup_message(self, mock_settings, bot):
        mock_settings.discord_guild_id = "111"
        mock_guild = MagicMock()
        mock_guild.name = "G"
        mock_guild.id = 111
        bot.get_guild = MagicMock(return_value=mock_guild)
        bot._ensure_channels = AsyncMock()

        mock_feed = AsyncMock()
        bot._channels = {"nile-feed": mock_feed}

        with patch("nile.discord.bot.asyncio") as mock_asyncio:
            mock_asyncio.create_task = MagicMock()
            await bot.on_ready()

        mock_feed.send.assert_called_once()

    @patch("nile.discord.bot.settings")
    async def test_startup_message_forbidden(self, mock_settings, bot):
        import discord

        mock_settings.discord_guild_id = "111"
        mock_guild = MagicMock()
        mock_guild.name = "G"
        mock_guild.id = 111
        bot.get_guild = MagicMock(return_value=mock_guild)
        bot._ensure_channels = AsyncMock()

        mock_feed = AsyncMock()
        # Raise discord.Forbidden to test the exception handler
        mock_feed.send.side_effect = discord.Forbidden(MagicMock(), "Missing Send Messages")
        bot._channels = {"nile-feed": mock_feed}

        with patch("nile.discord.bot.asyncio") as mock_asyncio:
            mock_asyncio.create_task = MagicMock()
            # Should not raise even when send fails
            await bot.on_ready()


@pytest.mark.asyncio
class TestEnsureChannels:
    async def test_no_guild_returns(self, bot):
        bot._target_guild = None
        await bot._ensure_channels()
        assert bot._channels == {}

    async def test_creates_category_and_channels(self, bot):
        mock_guild = MagicMock()
        mock_guild.categories = []
        mock_guild.text_channels = []
        mock_guild.default_role = MagicMock()
        mock_guild.me = MagicMock()

        mock_category = MagicMock()
        mock_guild.create_category = AsyncMock(return_value=mock_category)

        mock_channel = MagicMock()
        mock_guild.create_text_channel = AsyncMock(return_value=mock_channel)

        bot._target_guild = mock_guild

        with (
            patch("nile.discord.bot.discord.utils.get", return_value=None),
            patch("nile.discord.bot.discord.PermissionOverwrite"),
        ):
            await bot._ensure_channels()

        mock_guild.create_category.assert_called_once()
        assert mock_guild.create_text_channel.call_count == 7  # 7 managed channels

    async def test_uses_existing_channels(self, bot):
        mock_guild = MagicMock()
        mock_guild.me = MagicMock()

        existing_channel = AsyncMock()

        bot._target_guild = mock_guild

        def mock_get(collection, name=None):
            if collection == mock_guild.categories:
                return MagicMock()  # category exists
            return existing_channel  # channel exists

        with patch("nile.discord.bot.discord.utils.get", side_effect=mock_get):
            await bot._ensure_channels()

        assert len(bot._channels) == 7

    async def test_channel_create_forbidden(self, bot):
        mock_guild = MagicMock()
        mock_guild.categories = []
        mock_guild.text_channels = []
        mock_guild.default_role = MagicMock()
        mock_guild.me = MagicMock()

        import discord

        mock_guild.create_category = AsyncMock(
            side_effect=discord.Forbidden(MagicMock(), "Missing permissions")
        )
        mock_guild.create_text_channel = AsyncMock(
            side_effect=discord.Forbidden(MagicMock(), "Missing permissions")
        )

        bot._target_guild = mock_guild

        with (
            patch("nile.discord.bot.discord.utils.get", return_value=None),
            patch("nile.discord.bot.discord.PermissionOverwrite"),
        ):
            await bot._ensure_channels()

        # Should not raise, just log warnings
        assert len(bot._channels) == 0


@pytest.mark.asyncio
class TestListenEvents:
    async def test_no_redis_returns(self, bot):
        bot.redis = None
        await bot._listen_events()

    async def test_processes_messages(self, bot):
        mock_pubsub = MagicMock()
        messages = [
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": json.dumps({"event_type": "agent.joined", "metadata": {}})},
        ]

        async def mock_listen():
            for m in messages:
                yield m
            raise asyncio.CancelledError()

        mock_pubsub.listen = mock_listen
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        # pubsub() is a sync call
        bot.redis.pubsub = MagicMock(return_value=mock_pubsub)
        bot._route_event = AsyncMock()

        with pytest.raises(asyncio.CancelledError):
            await bot._listen_events()

        bot._route_event.assert_called_once()

    async def test_handles_bad_json(self, bot):
        mock_pubsub = MagicMock()
        messages = [
            {"type": "message", "data": "not-json"},
        ]

        async def mock_listen():
            for m in messages:
                yield m
            raise asyncio.CancelledError()

        mock_pubsub.listen = mock_listen
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        bot.redis.pubsub = MagicMock(return_value=mock_pubsub)

        with pytest.raises(asyncio.CancelledError):
            await bot._listen_events()


@pytest.mark.asyncio
class TestScreenshotLoop:
    async def test_calls_post_all(self, bot):
        bot._post_all_screenshots = AsyncMock()

        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()

        with (
            patch("nile.discord.bot.asyncio.sleep", side_effect=mock_sleep),
            pytest.raises(asyncio.CancelledError),
        ):
            await bot._screenshot_loop()

        bot._post_all_screenshots.assert_called_once()

    async def test_handles_exception(self, bot):
        bot._post_all_screenshots = AsyncMock(side_effect=RuntimeError("fail"))

        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()

        with (
            patch("nile.discord.bot.asyncio.sleep", side_effect=mock_sleep),
            pytest.raises(asyncio.CancelledError),
        ):
            await bot._screenshot_loop()


@pytest.mark.asyncio
class TestPostAllScreenshots:
    @patch("nile.discord.bot.discord.File")
    @patch("nile.discord.bot.capture_all_pages", new_callable=AsyncMock)
    async def test_posts_screenshots(self, mock_capture, mock_file, bot):
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_capture.return_value = {"dashboard": mock_path}

        mock_channel = AsyncMock()
        bot._channels = {"nile-dashboard": mock_channel}

        await bot._post_all_screenshots()
        mock_capture.assert_called_once()

    @patch("nile.discord.bot.capture_all_pages", new_callable=AsyncMock)
    async def test_skips_missing_screenshots(self, mock_capture, bot):
        mock_capture.return_value = {}
        bot._channels = {"nile-dashboard": AsyncMock()}

        await bot._post_all_screenshots()
        # No sends should happen
        for ch in bot._channels.values():
            ch.send.assert_not_called()


@pytest.mark.asyncio
class TestPostScreenshotTo:
    @patch("nile.discord.bot.discord.File")
    @patch("nile.discord.bot.capture_page", new_callable=AsyncMock)
    async def test_posts_to_channel(self, mock_capture, mock_file, bot):
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_capture.return_value = mock_path

        mock_channel = AsyncMock()
        bot._channels = {"nile-dashboard": mock_channel}

        await bot._post_screenshot_to("nile-dashboard", "/", "dashboard")
        mock_channel.send.assert_called_once()

    @patch("nile.discord.bot.capture_page", new_callable=AsyncMock)
    async def test_no_screenshot_skips(self, mock_capture, bot):
        mock_capture.return_value = None
        mock_channel = AsyncMock()
        bot._channels = {"nile-dashboard": mock_channel}

        await bot._post_screenshot_to("nile-dashboard", "/", "dashboard")
        mock_channel.send.assert_not_called()

    @patch("nile.discord.bot.capture_page", new_callable=AsyncMock)
    async def test_no_channel_skips(self, mock_capture, bot):
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_capture.return_value = mock_path
        bot._channels = {}

        await bot._post_screenshot_to("nile-dashboard", "/", "dashboard")


@pytest.mark.asyncio
class TestSlashCommands:
    async def test_nile_status(self):
        from nile.discord.bot import nile_status

        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        # nile_status is a discord Command object; call its .callback
        await nile_status.callback(mock_interaction)
        mock_interaction.response.send_message.assert_called_once()

    @patch("nile.discord.bot.discord.File")
    @patch("nile.discord.bot.capture_all_pages", new_callable=AsyncMock)
    async def test_nile_screenshot_success(self, mock_capture, mock_file):
        from nile.discord.bot import bot as nile_bot
        from nile.discord.bot import nile_screenshot

        mock_capture.return_value = {"dashboard": Path("/tmp/d.png")}  # noqa: S108
        nile_bot._post_all_screenshots = AsyncMock()

        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.followup = AsyncMock()

        await nile_screenshot.callback(mock_interaction)
        mock_interaction.response.defer.assert_called_once()
        mock_interaction.followup.send.assert_called_once()

    @patch("nile.discord.bot.capture_all_pages", new_callable=AsyncMock)
    async def test_nile_screenshot_empty(self, mock_capture):
        from nile.discord.bot import nile_screenshot

        mock_capture.return_value = {}

        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.followup = AsyncMock()

        await nile_screenshot.callback(mock_interaction)
        call_args = mock_interaction.followup.send.call_args
        assert "Could not" in str(call_args)

    @patch("nile.discord.bot.discord.File")
    @patch("nile.discord.bot.capture_page", new_callable=AsyncMock)
    async def test_nile_leaderboard_with_screenshot(self, mock_capture, mock_file):
        from nile.discord.bot import nile_leaderboard

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_capture.return_value = mock_path

        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.followup = AsyncMock()

        await nile_leaderboard.callback(mock_interaction)
        mock_interaction.followup.send.assert_called_once()

    @patch("nile.discord.bot.capture_page", new_callable=AsyncMock)
    async def test_nile_leaderboard_no_screenshot(self, mock_capture):
        from nile.discord.bot import nile_leaderboard

        mock_capture.return_value = None

        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.followup = AsyncMock()

        await nile_leaderboard.callback(mock_interaction)
        mock_interaction.followup.send.assert_called_once()
