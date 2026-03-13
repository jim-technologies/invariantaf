"""Integration tests -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "BinanceMarketService.GetPrice",
    "BinanceMarketService.Get24hrStats",
    "BinanceMarketService.GetOrderbook",
    "BinanceMarketService.GetKlines",
    "BinanceMarketService.GetTrades",
    "BinanceMarketService.GetExchangeInfo",
    "BinanceMarketService.GetAvgPrice",
    "BinanceMarketService.GetBookTicker",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 8

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_get_price_single(self, server):
        result = server._cli(
            ["BinanceMarketService", "GetPrice", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert "prices" in result
        prices = result["prices"]
        assert len(prices) == 1
        assert prices[0]["symbol"] == "BTCUSDT"
        assert prices[0]["price"] == "50000.00"

    def test_get_price_all(self, server):
        result = server._cli(["BinanceMarketService", "GetPrice"])
        assert "prices" in result
        prices = result["prices"]
        assert len(prices) == 2
        symbols = {p["symbol"] for p in prices}
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols

    def test_get_24hr_stats(self, server):
        result = server._cli(
            ["BinanceMarketService", "Get24hrStats", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        t = tickers[0]
        assert t["symbol"] == "BTCUSDT"
        assert t["last_price"] == "50000.00"
        assert t["price_change"] == "100.00"
        assert t["count"] == "1000"

    def test_get_orderbook(self, server):
        result = server._cli(
            ["BinanceMarketService", "GetOrderbook", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert result["last_update_id"] == "123456"
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2
        assert result["bids"][0]["price"] == "49999.00"
        assert result["asks"][0]["quantity"] == "1.0"

    def test_get_klines(self, server):
        result = server._cli(
            [
                "BinanceMarketService",
                "GetKlines",
                "-r",
                json.dumps({"symbol": "BTCUSDT", "interval": "1h", "limit": 2}),
            ]
        )
        assert "klines" in result
        klines = result["klines"]
        assert len(klines) == 2
        assert klines[0]["open"] == "49900.00"
        assert klines[0]["close"] == "50000.00"
        assert klines[0]["volume"] == "1000.00"

    def test_get_trades(self, server):
        result = server._cli(
            ["BinanceMarketService", "GetTrades", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert "trades" in result
        trades = result["trades"]
        assert len(trades) == 2
        assert trades[0]["price"] == "50000.00"
        assert trades[1]["is_buyer_maker"] is True

    def test_get_exchange_info(self, server):
        result = server._cli(
            ["BinanceMarketService", "GetExchangeInfo", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert result["timezone"] == "UTC"
        assert "rate_limits" in result
        assert len(result["rate_limits"]) == 1
        assert result["rate_limits"][0]["rate_limit_type"] == "REQUEST_WEIGHT"
        assert "symbols" in result
        assert len(result["symbols"]) == 1
        sym = result["symbols"][0]
        assert sym["symbol"] == "BTCUSDT"
        assert sym["base_asset"] == "BTC"
        assert sym["quote_asset"] == "USDT"

    def test_get_avg_price(self, server):
        result = server._cli(
            ["BinanceMarketService", "GetAvgPrice", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert result["mins"] == 5
        assert result["price"] == "50000.00"

    def test_get_book_ticker_single(self, server):
        result = server._cli(
            ["BinanceMarketService", "GetBookTicker", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        assert tickers[0]["symbol"] == "BTCUSDT"
        assert tickers[0]["bid_price"] == "49999.00"
        assert tickers[0]["ask_price"] == "50001.00"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["BinanceMarketService", "DoesNotExist"])


class TestHTTPProjection:
    @pytest.fixture(autouse=True)
    def start_http(self, server):
        self.port = server._start_http(0)
        yield
        server._stop_http()

    def _post(self, path: str, body: dict | None = None):
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read())

    def test_get_price(self):
        result = self._post(
            "/binance.v1.BinanceMarketService/GetPrice",
            {"symbol": "BTCUSDT"},
        )
        assert len(result["prices"]) == 1
        assert result["prices"][0]["price"] == "50000.00"

    def test_get_orderbook(self):
        result = self._post(
            "/binance.v1.BinanceMarketService/GetOrderbook",
            {"symbol": "BTCUSDT"},
        )
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2

    def test_get_avg_price(self):
        result = self._post(
            "/binance.v1.BinanceMarketService/GetAvgPrice",
            {"symbol": "BTCUSDT"},
        )
        assert result["price"] == "50000.00"

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
