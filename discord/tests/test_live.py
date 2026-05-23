"""Live integration tests for Discord REST API.

Required env vars:
    DISCORD_RUN_LIVE_TESTS=1   -- opts into hitting the API.
    DISCORD_BOT_TOKEN=...       -- bot token.

Optional:
    DISCORD_LIVE_GUILD_ID    -- a guild your bot is in (enables guild reads).
    DISCORD_LIVE_CHANNEL_ID  -- a channel your bot can post in (enables write tests).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("DISCORD_RUN_LIVE_TESTS") != "1",
    reason="Set DISCORD_RUN_LIVE_TESTS=1 and DISCORD_BOT_TOKEN to run live tests",
)


@pytest.fixture(scope="module")
def live_server():
    from discord_mcp.gen.discord.v1 import discord_pb2 as _discord_pb2  # noqa: F401
    from discord_mcp.service import DiscordService
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH)
    srv.register(DiscordService(), service_name="discord.v1.DiscordService")
    yield srv
    asyncio.run(srv.stop())


def test_get_current_user(live_server):
    result = asyncio.run(live_server._cli(["DiscordService", "GetCurrentUser"]))
    assert isinstance(result, dict)
    assert result.get("id"), result


def test_get_gateway(live_server):
    result = asyncio.run(live_server._cli(["DiscordService", "GetGateway"]))
    assert isinstance(result, dict)
    assert "url" in result, result


@pytest.mark.skipif(not os.getenv("DISCORD_LIVE_GUILD_ID"), reason="set DISCORD_LIVE_GUILD_ID")
def test_get_guild(live_server):
    import json

    guild_id = os.environ["DISCORD_LIVE_GUILD_ID"]
    result = asyncio.run(
        live_server._cli(["DiscordService", "GetGuild", "-r", json.dumps({"guild_id": guild_id})])
    )
    assert isinstance(result, dict)
    assert result.get("id") == guild_id


@pytest.mark.skipif(not os.getenv("DISCORD_LIVE_CHANNEL_ID"), reason="set DISCORD_LIVE_CHANNEL_ID")
def test_post_and_delete_message(live_server):
    import json

    channel_id = os.environ["DISCORD_LIVE_CHANNEL_ID"]
    posted = asyncio.run(
        live_server._cli(
            [
                "DiscordService",
                "CreateMessage",
                "-r",
                json.dumps({"channel_id": channel_id, "body": {"content": "invariantaf live test"}}),
            ]
        )
    )
    assert posted.get("id"), posted
    msg_id = posted["id"]
    deleted = asyncio.run(
        live_server._cli(
            [
                "DiscordService",
                "DeleteMessage",
                "-r",
                json.dumps({"channel_id": channel_id, "message_id": msg_id}),
            ]
        )
    )
    assert deleted.get("status") in (200, 204), deleted
