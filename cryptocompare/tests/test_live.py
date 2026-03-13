"""Live integration tests for CryptoCompare API -- hits the real API.

Run with:
    CRYPTOCOMPARE_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
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

DEFAULT_BASE_URL = "https://min-api.cryptocompare.com"

pytestmark = pytest.mark.skipif(
    os.getenv("CRYPTOCOMPARE_RUN_LIVE_TESTS") != "1",
    reason="Set CRYPTOCOMPARE_RUN_LIVE_TESTS=1 to run live CryptoCompare API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on 429/500/502/503 (rate limiting or transient errors)."""
    args = [service, method]
    if params:
        args.extend(["-r", json.dumps(params)])
    try:
        result = live_server._cli(args)
    except Exception as exc:
        msg = str(exc)
        for code in ("429", "500", "502", "503"):
            if code in msg:
                pytest.skip(f"{method} returned HTTP {code}")
        raise
    if result == {}:
        pytest.skip(f"{method} returned empty response (likely rate limited)")
    return result


@pytest.fixture(autouse=True)
def _rate_limit_delay():
    """Small delay between tests to avoid CryptoCompare free-tier rate limiting."""
    yield
    time.sleep(0.3)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from cryptocompare_mcp.gen.cryptocompare.v1 import cryptocompare_pb2 as _cryptocompare_pb2  # noqa: F401
    from cryptocompare_mcp.service import CryptoCompareService

    base_url = (os.getenv("CRYPTOCOMPARE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-cryptocompare-live", version="0.0.1"
    )
    servicer = CryptoCompareService(base_url=base_url)
    srv.register(servicer, service_name="cryptocompare.v1.CryptoCompareService")
    yield srv
    srv.stop()


# --- GetPrice ---


class TestLiveGetPrice:
    def test_btc_usd(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoCompareService", "GetPrice",
            {"fsym": "BTC", "tsyms": "USD"},
        )
        assert "prices" in result
        assert result["prices"]["USD"] > 0

    def test_btc_multi_currency(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoCompareService", "GetPrice",
            {"fsym": "BTC", "tsyms": "USD,EUR,GBP"},
        )
        assert "prices" in result
        prices = result["prices"]
        assert prices["USD"] > 0
        assert prices["EUR"] > 0
        assert prices["GBP"] > 0


# --- GetMultiPrice ---


class TestLiveGetMultiPrice:
    def test_btc_eth_multi(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoCompareService", "GetMultiPrice",
            {"fsyms": "BTC,ETH", "tsyms": "USD,EUR"},
        )
        assert "rows" in result
        rows = result["rows"]
        assert len(rows) == 2
        symbols = {r["from_symbol"] for r in rows}
        assert "BTC" in symbols
        assert "ETH" in symbols
        for row in rows:
            assert row["prices"]["USD"] > 0


# --- GetFullPrice ---


class TestLiveGetFullPrice:
    def test_btc_full(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoCompareService", "GetFullPrice",
            {"fsyms": "BTC", "tsyms": "USD"},
        )
        assert "coins" in result
        coins = result["coins"]
        assert len(coins) >= 1
        btc = coins[0]
        assert btc["from_symbol"] == "BTC"
        assert btc["to_symbol"] == "USD"
        assert btc["price"] > 0
        assert btc["market_cap"] > 0


# --- GetHistoHour ---


class TestLiveGetHistoHour:
    def test_btc_hourly(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoCompareService", "GetHistoHour",
            {"fsym": "BTC", "tsym": "USD", "limit": 5},
        )
        assert "candles" in result
        candles = result["candles"]
        assert len(candles) > 0
        c = candles[0]
        assert "time" in c
        assert "open" in c
        assert "high" in c
        assert "low" in c
        assert "close" in c
        assert c["close"] > 0


# --- GetHistoDay ---


class TestLiveGetHistoDay:
    def test_btc_daily(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoCompareService", "GetHistoDay",
            {"fsym": "BTC", "tsym": "USD", "limit": 5},
        )
        assert "candles" in result
        candles = result["candles"]
        assert len(candles) > 0
        c = candles[0]
        assert "time" in c
        assert c["close"] > 0


# --- GetTopByVolume ---


class TestLiveGetTopByVolume:
    def test_top_coins_usd(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoCompareService", "GetTopByVolume",
            {"tsym": "USD", "limit": 5},
        )
        assert "coins" in result
        coins = result["coins"]
        assert len(coins) > 0
        c = coins[0]
        assert "name" in c
        assert "symbol" in c
        assert c["price"] > 0
