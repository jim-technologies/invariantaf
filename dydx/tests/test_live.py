"""Live integration tests for dYdX v4 API -- hits the real API.

Run with:
    DYDX_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) dYdX v4 Indexer endpoints.
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
    os.getenv("DYDX_RUN_LIVE_TESTS") != "1",
    reason="Set DYDX_RUN_LIVE_TESTS=1 to run live dYdX API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from dydx_mcp.service import DydxService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-dydx-live", version="0.0.1"
    )
    servicer = DydxService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- ListMarkets ---


class TestLiveListMarkets:
    def test_list_markets(self, live_server):
        result = live_server._cli(["DydxService", "ListMarkets"])
        assert "markets" in result
        markets = result["markets"]
        assert isinstance(markets, list)
        assert len(markets) > 0, "expected at least one market"

    def test_list_markets_has_btc(self, live_server):
        result = live_server._cli(["DydxService", "ListMarkets"])
        tickers = [m["ticker"] for m in result["markets"]]
        assert "BTC-USD" in tickers, "expected BTC-USD market"

    def test_list_markets_has_eth(self, live_server):
        result = live_server._cli(["DydxService", "ListMarkets"])
        tickers = [m["ticker"] for m in result["markets"]]
        assert "ETH-USD" in tickers, "expected ETH-USD market"

    def test_market_has_oracle_price(self, live_server):
        result = live_server._cli(["DydxService", "ListMarkets"])
        btc = [m for m in result["markets"] if m["ticker"] == "BTC-USD"][0]
        key = "oraclePrice" if "oraclePrice" in btc else "oracle_price"
        assert key in btc
        assert float(btc[key]) > 0, "oracle price should be positive"

    def test_market_has_funding_rate(self, live_server):
        result = live_server._cli(["DydxService", "ListMarkets"])
        btc = [m for m in result["markets"] if m["ticker"] == "BTC-USD"][0]
        key = "nextFundingRate" if "nextFundingRate" in btc else "next_funding_rate"
        assert key in btc, "expected nextFundingRate field"

    def test_market_has_volume(self, live_server):
        result = live_server._cli(["DydxService", "ListMarkets"])
        btc = [m for m in result["markets"] if m["ticker"] == "BTC-USD"][0]
        key = "volume24h" if "volume24h" in btc else "volume_24h"
        assert key in btc, "expected volume_24h field"


# --- GetOrderbook ---


class TestLiveGetOrderbook:
    def test_get_orderbook(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetOrderbook", "-r", '{"ticker":"BTC-USD"}']
        )
        assert "bids" in result
        assert "asks" in result

    def test_orderbook_has_bids(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetOrderbook", "-r", '{"ticker":"BTC-USD"}']
        )
        assert len(result["bids"]) > 0, "expected at least one bid"

    def test_orderbook_has_asks(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetOrderbook", "-r", '{"ticker":"BTC-USD"}']
        )
        assert len(result["asks"]) > 0, "expected at least one ask"

    def test_orderbook_bid_has_price(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetOrderbook", "-r", '{"ticker":"BTC-USD"}']
        )
        bid = result["bids"][0]
        assert "price" in bid
        assert float(bid["price"]) > 0

    def test_orderbook_bid_has_size(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetOrderbook", "-r", '{"ticker":"BTC-USD"}']
        )
        bid = result["bids"][0]
        assert "size" in bid
        assert float(bid["size"]) > 0


# --- GetTrades ---


class TestLiveGetTrades:
    def test_get_trades(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetTrades", "-r", '{"ticker":"BTC-USD"}']
        )
        assert "trades" in result
        assert isinstance(result["trades"], list)
        assert len(result["trades"]) > 0, "expected at least one trade"

    def test_trade_has_price(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetTrades", "-r", '{"ticker":"BTC-USD"}']
        )
        trade = result["trades"][0]
        assert "price" in trade
        assert float(trade["price"]) > 0

    def test_trade_has_side(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetTrades", "-r", '{"ticker":"BTC-USD"}']
        )
        trade = result["trades"][0]
        assert "side" in trade

    def test_trade_has_size(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetTrades", "-r", '{"ticker":"BTC-USD"}']
        )
        trade = result["trades"][0]
        assert "size" in trade
        assert float(trade["size"]) > 0

    def test_trade_with_limit(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetTrades", "-r", json.dumps({"ticker": "BTC-USD", "limit": 5})]
        )
        assert len(result["trades"]) <= 5


# --- GetCandles ---


class TestLiveGetCandles:
    def test_get_candles_1hour(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetCandles", "-r", json.dumps({"ticker": "BTC-USD", "resolution": 5})]
        )
        assert "candles" in result
        assert isinstance(result["candles"], list)
        assert len(result["candles"]) > 0, "expected at least one candle"

    def test_candle_has_ohlcv(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetCandles", "-r", json.dumps({"ticker": "BTC-USD", "resolution": 5})]
        )
        candle = result["candles"][0]
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle

    def test_candle_has_volume(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetCandles", "-r", json.dumps({"ticker": "BTC-USD", "resolution": 5})]
        )
        candle = result["candles"][0]
        vol_key = "usdVolume" if "usdVolume" in candle else "usd_volume"
        assert vol_key in candle

    def test_candle_1min_resolution(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetCandles", "-r", json.dumps({"ticker": "BTC-USD", "resolution": 1})]
        )
        assert "candles" in result
        assert len(result["candles"]) > 0

    def test_candle_1day_resolution(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetCandles", "-r", json.dumps({"ticker": "BTC-USD", "resolution": 7})]
        )
        assert "candles" in result
        assert len(result["candles"]) > 0


# --- GetFundingRates ---


class TestLiveGetFundingRates:
    def test_get_funding_rates(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetFundingRates", "-r", '{"ticker":"BTC-USD"}']
        )
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        assert key in result
        rates = result[key]
        assert isinstance(rates, list)
        assert len(rates) > 0, "expected at least one funding rate"

    def test_funding_rate_has_rate(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetFundingRates", "-r", '{"ticker":"BTC-USD"}']
        )
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        fr = result[key][0]
        assert "rate" in fr

    def test_funding_rate_has_price(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetFundingRates", "-r", '{"ticker":"BTC-USD"}']
        )
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        fr = result[key][0]
        assert "price" in fr
        assert float(fr["price"]) > 0

    def test_funding_rate_has_effective_at(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetFundingRates", "-r", '{"ticker":"BTC-USD"}']
        )
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        fr = result[key][0]
        eff_key = "effectiveAt" if "effectiveAt" in fr else "effective_at"
        assert eff_key in fr

    def test_funding_rates_eth(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetFundingRates", "-r", '{"ticker":"ETH-USD"}']
        )
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        assert len(result[key]) > 0, "expected ETH-USD funding rates"

    def test_funding_rates_with_limit(self, live_server):
        result = live_server._cli(
            ["DydxService", "GetFundingRates", "-r", json.dumps({"ticker": "BTC-USD", "limit": 5})]
        )
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        assert len(result[key]) <= 5
