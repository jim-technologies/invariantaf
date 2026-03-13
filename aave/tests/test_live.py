"""Live integration tests for Aave v3 GraphQL API.

Run with:
    AAVE_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

No API key required -- Aave v3 GraphQL is public.
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
    os.getenv("AAVE_RUN_LIVE_TESTS") != "1",
    reason="Set AAVE_RUN_LIVE_TESTS=1 to run live Aave API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from aave_mcp.service import AaveService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-aave-live", version="0.0.1"
    )
    servicer = AaveService()
    srv.register(servicer)
    yield srv
    srv.stop()


def _cli_or_skip(live_server, args):
    try:
        return live_server._cli(args)
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("404", "429", "500", "502", "503", "Timeout")):
            pytest.skip(f"Aave API unavailable: {msg[:120]}")
        raise


class TestLiveGetMarkets:
    def test_ethereum_markets(self, live_server):
        result = _cli_or_skip(
            live_server,
            ["AaveService", "GetMarkets", "-r", json.dumps({"chain_ids": [1]})],
        )
        assert "markets" in result
        markets = result["markets"]
        assert len(markets) > 0
        m = markets[0]
        assert "name" in m
        assert "reserves" in m
        assert len(m["reserves"]) > 0

    def test_reserve_has_apy(self, live_server):
        result = _cli_or_skip(
            live_server,
            ["AaveService", "GetMarkets", "-r", json.dumps({"chain_ids": [1]})],
        )
        r = result["markets"][0]["reserves"][0]
        assert "symbol" in r
        assert "supply_apy" in r
        assert "usd_exchange_rate" in r

    def test_multi_chain(self, live_server):
        result = _cli_or_skip(
            live_server,
            ["AaveService", "GetMarkets", "-r", json.dumps({"chain_ids": [1, 42161]})],
        )
        markets = result["markets"]
        assert len(markets) >= 2
