"""Live integration tests for Bitget API -- hits the real API.

Run with:
    BITGET_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

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

DEFAULT_BASE_URL = "https://api.bitget.com"

pytestmark = pytest.mark.skipif(
    os.getenv("BITGET_RUN_LIVE_TESTS") != "1",
    reason="Set BITGET_RUN_LIVE_TESTS=1 to run live Bitget API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient HTTP or network errors."""
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
    from bitget_mcp.gen.bitget.v1 import bitget_pb2 as _bitget_pb2  # noqa: F401
    from bitget_mcp.service import BitgetService

    base_url = (os.getenv("BITGET_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-bitget-live", version="0.0.1"
    )
    servicer = BitgetService(base_url=base_url, timeout=10.0)
    srv.register(servicer, service_name="bitget.v1.BitgetService")
    yield srv
    srv.stop()


# --- ListSpotTickers ---


class TestLiveListSpotTickers:
    def test_list_all_spot_tickers(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "ListSpotTickers", {},
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        t = tickers[0]
        assert "symbol" in t
        assert "last_pr" in t

    def test_list_spot_tickers_btcusdt(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "ListSpotTickers",
            {"symbol": "BTCUSDT"},
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) >= 1


# --- GetSpotOrderbook ---


class TestLiveGetSpotOrderbook:
    def test_get_orderbook(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "GetSpotOrderbook",
            {"symbol": "BTCUSDT"},
        )
        assert "asks" in result
        assert "bids" in result
        assert len(result["asks"]) > 0
        assert len(result["bids"]) > 0
        assert "price" in result["asks"][0]
        assert "amount" in result["asks"][0]

    def test_get_orderbook_with_limit(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "GetSpotOrderbook",
            {"symbol": "BTCUSDT", "limit": 5},
        )
        assert len(result["asks"]) <= 5
        assert len(result["bids"]) <= 5


# --- GetSpotCandles ---


class TestLiveGetSpotCandles:
    def test_get_candles_1h(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "GetSpotCandles",
            {"symbol": "BTCUSDT", "granularity": "1h"},
        )
        assert "candles" in result
        candles = result["candles"]
        assert isinstance(candles, list)
        assert len(candles) > 0
        c = candles[0]
        assert "ts" in c
        assert "open" in c
        assert "high" in c
        assert "low" in c
        assert "close" in c

    def test_get_candles_with_limit(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "GetSpotCandles",
            {"symbol": "BTCUSDT", "granularity": "1h", "limit": 10},
        )
        assert "candles" in result
        assert len(result["candles"]) <= 10


# --- ListFuturesTickers ---


class TestLiveListFuturesTickers:
    def test_list_usdt_futures(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "ListFuturesTickers",
            {"productType": "USDT-FUTURES"},
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        t = tickers[0]
        assert "symbol" in t
        assert "last_pr" in t

    def test_list_usdt_futures_has_btc(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "ListFuturesTickers",
            {"productType": "USDT-FUTURES"},
        )
        tickers = result["tickers"]
        found = any("BTCUSDT" in t.get("symbol", "") for t in tickers)
        assert found


# --- GetFuturesOrderbook ---


class TestLiveGetFuturesOrderbook:
    def test_get_futures_orderbook(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "GetFuturesOrderbook",
            {"symbol": "BTCUSDT", "productType": "USDT-FUTURES"},
        )
        assert "asks" in result
        assert "bids" in result
        assert len(result["asks"]) > 0
        assert len(result["bids"]) > 0
        assert "price" in result["asks"][0]
        assert "amount" in result["asks"][0]

    def test_get_futures_orderbook_with_limit(self, live_server):
        result = _cli_or_skip(
            live_server, "BitgetService", "GetFuturesOrderbook",
            {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "limit": 5},
        )
        assert len(result["asks"]) <= 5
        assert len(result["bids"]) <= 5
