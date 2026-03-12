"""Live integration tests for DeFiLlama API -- hits the real API.

Run with:
    DEFILLAMA_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) DeFiLlama endpoints.
No API key or authentication is required.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("DEFILLAMA_RUN_LIVE_TESTS") != "1",
    reason="Set DEFILLAMA_RUN_LIVE_TESTS=1 to run live DeFiLlama API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from defillama_mcp.service import DefiLlamaService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-defillama-live", version="0.0.1"
    )
    servicer = DefiLlamaService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Shared fixtures for discovery ---


@pytest.fixture(scope="module")
def first_protocol_slug(live_server):
    """Discover a protocol slug for tests that need one."""
    result = live_server._cli(["DefiLlamaService", "GetProtocols"])
    protocols = result.get("protocols", [])
    assert protocols, "expected at least one protocol"
    slug = protocols[0].get("slug", "")
    assert slug, "first protocol has no slug"
    return slug


# --- Protocols ---


class TestLiveProtocols:
    def test_get_protocols(self, live_server):
        result = live_server._cli(["DefiLlamaService", "GetProtocols"])
        assert "protocols" in result
        protocols = result["protocols"]
        assert isinstance(protocols, list)
        assert len(protocols) > 0
        p = protocols[0]
        assert "name" in p
        assert "slug" in p

    def test_get_protocol_detail(self, live_server, first_protocol_slug):
        result = live_server._cli(
            [
                "DefiLlamaService",
                "GetProtocol",
                "-r",
                json.dumps({"slug": first_protocol_slug}),
            ]
        )
        assert "protocol" in result
        detail = result["protocol"]
        assert "name" in detail
        assert "chains" in detail

    def test_get_tvl(self, live_server, first_protocol_slug):
        result = live_server._cli(
            [
                "DefiLlamaService",
                "GetTVL",
                "-r",
                json.dumps({"slug": first_protocol_slug}),
            ]
        )
        assert "tvl" in result
        assert isinstance(result["tvl"], (int, float))


# --- Chains ---


class TestLiveChains:
    def test_get_chains(self, live_server):
        result = live_server._cli(["DefiLlamaService", "GetChains"])
        assert "chains" in result
        chains = result["chains"]
        assert isinstance(chains, list)
        assert len(chains) > 0
        c = chains[0]
        assert "name" in c


# --- Global TVL ---


class TestLiveGlobalTVL:
    def test_get_global_tvl(self, live_server):
        result = live_server._cli(["DefiLlamaService", "GetGlobalTVL"])
        key = "dataPoints" if "dataPoints" in result else "data_points"
        assert key in result
        data_points = result[key]
        assert isinstance(data_points, list)
        assert len(data_points) > 0
        dp = data_points[0]
        assert "date" in dp


# --- Stablecoins ---


class TestLiveStablecoins:
    def test_get_stablecoins(self, live_server):
        result = live_server._cli(["DefiLlamaService", "GetStablecoins"])
        assert "stablecoins" in result
        stablecoins = result["stablecoins"]
        assert isinstance(stablecoins, list)
        assert len(stablecoins) > 0
        s = stablecoins[0]
        assert "name" in s
        assert "symbol" in s

    def test_get_stablecoin_chains(self, live_server):
        result = live_server._cli(["DefiLlamaService", "GetStablecoinChains"])
        assert "chains" in result
        chains = result["chains"]
        assert isinstance(chains, list)
        assert len(chains) > 0
        c = chains[0]
        assert "name" in c


# --- Yield Pools ---


class TestLiveYieldPools:
    def test_get_yield_pools(self, live_server):
        result = live_server._cli(["DefiLlamaService", "GetYieldPools"])
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        p = pools[0]
        assert "chain" in p
        assert "project" in p


# --- DEX Volumes ---


class TestLiveDexVolumes:
    def test_get_dex_volumes(self, live_server):
        result = live_server._cli(["DefiLlamaService", "GetDexVolumes"])
        assert result.get("total24h") or result.get("total_24h")
        assert "protocols" in result
        protocols = result["protocols"]
        assert isinstance(protocols, list)
        assert len(protocols) > 0


# --- Fees ---


class TestLiveFees:
    def test_get_fees(self, live_server):
        result = live_server._cli(["DefiLlamaService", "GetFees"])
        assert result.get("total24h") or result.get("total_24h")
        assert "protocols" in result
        protocols = result["protocols"]
        assert isinstance(protocols, list)
        assert len(protocols) > 0
