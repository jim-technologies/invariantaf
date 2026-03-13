"""Live integration tests for Curve Finance API -- hits the real API.

Run with:
    CURVE_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Curve Finance endpoints.
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
    os.getenv("CURVE_RUN_LIVE_TESTS") != "1",
    reason="Set CURVE_RUN_LIVE_TESTS=1 to run live Curve Finance API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from curve_mcp.service import CurveService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-curve-live", version="0.0.1"
    )
    servicer = CurveService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Pools ---


class TestLivePools:
    def test_get_pools_ethereum_main(self, live_server):
        result = live_server._cli(
            [
                "CurveService",
                "GetPools",
                "-r",
                json.dumps({"blockchainId": "ethereum", "registryId": "main"}),
            ]
        )
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        p = pools[0]
        assert "address" in p
        assert "name" in p
        assert "coins" in p

    def test_get_pools_defaults(self, live_server):
        result = live_server._cli(["CurveService", "GetPools"])
        assert "pools" in result
        assert len(result["pools"]) > 0

    def test_pool_has_coins(self, live_server):
        result = live_server._cli(["CurveService", "GetPools"])
        pools = result["pools"]
        # Find a pool with coins
        pool_with_coins = None
        for p in pools:
            if p.get("coins"):
                pool_with_coins = p
                break
        assert pool_with_coins is not None, "expected at least one pool with coins"
        coin = pool_with_coins["coins"][0]
        assert "symbol" in coin
        assert "address" in coin


# --- APYs ---


class TestLiveApys:
    def test_get_apys(self, live_server):
        result = live_server._cli(["CurveService", "GetApys"])
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        p = pools[0]
        assert "address" in p
        assert "type" in p


# --- Volumes ---


class TestLiveVolumes:
    def test_get_volumes(self, live_server):
        result = live_server._cli(["CurveService", "GetVolumes"])
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        p = pools[0]
        assert "address" in p


# --- TVL ---


class TestLiveTVL:
    def test_get_tvl(self, live_server):
        result = live_server._cli(["CurveService", "GetTVL"])
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0


# --- Factory TVL ---


class TestLiveFactoryTVL:
    def test_get_factory_tvl(self, live_server):
        result = live_server._cli(["CurveService", "GetFactoryTVL"])
        key = "factoryBalances" if "factoryBalances" in result else "factory_balances"
        assert key in result
        assert isinstance(result[key], (int, float))
        assert result[key] > 0


# --- Weekly Fees ---


class TestLiveWeeklyFees:
    def test_get_weekly_fees(self, live_server):
        result = live_server._cli(["CurveService", "GetWeeklyFees"])
        key = "weeklyFees" if "weeklyFees" in result else "weekly_fees"
        assert key in result
        fees = result[key]
        assert isinstance(fees, list)
        assert len(fees) > 0
        entry = fees[0]
        assert "date" in entry
        assert "ts" in entry

    def test_total_fees(self, live_server):
        result = live_server._cli(["CurveService", "GetWeeklyFees"])
        key = "totalFees" if "totalFees" in result else "total_fees"
        assert key in result
        assert isinstance(result[key], (int, float))
        assert result[key] > 0


# --- ETH Price ---


class TestLiveETHPrice:
    def test_get_eth_price(self, live_server):
        result = live_server._cli(["CurveService", "GetETHPrice"])
        assert "price" in result
        assert isinstance(result["price"], (int, float))
        assert result["price"] > 0


# --- Subgraph Data ---


class TestLiveSubgraphData:
    def test_get_subgraph_data(self, live_server):
        result = live_server._cli(
            [
                "CurveService",
                "GetSubgraphData",
                "-r",
                json.dumps({"blockchainId": "ethereum"}),
            ]
        )
        assert "pools" in result
        pools = result["pools"]
        assert isinstance(pools, list)
        assert len(pools) > 0
        p = pools[0]
        assert "address" in p
        assert "type" in p
