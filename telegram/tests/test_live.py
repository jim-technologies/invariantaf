"""Live integration tests for Telegram Bot API.

Required env vars:
    TELEGRAM_RUN_LIVE_TESTS=1
    TELEGRAM_BOT_TOKEN=...

Optional:
    TELEGRAM_LIVE_CHAT_ID -- chat ID for send/delete tests. If unset, only read tests run.
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
    os.getenv("TELEGRAM_RUN_LIVE_TESTS") != "1",
    reason="Set TELEGRAM_RUN_LIVE_TESTS=1 and TELEGRAM_BOT_TOKEN to run live tests",
)


@pytest.fixture(scope="module")
def live_server():
    from telegram_mcp.gen.telegram.v1 import telegram_pb2 as _telegram_pb2  # noqa: F401
    from telegram_mcp.service import TelegramService
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH)
    srv.register(TelegramService(), service_name="telegram.v1.TelegramService")
    yield srv
    asyncio.run(srv.stop())


def test_get_me(live_server):
    result = asyncio.run(live_server._cli(["TelegramService", "GetMe"]))
    assert isinstance(result, dict)
    assert result.get("is_bot") is True, result
    assert result.get("id"), result


def test_get_webhook_info(live_server):
    result = asyncio.run(live_server._cli(["TelegramService", "GetWebhookInfo"]))
    assert isinstance(result, dict)
    # The "url" field is always present in webhook info (empty string if no webhook).
    assert "url" in result, result


@pytest.mark.skipif(not os.getenv("TELEGRAM_LIVE_CHAT_ID"), reason="set TELEGRAM_LIVE_CHAT_ID")
def test_send_and_delete_message(live_server):
    import json

    chat_id = os.environ["TELEGRAM_LIVE_CHAT_ID"]
    sent = asyncio.run(
        live_server._cli(
            [
                "TelegramService",
                "SendMessage",
                "-r",
                json.dumps({"chat_id": chat_id, "text": "invariantaf live test"}),
            ]
        )
    )
    assert sent.get("message_id"), sent
    message_id = sent["message_id"]
    deleted = asyncio.run(
        live_server._cli(
            [
                "TelegramService",
                "DeleteMessage",
                "-r",
                json.dumps({"chat_id": chat_id, "message_id": message_id}),
            ]
        )
    )
    # DeleteMessage returns the boolean True on success.
    assert deleted in (True, {"value": True}), deleted
