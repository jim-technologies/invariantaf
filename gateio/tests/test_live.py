"""Live integration tests for Gate.io API -- hits the real API.

Run with:
    GATEIO_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

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

DEFAULT_BASE_URL = "https://api.gateio.ws"

pytestmark = pytest.mark.skipif(
    os.getenv("GATEIO_RUN_LIVE_TESTS") != "1",
    reason="Set GATEIO_RUN_LIVE_TESTS=1 to run live Gate.io API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on 429/500/502/503 (rate limiting or transient errors)."""
    args = [service, method]
    if params:
        args.extend(["-r", json.dumps(params)])
    try:
        return live_server._cli(args)
    except Exception as exc:
        msg = str(exc)
        for code in ("429", "500", "502", "503"):
            if code in msg:
                pytest.skip(f"{method} returned HTTP {code}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from gateio_mcp.gen.gateio.v1 import gateio_pb2 as _gateio_pb2  # noqa: F401
    from gateio_mcp.service import GateioService

    base_url = (os.getenv("GATEIO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-gateio-live", version="0.0.1"
    )
    servicer = GateioService(base_url=base_url)
    srv.register(servicer, service_name="gateio.v1.GateioService")
    yield srv
    srv.stop()


# --- ListSpotTickers ---


class TestLiveListSpotTickers:
    def test_single_pair(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "ListSpotTickers",
            {"currency_pair": "BTC_USDT"},
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) == 1
        t = tickers[0]
        assert t["currency_pair"] == "BTC_USDT"
        assert t["last"] > 0
        assert t["high_24h"] > 0
        assert t["low_24h"] > 0

    def test_all_tickers(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "ListSpotTickers",
            {},
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) > 10


# --- GetSpotOrderbook ---


class TestLiveGetSpotOrderbook:
    def test_btc_usdt(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "GetSpotOrderbook",
            {"currency_pair": "BTC_USDT", "limit": 10},
        )
        assert "asks" in result
        assert "bids" in result
        assert len(result["asks"]) > 0
        assert len(result["bids"]) > 0
        assert result["asks"][0]["price"] > 0
        assert result["asks"][0]["amount"] > 0
        assert result["bids"][0]["price"] > 0
        assert result["bids"][0]["amount"] > 0

    def test_orderbook_with_limit(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "GetSpotOrderbook",
            {"currency_pair": "BTC_USDT", "limit": 5},
        )
        assert len(result["asks"]) <= 5
        assert len(result["bids"]) <= 5


# --- GetSpotCandlesticks ---


class TestLiveGetSpotCandlesticks:
    def test_btc_usdt_1h(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "GetSpotCandlesticks",
            {"currency_pair": "BTC_USDT", "interval": "1h", "limit": 10},
        )
        assert "candlesticks" in result
        candles = result["candlesticks"]
        assert isinstance(candles, list)
        assert len(candles) > 0
        c = candles[0]
        assert int(c["timestamp"]) > 0
        assert c["open"] > 0
        assert c["high"] > 0
        assert c["low"] > 0
        assert c["close"] > 0
        assert c["base_volume"] >= 0

    def test_eth_usdt_15m(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "GetSpotCandlesticks",
            {"currency_pair": "ETH_USDT", "interval": "15m", "limit": 5},
        )
        assert "candlesticks" in result
        assert len(result["candlesticks"]) > 0


# --- ListCurrencyPairs ---


class TestLiveListCurrencyPairs:
    def test_list_all(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "ListCurrencyPairs",
            {},
        )
        assert "currency_pairs" in result
        pairs = result["currency_pairs"]
        assert isinstance(pairs, list)
        assert len(pairs) > 10
        # Find BTC_USDT
        btc_usdt = [p for p in pairs if p["id"] == "BTC_USDT"]
        assert len(btc_usdt) == 1
        p = btc_usdt[0]
        assert p["base"] == "BTC"
        assert p["quote"] == "USDT"
        assert p["trade_status"] == "tradable"


# --- ListFuturesTickers ---


class TestLiveListFuturesTickers:
    def test_single_contract(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "ListFuturesTickers",
            {"contract": "BTC_USDT"},
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) == 1
        t = tickers[0]
        assert t["contract"] == "BTC_USDT"
        assert t["last"] > 0
        assert t["mark_price"] > 0
        assert t["index_price"] > 0

    def test_all_futures(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "ListFuturesTickers",
            {},
        )
        assert "tickers" in result
        assert len(result["tickers"]) > 5


# --- GetFuturesOrderbook ---


class TestLiveGetFuturesOrderbook:
    def test_btc_usdt(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "GetFuturesOrderbook",
            {"contract": "BTC_USDT", "limit": 10},
        )
        assert "asks" in result
        assert "bids" in result
        assert len(result["asks"]) > 0
        assert len(result["bids"]) > 0
        assert result["asks"][0]["price"] > 0
        assert result["asks"][0]["size"] > 0
        assert result["bids"][0]["price"] > 0
        assert result["bids"][0]["size"] > 0

    def test_orderbook_with_limit(self, live_server):
        result = _cli_or_skip(
            live_server, "GateioService", "GetFuturesOrderbook",
            {"contract": "BTC_USDT", "limit": 5},
        )
        assert len(result["asks"]) <= 5
        assert len(result["bids"]) <= 5
