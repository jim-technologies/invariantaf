"""Live integration tests for Kraken API -- hits the real API.

Run with:
    KRAKEN_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Only PUBLIC endpoints are tested (no auth required):
  - Spot: GetServerTime, GetSystemStatus, GetTradableAssetPairs, GetTickerInformation, GetOrderBook
  - Futures: GetInstruments, GetTickers, GetOrderbook

Private endpoints (balance, orders, fills) are skipped.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_SPOT_BASE_URL = "https://api.kraken.com/0"
DEFAULT_FUTURES_BASE_URL = "https://futures.kraken.com/derivatives/api/v3"

pytestmark = pytest.mark.skipif(
    os.getenv("KRAKEN_RUN_LIVE_TESTS") != "1",
    reason="Set KRAKEN_RUN_LIVE_TESTS=1 to run live Kraken API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from kraken_mcp.gen.kraken.v1 import kraken_pb2 as _kraken_pb2  # noqa: F401
    from kraken_mcp.service import KrakenService

    spot_base = (os.getenv("KRAKEN_SPOT_BASE_URL") or DEFAULT_SPOT_BASE_URL).rstrip("/")
    futures_base = (os.getenv("KRAKEN_FUTURES_BASE_URL") or DEFAULT_FUTURES_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-kraken-live", version="0.0.1"
    )
    servicer = KrakenService(spot_base_url=spot_base, futures_base_url=futures_base)
    srv.register(servicer, service_name="kraken.v1.KrakenSpotService")
    srv.register(servicer, service_name="kraken.v1.KrakenFuturesService")
    yield srv
    srv.stop()


# --- Shared fixtures for discovery ---


@pytest.fixture(scope="module")
def spot_pair(live_server):
    """Discover a valid spot trading pair."""
    result = live_server._cli(
        ["KrakenSpotService", "GetTradableAssetPairs", "-r", json.dumps({"pair": "XBTUSD"})]
    )
    pairs = result.get("result", {})
    if pairs:
        return next(iter(pairs.keys()))
    pytest.skip("no spot pairs found")


@pytest.fixture(scope="module")
def futures_symbol(live_server):
    """Discover a valid futures instrument symbol."""
    result = live_server._cli(["KrakenFuturesService", "GetInstruments"])
    instruments = result.get("instruments", [])
    for inst in instruments:
        if inst.get("tradeable") and inst.get("symbol", "").startswith("PF_"):
            return inst["symbol"]
    if instruments:
        return instruments[0].get("symbol", "")
    pytest.skip("no futures instruments found")


# --- Spot Public ---


class TestLiveSpotPublic:
    def test_get_server_time(self, live_server):
        result = live_server._cli(["KrakenSpotService", "GetServerTime"])
        assert "result" in result
        assert result.get("error") == [] or "error" not in result
        res = result["result"]
        assert "unixtime" in res

    def test_get_system_status(self, live_server):
        result = live_server._cli(["KrakenSpotService", "GetSystemStatus"])
        assert "result" in result
        res = result["result"]
        assert "status" in res
        assert res["status"] in ("online", "maintenance", "cancel_only", "post_only")

    def test_get_tradable_asset_pairs(self, live_server):
        result = live_server._cli(
            [
                "KrakenSpotService",
                "GetTradableAssetPairs",
                "-r",
                json.dumps({"pair": "XBTUSD"}),
            ]
        )
        assert "result" in result
        pairs = result["result"]
        assert isinstance(pairs, dict)
        assert len(pairs) > 0
        first_pair = next(iter(pairs.values()))
        assert "base" in first_pair
        assert "quote" in first_pair

    def test_get_ticker_information(self, live_server, spot_pair):
        result = live_server._cli(
            [
                "KrakenSpotService",
                "GetTickerInformation",
                "-r",
                json.dumps({"pair": spot_pair}),
            ]
        )
        assert "result" in result
        tickers = result["result"]
        assert isinstance(tickers, dict)
        assert len(tickers) > 0
        first_ticker = next(iter(tickers.values()))
        # 'a' is ask, 'b' is bid
        assert "a" in first_ticker
        assert "b" in first_ticker

    def test_get_order_book(self, live_server, spot_pair):
        result = live_server._cli(
            [
                "KrakenSpotService",
                "GetOrderBook",
                "-r",
                json.dumps({"pair": spot_pair, "count": 5}),
            ]
        )
        assert "result" in result
        books = result["result"]
        assert isinstance(books, dict)
        assert len(books) > 0
        first_book = next(iter(books.values()))
        assert "asks" in first_book
        assert "bids" in first_book
        assert len(first_book["asks"]) > 0
        assert len(first_book["bids"]) > 0


# --- Futures Public ---


class TestLiveFuturesPublic:
    def test_get_instruments(self, live_server):
        result = live_server._cli(["KrakenFuturesService", "GetInstruments"])
        assert "instruments" in result
        instruments = result["instruments"]
        assert isinstance(instruments, list)
        assert len(instruments) > 0
        inst = instruments[0]
        assert "symbol" in inst

    def test_get_tickers(self, live_server):
        result = live_server._cli(["KrakenFuturesService", "GetTickers"])
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        t = tickers[0]
        assert "symbol" in t

    def test_get_tickers_with_symbol(self, live_server, futures_symbol):
        result = live_server._cli(
            [
                "KrakenFuturesService",
                "GetTickers",
                "-r",
                json.dumps({"symbol": [futures_symbol]}),
            ]
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) > 0

    def test_get_orderbook(self, live_server, futures_symbol):
        result = live_server._cli(
            [
                "KrakenFuturesService",
                "GetOrderbook",
                "-r",
                json.dumps({"symbol": futures_symbol}),
            ]
        )
        assert "order_book" in result or "orderBook" in result
        ob = result.get("order_book") or result.get("orderBook", {})
        assert "asks" in ob
        assert "bids" in ob
        assert len(ob["asks"]) > 0 or len(ob["bids"]) > 0
