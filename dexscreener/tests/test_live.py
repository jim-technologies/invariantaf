"""Live integration tests for DexScreener API -- hits the real API.

Run with:
    DEXSCREENER_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.dexscreener.com"

pytestmark = pytest.mark.skipif(
    os.getenv("DEXSCREENER_RUN_LIVE_TESTS") != "1",
    reason="Set DEXSCREENER_RUN_LIVE_TESTS=1 to run live DexScreener API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on connection errors or transient failures."""
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
        if any(code in msg for code in ("429", "500", "502", "503", "Timeout", "timed out")):
            pytest.skip(f"{method}: {msg[:120]}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from dexscreener_mcp.gen.dexscreener.v1 import dexscreener_pb2 as _dexscreener_pb2  # noqa: F401
    from dexscreener_mcp.service import DexScreenerService

    base_url = (os.getenv("DEXSCREENER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-dexscreener-live", version="0.0.1"
    )
    servicer = DexScreenerService(base_url=base_url)
    srv.register(servicer, service_name="dexscreener.v1.DexScreenerService")
    yield srv
    srv.stop()


# --- SearchPairs ---


class TestLiveSearchPairs:
    def test_search_weth(self, live_server):
        result = _cli_or_skip(
            live_server, "DexScreenerService", "SearchPairs",
            {"query": "WETH"},
        )
        assert "pairs" in result
        pairs = result["pairs"]
        assert isinstance(pairs, list)
        assert len(pairs) > 0
        pair = pairs[0]
        assert "chain_id" in pair
        assert "base_token" in pair
        assert "quote_token" in pair
        assert "price_usd" in pair

    def test_search_usdc(self, live_server):
        result = _cli_or_skip(
            live_server, "DexScreenerService", "SearchPairs",
            {"query": "USDC"},
        )
        assert "pairs" in result
        assert len(result["pairs"]) > 0


# --- GetTokenPairs ---


class TestLiveGetTokenPairs:
    def test_get_weth_pairs(self, live_server):
        result = _cli_or_skip(
            live_server, "DexScreenerService", "GetTokenPairs",
            {"token_addresses": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"},
        )
        assert "pairs" in result
        pairs = result["pairs"]
        assert isinstance(pairs, list)
        assert len(pairs) > 0
        pair = pairs[0]
        assert "chain_id" in pair
        assert "volume" in pair
        assert "liquidity" in pair


# --- GetLatestTokenProfiles ---


class TestLiveGetLatestTokenProfiles:
    def test_get_profiles(self, live_server):
        result = _cli_or_skip(
            live_server, "DexScreenerService", "GetLatestTokenProfiles",
        )
        assert "profiles" in result
        profiles = result["profiles"]
        assert isinstance(profiles, list)
        assert len(profiles) > 0
        p = profiles[0]
        assert "chain_id" in p
        assert "token_address" in p


# --- GetLatestBoostedTokens ---


class TestLiveGetLatestBoostedTokens:
    def test_get_latest_boosted(self, live_server):
        result = _cli_or_skip(
            live_server, "DexScreenerService", "GetLatestBoostedTokens",
        )
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        t = tokens[0]
        assert "chain_id" in t
        assert "token_address" in t


# --- GetTopBoostedTokens ---


class TestLiveGetTopBoostedTokens:
    def test_get_top_boosted(self, live_server):
        result = _cli_or_skip(
            live_server, "DexScreenerService", "GetTopBoostedTokens",
        )
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        t = tokens[0]
        assert "chain_id" in t
        assert "token_address" in t
