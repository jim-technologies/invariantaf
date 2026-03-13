"""Live integration tests for Binance API -- hits the real API.

Run with:
    BINANCE_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Only PUBLIC market-data endpoints are tested (no auth required).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.binance.com"

pytestmark = pytest.mark.skipif(
    os.getenv("BINANCE_RUN_LIVE_TESTS") != "1",
    reason="Set BINANCE_RUN_LIVE_TESTS=1 to run live Binance API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from binance_mcp.gen.binance.v1 import binance_pb2 as _binance_pb2  # noqa: F401
    from binance_mcp.service import BinanceService

    base_url = (os.getenv("BINANCE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-binance-live", version="0.0.1"
    )
    servicer = BinanceService(base_url=base_url)
    srv.register(servicer, service_name="binance.v1.BinanceMarketService")
    yield srv
    srv.stop()


# --- GetPrice ---


class TestLiveGetPrice:
    def test_get_price_single(self, live_server):
        result = live_server._cli(
            ["BinanceMarketService", "GetPrice", "-r", json.dumps({"symbol": "BTCUSDT"})]
        )
        assert "prices" in result
        prices = result["prices"]
        assert len(prices) == 1
        assert prices[0]["symbol"] == "BTCUSDT"
        assert float(prices[0]["price"]) > 0

    def test_get_price_all(self, live_server):
        result = live_server._cli(["BinanceMarketService", "GetPrice"])
        assert "prices" in result
        prices = result["prices"]
        assert isinstance(prices, list)
        assert len(prices) > 10  # Binance has many trading pairs
        symbols = {p["symbol"] for p in prices}
        assert "BTCUSDT" in symbols


# --- Get24hrStats ---


class TestLiveGet24hrStats:
    def test_get_24hr_stats(self, live_server):
        result = live_server._cli(
            ["BinanceMarketService", "Get24hrStats", "-r", json.dumps({"symbol": "BTCUSDT"})]
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        t = tickers[0]
        assert t["symbol"] == "BTCUSDT"
        assert float(t["lastPrice"]) > 0
        assert "priceChange" in t
        assert "volume" in t


# --- GetOrderbook ---


class TestLiveGetOrderbook:
    def test_get_orderbook(self, live_server):
        result = live_server._cli(
            [
                "BinanceMarketService",
                "GetOrderbook",
                "-r",
                json.dumps({"symbol": "BTCUSDT", "limit": 5}),
            ]
        )
        assert "bids" in result
        assert "asks" in result
        assert len(result["bids"]) > 0
        assert len(result["asks"]) > 0
        # Each level has price and quantity
        bid = result["bids"][0]
        assert "price" in bid
        assert "quantity" in bid
        assert float(bid["price"]) > 0


# --- GetKlines ---


class TestLiveGetKlines:
    def test_get_klines(self, live_server):
        result = live_server._cli(
            [
                "BinanceMarketService",
                "GetKlines",
                "-r",
                json.dumps({"symbol": "BTCUSDT", "interval": "1h", "limit": 5}),
            ]
        )
        assert "klines" in result
        klines = result["klines"]
        assert isinstance(klines, list)
        assert len(klines) > 0
        k = klines[0]
        assert "open" in k
        assert "high" in k
        assert "low" in k
        assert "close" in k
        assert "volume" in k
        assert float(k["open"]) > 0


# --- GetTrades ---


class TestLiveGetTrades:
    def test_get_trades(self, live_server):
        result = live_server._cli(
            [
                "BinanceMarketService",
                "GetTrades",
                "-r",
                json.dumps({"symbol": "BTCUSDT", "limit": 5}),
            ]
        )
        assert "trades" in result
        trades = result["trades"]
        assert isinstance(trades, list)
        assert len(trades) > 0
        t = trades[0]
        assert "price" in t
        assert "qty" in t
        assert float(t["price"]) > 0


# --- GetExchangeInfo ---


class TestLiveGetExchangeInfo:
    def test_get_exchange_info_single(self, live_server):
        result = live_server._cli(
            [
                "BinanceMarketService",
                "GetExchangeInfo",
                "-r",
                json.dumps({"symbol": "BTCUSDT"}),
            ]
        )
        assert result["timezone"] == "UTC"
        assert "symbols" in result
        symbols = result["symbols"]
        assert len(symbols) >= 1
        sym = symbols[0]
        assert sym["symbol"] == "BTCUSDT"
        assert sym["baseAsset"] == "BTC"
        assert sym["quoteAsset"] == "USDT"
        assert sym["status"] == "TRADING"

    def test_get_exchange_info_has_rate_limits(self, live_server):
        result = live_server._cli(
            [
                "BinanceMarketService",
                "GetExchangeInfo",
                "-r",
                json.dumps({"symbol": "BTCUSDT"}),
            ]
        )
        assert "rateLimits" in result
        assert len(result["rateLimits"]) > 0


# --- GetAvgPrice ---


class TestLiveGetAvgPrice:
    def test_get_avg_price(self, live_server):
        result = live_server._cli(
            ["BinanceMarketService", "GetAvgPrice", "-r", json.dumps({"symbol": "BTCUSDT"})]
        )
        assert "price" in result
        assert float(result["price"]) > 0
        assert result["mins"] > 0


# --- GetBookTicker ---


class TestLiveGetBookTicker:
    def test_get_book_ticker_single(self, live_server):
        result = live_server._cli(
            ["BinanceMarketService", "GetBookTicker", "-r", json.dumps({"symbol": "BTCUSDT"})]
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        t = tickers[0]
        assert t["symbol"] == "BTCUSDT"
        assert float(t["bidPrice"]) > 0
        assert float(t["askPrice"]) > 0

    def test_get_book_ticker_all(self, live_server):
        result = live_server._cli(["BinanceMarketService", "GetBookTicker"])
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) > 10
