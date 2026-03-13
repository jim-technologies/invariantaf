"""Live integration tests for Morpho API -- hits the real API.

Run with:
    MORPHO_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit the public (unauthenticated) Morpho GraphQL endpoint.
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
    os.getenv("MORPHO_RUN_LIVE_TESTS") != "1",
    reason="Set MORPHO_RUN_LIVE_TESTS=1 to run live Morpho API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from morpho_mcp.service import MorphoService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-morpho-live", version="0.0.1"
    )
    servicer = MorphoService()
    srv.register(servicer)
    yield srv
    srv.stop()


class TestLiveMarkets:
    def test_list_markets(self, live_server):
        result = live_server._cli(["MorphoService", "ListMarkets"])
        assert "markets" in result
        markets = result["markets"]
        assert isinstance(markets, list)
        assert len(markets) > 0
        m = markets[0]
        assert "unique_key" in m or "uniqueKey" in m

    def test_list_markets_with_pagination(self, live_server):
        result = live_server._cli(
            ["MorphoService", "ListMarkets", "-r", json.dumps({"first": 3})]
        )
        markets = result.get("markets", [])
        assert len(markets) <= 3


class TestLiveVaults:
    def test_list_vaults(self, live_server):
        result = live_server._cli(["MorphoService", "ListVaults"])
        assert "vaults" in result
        vaults = result["vaults"]
        assert isinstance(vaults, list)
        assert len(vaults) > 0
        v = vaults[0]
        assert "address" in v
        assert "name" in v

    def test_list_vaults_with_pagination(self, live_server):
        result = live_server._cli(
            ["MorphoService", "ListVaults", "-r", json.dumps({"first": 2})]
        )
        vaults = result.get("vaults", [])
        assert len(vaults) <= 2


class TestLiveMarketPositions:
    def test_list_positions_empty_user(self, live_server):
        """A random address likely has no positions -- should return empty list."""
        result = live_server._cli(
            [
                "MorphoService",
                "ListMarketPositions",
                "-r",
                json.dumps({"user_address": "0x0000000000000000000000000000000000000001"}),
            ]
        )
        assert "positions" in result
        assert isinstance(result["positions"], list)
