"""Unit tests for KuCoin service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "KucoinService.GetAllTickers",
    "KucoinService.GetTicker",
    "KucoinService.GetOrderbook",
    "KucoinService.GetKlines",
    "KucoinService.ListSymbols",
    "KucoinService.GetFiat",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 6

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_get_all_tickers(self, server):
        result = server._cli(
            ["KucoinService", "GetAllTickers", "-r", "{}"]
        )
        assert "time" in result
        assert result["time"] == "1710300000000"
        assert "ticker" in result
        tickers = result["ticker"]
        assert len(tickers) == 2
        btc = tickers[0]
        assert btc["symbol"] == "BTC-USDT"
        assert btc["buy"] == "83500.1"
        assert btc["sell"] == "83500.2"
        assert btc["last"] == "83500.15"
        eth = tickers[1]
        assert eth["symbol"] == "ETH-USDT"
        assert eth["last"] == "1920.65"

    def test_get_ticker(self, server):
        result = server._cli(
            ["KucoinService", "GetTicker", "-r", '{"symbol":"BTC-USDT"}']
        )
        assert result["symbol"] == "BTC-USDT"
        assert result["buy"] == "83500.1"
        assert result["sell"] == "83500.2"
        assert result["last"] == "83500.15"
        assert result["high"] == "84000"
        assert result["low"] == "81000"
        assert result["change_rate"] == "0.025"
        assert result["vol"] == "12500.5"

    def test_get_orderbook(self, server):
        result = server._cli(
            ["KucoinService", "GetOrderbook", "-r", '{"symbol":"BTC-USDT"}']
        )
        assert result["sequence"] == "1234567890"
        assert result["time"] == "1710300000000"
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2
        assert result["bids"][0]["price"] == "83500.1"
        assert result["bids"][0]["size"] == "0.5"
        assert result["asks"][0]["price"] == "83500.2"
        assert result["asks"][0]["size"] == "0.3"

    def test_get_klines(self, server):
        result = server._cli(
            [
                "KucoinService",
                "GetKlines",
                "-r",
                json.dumps({
                    "symbol": "BTC-USDT",
                    "type": "1hour",
                    "start_at": 1710296400,
                    "end_at": 1710307200,
                }),
            ]
        )
        assert "klines" in result
        klines = result["klines"]
        assert len(klines) == 3
        k = klines[0]
        assert k["time"] == "1710296400"
        assert k["open"] == "83000"
        assert k["close"] == "83500"
        assert k["high"] == "83600"
        assert k["low"] == "82900"
        assert k["volume"] == "500.5"
        assert k["turnover"] == "41525000"

    def test_list_symbols(self, server):
        result = server._cli(
            ["KucoinService", "ListSymbols", "-r", "{}"]
        )
        assert "symbols" in result
        symbols = result["symbols"]
        assert len(symbols) == 2
        btc = symbols[0]
        assert btc["symbol"] == "BTC-USDT"
        assert btc["base_currency"] == "BTC"
        assert btc["quote_currency"] == "USDT"
        assert btc["market"] == "USDS"
        assert btc["enable_trading"] is True
        assert btc["is_margin_enabled"] is True

    def test_get_fiat(self, server):
        result = server._cli(
            ["KucoinService", "GetFiat", "-r", '{"base":"USD"}']
        )
        assert "prices" in result
        prices = result["prices"]
        assert len(prices) == 3
        by_currency = {p["currency"]: p["price"] for p in prices}
        assert by_currency["BTC"] == "83500.15"
        assert by_currency["ETH"] == "1920.65"
        assert by_currency["SOL"] == "135.20"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["KucoinService", "DoesNotExist"])


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

    def test_get_all_tickers(self):
        result = self._post(
            "/kucoin.v1.KucoinService/GetAllTickers",
            {},
        )
        assert len(result["ticker"]) == 2

    def test_get_orderbook(self):
        result = self._post(
            "/kucoin.v1.KucoinService/GetOrderbook",
            {"symbol": "BTC-USDT"},
        )
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2

    def test_get_ticker(self):
        result = self._post(
            "/kucoin.v1.KucoinService/GetTicker",
            {"symbol": "BTC-USDT"},
        )
        assert result["last"] == "83500.15"

    def test_list_symbols(self):
        result = self._post(
            "/kucoin.v1.KucoinService/ListSymbols",
            {},
        )
        assert len(result["symbols"]) == 2

    def test_get_fiat(self):
        result = self._post(
            "/kucoin.v1.KucoinService/GetFiat",
            {"base": "USD"},
        )
        assert len(result["prices"]) == 3

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
