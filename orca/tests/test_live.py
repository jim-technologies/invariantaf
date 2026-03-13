"""Live integration tests for Orca API -- hits the real API.

Run with:
    ORCA_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Orca endpoints.
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
    os.getenv("ORCA_RUN_LIVE_TESTS") != "1",
    reason="Set ORCA_RUN_LIVE_TESTS=1 to run live Orca API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from orca_mcp.service import OrcaService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-orca-live", version="0.0.1"
    )
    servicer = OrcaService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Shared fixtures for discovery ---


@pytest.fixture(scope="module")
def first_pool_address(live_server):
    """Discover a pool address for tests that need one."""
    result = live_server._cli(["OrcaService", "ListPools", "-r", '{"limit": 1}'])
    pools = result.get("pools", [])
    assert pools, "expected at least one pool"
    address = pools[0].get("address", "")
    assert address, "first pool has no address"
    return address


@pytest.fixture(scope="module")
def first_token_address(live_server):
    """Discover a token mint address for tests that need one."""
    result = live_server._cli(["OrcaService", "ListTokens", "-r", '{"limit": 1}'])
    tokens = result.get("tokens", [])
    assert tokens, "expected at least one token"
    address = tokens[0].get("address", "")
    assert address, "first token has no address"
    return address


# --- Pools ---


class TestLivePools:
    def test_list_pools(self, live_server):
        result = live_server._cli(["OrcaService", "ListPools", "-r", '{"limit": 5}'])
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        p = pools[0]
        assert "address" in p
        assert "tokenA" in p or "token_a" in p

    def test_get_pool(self, live_server, first_pool_address):
        result = live_server._cli(
            [
                "OrcaService",
                "GetPool",
                "-r",
                json.dumps({"address": first_pool_address}),
            ]
        )
        assert "pool" in result
        pool = result["pool"]
        assert "address" in pool

    def test_search_pools(self, live_server):
        result = live_server._cli(
            [
                "OrcaService",
                "SearchPools",
                "-r",
                json.dumps({"query": "SOL-USDC", "limit": 3}),
            ]
        )
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0


# --- Tokens ---


class TestLiveTokens:
    def test_list_tokens(self, live_server):
        result = live_server._cli(["OrcaService", "ListTokens", "-r", '{"limit": 5}'])
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        t = tokens[0]
        assert "address" in t

    def test_get_token(self, live_server, first_token_address):
        result = live_server._cli(
            [
                "OrcaService",
                "GetToken",
                "-r",
                json.dumps({"mintAddress": first_token_address}),
            ]
        )
        assert "token" in result
        token = result["token"]
        assert "address" in token

    def test_search_tokens(self, live_server):
        result = live_server._cli(
            [
                "OrcaService",
                "SearchTokens",
                "-r",
                json.dumps({"query": "ORCA", "limit": 3}),
            ]
        )
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0


# --- Protocol ---


class TestLiveProtocol:
    def test_get_protocol_stats(self, live_server):
        result = live_server._cli(["OrcaService", "GetProtocolStats"])
        assert "tvl" in result
        assert result.get("volume24hUsdc") or result.get("volume_24h_usdc")

    def test_get_protocol_token(self, live_server):
        result = live_server._cli(["OrcaService", "GetProtocolToken"])
        assert result.get("symbol") == "ORCA"
        assert result.get("name") == "Orca"
        assert "price" in result


# --- Locked Liquidity ---


class TestLiveLockedLiquidity:
    def test_get_locked_liquidity(self, live_server, first_pool_address):
        result = live_server._cli(
            [
                "OrcaService",
                "GetLockedLiquidity",
                "-r",
                json.dumps({"address": first_pool_address}),
            ]
        )
        # entries may be empty for some pools — just verify the shape
        assert isinstance(result.get("entries", []), list)
