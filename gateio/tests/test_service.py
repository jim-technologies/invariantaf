"""Unit tests for Gate.io service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "GateioService.ListSpotTickers",
    "GateioService.GetSpotOrderbook",
    "GateioService.GetSpotCandlesticks",
    "GateioService.ListCurrencyPairs",
    "GateioService.ListFuturesTickers",
    "GateioService.GetFuturesOrderbook",
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
    def test_list_spot_tickers(self, server):
        result = server._cli(
            ["GateioService", "ListSpotTickers", "-r", '{"currency_pair":"BTC_USDT"}']
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        t = tickers[0]
        assert t["currency_pair"] == "BTC_USDT"
        assert t["last"] == 64500.5
        assert t["lowest_ask"] == 64510.0
        assert t["highest_bid"] == 64500.0
        assert t["change_percentage"] == 2.5
        assert t["base_volume"] == 12000.123
        assert t["high_24h"] == 65000.0
        assert t["low_24h"] == 63500.0

    def test_list_spot_tickers_no_filter(self, server):
        result = server._cli(
            ["GateioService", "ListSpotTickers", "-r", "{}"]
        )
        assert "tickers" in result
        assert len(result["tickers"]) == 1

    def test_get_spot_orderbook(self, server):
        result = server._cli(
            ["GateioService", "GetSpotOrderbook", "-r", '{"currency_pair":"BTC_USDT"}']
        )
        assert int(result["current"]) == 1772720841000
        assert int(result["update"]) == 1772720841000
        assert len(result["asks"]) == 2
        assert len(result["bids"]) == 2
        assert result["asks"][0]["price"] == 64510.0
        assert result["asks"][0]["amount"] == 3.0
        assert result["bids"][0]["price"] == 64500.0
        assert result["bids"][0]["amount"] == 5.0

    def test_get_spot_candlesticks(self, server):
        result = server._cli(
            [
                "GateioService",
                "GetSpotCandlesticks",
                "-r",
                '{"currency_pair":"BTC_USDT","interval":"1h","limit":100}',
            ]
        )
        assert "candlesticks" in result
        candles = result["candlesticks"]
        assert len(candles) == 3
        c = candles[0]
        assert int(c["timestamp"]) == 1772720000
        assert c["open"] == 64000.0
        assert c["high"] == 65000.0
        assert c["low"] == 63900.0
        assert c["close"] == 64500.0
        assert c["base_volume"] == 100.5
        assert c["quote_volume"] == 500000.0
        assert c["is_closed"] is True
        assert candles[2].get("is_closed", False) is False

    def test_list_currency_pairs(self, server):
        result = server._cli(
            ["GateioService", "ListCurrencyPairs", "-r", "{}"]
        )
        assert "currency_pairs" in result
        pairs = result["currency_pairs"]
        assert len(pairs) == 1
        p = pairs[0]
        assert p["id"] == "BTC_USDT"
        assert p["base"] == "BTC"
        assert p["quote"] == "USDT"
        assert p["fee"] == 0.2
        assert p["min_base_amount"] == 0.0001
        assert p["amount_precision"] == 4
        assert p["precision"] == 2
        assert p["trade_status"] == "tradable"

    def test_list_futures_tickers(self, server):
        result = server._cli(
            ["GateioService", "ListFuturesTickers", "-r", '{"contract":"BTC_USDT"}']
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        t = tickers[0]
        assert t["contract"] == "BTC_USDT"
        assert t["last"] == 64500.5
        assert t["mark_price"] == 64502.5
        assert t["index_price"] == 64500.0
        assert t["funding_rate"] == 0.00015
        assert t["high_24h"] == 65000.0
        assert t["low_24h"] == 63500.0
        assert t["total_size"] == 250000.0

    def test_get_futures_orderbook(self, server):
        result = server._cli(
            ["GateioService", "GetFuturesOrderbook", "-r", '{"contract":"BTC_USDT"}']
        )
        assert int(result["current"]) == 1772720841000
        assert int(result["update"]) == 1772720841000
        assert len(result["asks"]) == 2
        assert len(result["bids"]) == 2
        assert result["asks"][0]["price"] == 64510.0
        assert result["asks"][0]["size"] == 300.0
        assert result["bids"][0]["price"] == 64500.0
        assert result["bids"][0]["size"] == 500.0

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["GateioService", "DoesNotExist"])


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

    def test_list_spot_tickers(self):
        result = self._post(
            "/gateio.v1.GateioService/ListSpotTickers",
            {"currency_pair": "BTC_USDT"},
        )
        assert len(result["tickers"]) == 1

    def test_get_spot_orderbook(self):
        result = self._post(
            "/gateio.v1.GateioService/GetSpotOrderbook",
            {"currency_pair": "BTC_USDT"},
        )
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2

    def test_list_futures_tickers(self):
        result = self._post(
            "/gateio.v1.GateioService/ListFuturesTickers",
            {"contract": "BTC_USDT"},
        )
        assert len(result["tickers"]) == 1

    def test_get_futures_orderbook(self):
        result = self._post(
            "/gateio.v1.GateioService/GetFuturesOrderbook",
            {"contract": "BTC_USDT"},
        )
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
