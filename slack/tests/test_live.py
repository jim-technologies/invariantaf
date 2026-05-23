"""Live integration tests for Slack Web API -- hits real api.slack.com.

Required env vars:
    SLACK_RUN_LIVE_TESTS=1   -- opts into hitting the API.
    SLACK_BOT_TOKEN=xoxb-... -- bot token with appropriate scopes.

Optional:
    SLACK_LIVE_CHANNEL_ID  -- channel ID used by write tests. If unset, only
                              identity/read-only tests run.
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
    os.getenv("SLACK_RUN_LIVE_TESTS") != "1",
    reason="Set SLACK_RUN_LIVE_TESTS=1 and SLACK_BOT_TOKEN to run live tests",
)


@pytest.fixture(scope="module")
def live_server():
    from slack_mcp.gen.slack.v1 import slack_pb2 as _slack_pb2  # noqa: F401
    from slack_mcp.service import SlackService
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH)
    srv.register(SlackService(), service_name="slack.v1.SlackService")
    yield srv
    asyncio.run(srv.stop())


def test_auth_test_returns_ok(live_server):
    result = asyncio.run(live_server._cli(["SlackService", "AuthTest"]))
    assert isinstance(result, dict)
    assert result.get("ok") is True, result


def test_conversations_list(live_server):
    result = asyncio.run(
        live_server._cli(
            ["SlackService", "ConversationsList", "-r", '{"limit": 5, "types": "public_channel"}']
        )
    )
    assert isinstance(result, dict)
    assert "channels" in result


def test_users_list(live_server):
    result = asyncio.run(live_server._cli(["SlackService", "UsersList", "-r", '{"limit": 5}']))
    assert isinstance(result, dict)
    assert "members" in result


@pytest.mark.skipif(not os.getenv("SLACK_LIVE_CHANNEL_ID"), reason="set SLACK_LIVE_CHANNEL_ID")
def test_post_and_delete_message(live_server):
    import json

    channel = os.environ["SLACK_LIVE_CHANNEL_ID"]
    posted = asyncio.run(
        live_server._cli(
            [
                "SlackService",
                "ChatPostMessage",
                "-r",
                json.dumps({"channel": channel, "text": "invariantaf live test ping"}),
            ]
        )
    )
    assert posted.get("ok") is True, posted
    ts = posted["ts"]
    deleted = asyncio.run(
        live_server._cli(
            ["SlackService", "ChatDelete", "-r", json.dumps({"channel": channel, "ts": ts})]
        )
    )
    assert deleted.get("ok") is True, deleted
