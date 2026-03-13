"""Live integration tests for GeckoTerminal API -- hits the real API.

Run with:
    GECKOTERMINAL_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.geckoterminal.com"

pytestmark = pytest.mark.skipif(
    os.getenv("GECKOTERMINAL_RUN_LIVE_TESTS") != "1",
    reason="Set GECKOTERMINAL_RUN_LIVE_TESTS=1 to run live GeckoTerminal API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on connection errors or transient HTTP errors."""
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
    from geckoterminal_mcp.gen.geckoterminal.v1 import geckoterminal_pb2 as _pb2  # noqa: F401
    from geckoterminal_mcp.service import GeckoTerminalService

    base_url = (os.getenv("GECKOTERMINAL_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-geckoterminal-live", version="0.0.1"
    )
    servicer = GeckoTerminalService(base_url=base_url)
    srv.register(servicer, service_name="geckoterminal.v1.GeckoTerminalService")
    yield srv
    srv.stop()


# --- ListNetworks ---


class TestLiveListNetworks:
    def test_list_networks(self, live_server):
        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "ListNetworks",
        )
        assert "networks" in result
        networks = result["networks"]
        assert isinstance(networks, list)
        assert len(networks) > 0
        net = networks[0]
        assert "id" in net
        assert "name" in net


# --- GetTrendingPools ---


class TestLiveGetTrendingPools:
    def test_trending_all_networks(self, live_server):
        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "GetTrendingPools",
        )
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        pool = pools[0]
        assert "address" in pool
        assert "name" in pool

    def test_trending_specific_network(self, live_server):
        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "GetTrendingPools",
            {"network": "eth"},
        )
        assert "pools" in result
        assert len(result["pools"]) > 0


# --- GetPool ---


class TestLiveGetPool:
    def test_get_eth_pool(self, live_server):
        # First get trending to find a valid pool address
        trending = _cli_or_skip(
            live_server, "GeckoTerminalService", "GetTrendingPools",
            {"network": "eth"},
        )
        if not trending.get("pools"):
            pytest.skip("No trending pools on eth to test with")
        pool_address = trending["pools"][0]["address"]

        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "GetPool",
            {"network": "eth", "address": pool_address},
        )
        assert "pool" in result
        pool = result["pool"]
        assert pool["address"] == pool_address
        assert "name" in pool


# --- SearchPools ---


class TestLiveSearchPools:
    def test_search_weth(self, live_server):
        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "SearchPools",
            {"query": "WETH"},
        )
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        assert "address" in pools[0]

    def test_search_with_network(self, live_server):
        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "SearchPools",
            {"query": "USDC", "network": "eth"},
        )
        assert "pools" in result
        assert len(result["pools"]) > 0


# --- GetPoolOHLCV ---


class TestLiveGetPoolOHLCV:
    def test_ohlcv_hour(self, live_server):
        # Get a trending pool to use for OHLCV
        trending = _cli_or_skip(
            live_server, "GeckoTerminalService", "GetTrendingPools",
            {"network": "eth"},
        )
        if not trending.get("pools"):
            pytest.skip("No trending pools on eth to test with")
        pool_address = trending["pools"][0]["address"]

        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "GetPoolOHLCV",
            {
                "network": "eth",
                "pool_address": pool_address,
                "timeframe": "hour",
            },
        )
        assert "candles" in result
        candles = result["candles"]
        assert isinstance(candles, list)
        if len(candles) > 0:
            c = candles[0]
            assert "timestamp" in c
            assert "open" in c
            assert "high" in c
            assert "low" in c
            assert "close" in c
            assert "volume" in c


# --- GetNewPools ---


class TestLiveGetNewPools:
    def test_new_pools_eth(self, live_server):
        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "GetNewPools",
            {"network": "eth"},
        )
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        assert "address" in pools[0]


# --- GetTopPools ---


class TestLiveGetTopPools:
    def test_top_pools_uniswap(self, live_server):
        result = _cli_or_skip(
            live_server, "GeckoTerminalService", "GetTopPools",
            {"network": "eth", "dex": "uniswap_v3"},
        )
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        assert "address" in pools[0]
