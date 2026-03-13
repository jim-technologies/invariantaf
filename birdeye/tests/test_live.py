"""Live integration tests for Birdeye API -- hits the real API.

Run with:
    BIRDEYE_RUN_LIVE_TESTS=1 BIRDEYE_API_KEY=<key> uv run python -m pytest tests/test_live.py -v

Requires a valid Birdeye API key (free tier).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://public-api.birdeye.so"

# Well-known Solana token addresses
SOL_ADDRESS = "So11111111111111111111111111111111111111112"
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

pytestmark = pytest.mark.skipif(
    os.getenv("BIRDEYE_RUN_LIVE_TESTS") != "1" or not os.getenv("BIRDEYE_API_KEY"),
    reason="Set BIRDEYE_RUN_LIVE_TESTS=1 and BIRDEYE_API_KEY to run live Birdeye API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    import httpx
    args = [service, method]
    if params:
        args.extend(["-r", json.dumps(params)])
    try:
        return live_server._cli(args)
    except (httpx.ConnectTimeout, httpx.ConnectError, httpx.TimeoutException) as exc:
        pytest.skip(f"{method}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("401", "403", "429", "500", "502", "503", "Timeout", "timed out")):
            pytest.skip(f"{method}: {msg[:120]}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from birdeye_mcp.gen.birdeye.v1 import birdeye_pb2 as _birdeye_pb2  # noqa: F401
    from birdeye_mcp.service import BirdeyeService

    base_url = (os.getenv("BIRDEYE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = os.getenv("BIRDEYE_API_KEY", "")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-birdeye-live", version="0.0.1"
    )
    servicer = BirdeyeService(base_url=base_url, api_key=api_key)
    srv.register(servicer, service_name="birdeye.v1.BirdeyeService")
    yield srv
    srv.stop()


# --- GetTokenPrice ---


class TestLiveGetTokenPrice:
    def test_sol_price(self, live_server):
        result = _cli_or_skip(
            live_server, "BirdeyeService", "GetTokenPrice",
            {"address": SOL_ADDRESS},
        )
        assert result["value"] > 0

    def test_usdc_price(self, live_server):
        result = _cli_or_skip(
            live_server, "BirdeyeService", "GetTokenPrice",
            {"address": USDC_ADDRESS},
        )
        assert 0.99 < result["value"] < 1.01


# --- GetMultiPrice ---


class TestLiveGetMultiPrice:
    def test_multi_price(self, live_server):
        result = _cli_or_skip(
            live_server, "BirdeyeService", "GetMultiPrice",
            {"list_address": f"{SOL_ADDRESS},{USDC_ADDRESS}"},
        )
        assert "prices" in result
        prices = result["prices"]
        assert len(prices) >= 1


# --- GetTokenOverview ---


class TestLiveGetTokenOverview:
    def test_sol_overview(self, live_server):
        result = _cli_or_skip(
            live_server, "BirdeyeService", "GetTokenOverview",
            {"address": SOL_ADDRESS},
        )
        assert result["symbol"] == "SOL"
        assert result["price"] > 0
        assert result["liquidity"] > 0


# --- ListTokens ---


class TestLiveListTokens:
    def test_top_tokens_by_volume(self, live_server):
        result = _cli_or_skip(
            live_server, "BirdeyeService", "ListTokens",
            {"sort_by": "v24hUSD", "sort_type": "desc", "limit": 10},
        )
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        assert tokens[0]["price"] > 0


# --- GetOHLCV ---


class TestLiveGetOHLCV:
    def test_sol_ohlcv_1h(self, live_server):
        now = int(time.time())
        one_day_ago = now - (24 * 60 * 60)
        result = _cli_or_skip(
            live_server, "BirdeyeService", "GetOHLCV",
            {
                "address": SOL_ADDRESS,
                "type": "1H",
                "time_from": one_day_ago,
                "time_to": now,
            },
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0
        assert items[0]["o"] > 0
        assert items[0]["c"] > 0


# --- GetTradesToken ---


class TestLiveGetTradesToken:
    def test_sol_trades(self, live_server):
        result = _cli_or_skip(
            live_server, "BirdeyeService", "GetTradesToken",
            {"address": SOL_ADDRESS, "limit": 10},
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0


# --- SearchToken ---


class TestLiveSearchToken:
    def test_search_sol(self, live_server):
        result = _cli_or_skip(
            live_server, "BirdeyeService", "SearchToken",
            {"keyword": "SOL"},
        )
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0
