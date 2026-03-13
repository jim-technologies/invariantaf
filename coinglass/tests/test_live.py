"""Live integration tests for CoinGlass API -- hits the real API.

Run with:
    COINGLASS_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Some endpoints may require a CoinGlass API key. Set COINGLASS_API_KEY
environment variable if authentication is needed.
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
    os.getenv("COINGLASS_RUN_LIVE_TESTS") != "1",
    reason="Set COINGLASS_RUN_LIVE_TESTS=1 to run live CoinGlass API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from coinglass_mcp.service import CoinGlassService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-coinglass-live", version="0.0.1"
    )
    servicer = CoinGlassService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- GetFundingRate ---


class TestLiveGetFundingRate:
    def test_returns_data(self, live_server):
        result = live_server._cli(["CoinGlassService", "GetFundingRate"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)

    def test_btc_funding_rate(self, live_server):
        result = live_server._cli(
            ["CoinGlassService", "GetFundingRate", "-r", json.dumps({"symbol": "BTC"})]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)


# --- GetOpenInterest ---


class TestLiveGetOpenInterest:
    def test_btc_open_interest(self, live_server):
        result = live_server._cli(
            ["CoinGlassService", "GetOpenInterest", "-r", json.dumps({"symbol": "BTC"})]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)


# --- GetLiquidation ---


class TestLiveGetLiquidation:
    def test_btc_liquidation(self, live_server):
        result = live_server._cli(
            ["CoinGlassService", "GetLiquidation", "-r", json.dumps({"symbol": "BTC", "timeType": "all"})]
        )
        assert "records" in result
        records = result["records"]
        assert isinstance(records, list)


# --- GetLongShortRatio ---


class TestLiveGetLongShortRatio:
    def test_btc_long_short(self, live_server):
        result = live_server._cli(
            ["CoinGlassService", "GetLongShortRatio", "-r", json.dumps({"symbol": "BTC", "timeType": "all"})]
        )
        assert "records" in result
        records = result["records"]
        assert isinstance(records, list)


# --- GetOIHistory ---


class TestLiveGetOIHistory:
    def test_btc_oi_history(self, live_server):
        result = live_server._cli(
            ["CoinGlassService", "GetOIHistory", "-r", json.dumps({"symbol": "BTC", "timeType": "all"})]
        )
        assert "records" in result
        records = result["records"]
        assert isinstance(records, list)
