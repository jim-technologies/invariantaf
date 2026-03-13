"""Unit tests for Bitget service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "BitgetService.ListSpotTickers",
    "BitgetService.GetSpotOrderbook",
    "BitgetService.GetSpotCandles",
    "BitgetService.ListFuturesTickers",
    "BitgetService.GetFuturesOrderbook",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 5

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_list_spot_tickers(self, server):
        result = server._cli(
            ["BitgetService", "ListSpotTickers", "-r", "{}"]
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        t = tickers[0]
        assert t["symbol"] == "BTCUSDT"
        assert t["last_pr"] == "64500.00"
        assert t["high24h"] == "65000.00"
        assert t["bid_pr"] == "64490.00"
        assert t["ask_pr"] == "64510.00"

    def test_list_spot_tickers_with_symbol(self, server):
        result = server._cli(
            ["BitgetService", "ListSpotTickers", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert "tickers" in result
        assert len(result["tickers"]) == 1

    def test_get_spot_orderbook(self, server):
        result = server._cli(
            ["BitgetService", "GetSpotOrderbook", "-r", '{"symbol":"BTCUSDT"}']
        )
        assert "asks" in result
        assert "bids" in result
        assert len(result["asks"]) == 2
        assert len(result["bids"]) == 2
        assert result["asks"][0]["price"] == "64510.00"
        assert result["asks"][0]["amount"] == "2.0"
        assert result["bids"][0]["price"] == "64490.00"
        assert result["bids"][0]["amount"] == "1.5"
        assert result["ts"] == "1772720841000"

    def test_get_spot_orderbook_with_limit(self, server):
        result = server._cli(
            ["BitgetService", "GetSpotOrderbook", "-r", '{"symbol":"BTCUSDT","limit":5}']
        )
        assert "asks" in result
        assert "bids" in result

    def test_get_spot_candles(self, server):
        result = server._cli(
            ["BitgetService", "GetSpotCandles", "-r", '{"symbol":"BTCUSDT","granularity":"1h"}']
        )
        assert "candles" in result
        candles = result["candles"]
        assert len(candles) == 3
        c = candles[0]
        assert c["ts"] == "1772720000000"
        assert c["open"] == "64000.00"
        assert c["high"] == "64600.00"
        assert c["low"] == "63900.00"
        assert c["close"] == "64500.00"
        assert c["base_volume"] == "1000.0"

    def test_get_spot_candles_with_limit(self, server):
        result = server._cli(
            [
                "BitgetService",
                "GetSpotCandles",
                "-r",
                '{"symbol":"BTCUSDT","granularity":"1h","limit":50}',
            ]
        )
        assert "candles" in result

    def test_list_futures_tickers(self, server):
        result = server._cli(
            ["BitgetService", "ListFuturesTickers", "-r", '{"productType":"USDT-FUTURES"}']
        )
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        t = tickers[0]
        assert t["symbol"] == "BTCUSDT"
        assert t["last_pr"] == "64500.00"
        assert t["funding_rate"] == "0.0001"
        assert t["index_price"] == "64495.00"

    def test_get_futures_orderbook(self, server):
        result = server._cli(
            [
                "BitgetService",
                "GetFuturesOrderbook",
                "-r",
                '{"symbol":"BTCUSDT","productType":"USDT-FUTURES"}',
            ]
        )
        assert "asks" in result
        assert "bids" in result
        assert len(result["asks"]) == 2
        assert len(result["bids"]) == 2
        assert result["asks"][0]["price"] == "64510.00"
        assert result["asks"][0]["amount"] == "8.0"
        assert result["bids"][0]["price"] == "64490.00"
        assert result["bids"][0]["amount"] == "10.0"
        assert result["ts"] == "1772720841000"

    def test_get_futures_orderbook_with_limit(self, server):
        result = server._cli(
            [
                "BitgetService",
                "GetFuturesOrderbook",
                "-r",
                '{"symbol":"BTCUSDT","productType":"USDT-FUTURES","limit":5}',
            ]
        )
        assert "asks" in result
        assert "bids" in result

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["BitgetService", "DoesNotExist"])


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
            "/bitget.v1.BitgetService/ListSpotTickers",
            {},
        )
        assert len(result["tickers"]) == 1

    def test_get_spot_orderbook(self):
        result = self._post(
            "/bitget.v1.BitgetService/GetSpotOrderbook",
            {"symbol": "BTCUSDT"},
        )
        assert len(result["asks"]) == 2
        assert len(result["bids"]) == 2

    def test_get_spot_candles(self):
        result = self._post(
            "/bitget.v1.BitgetService/GetSpotCandles",
            {"symbol": "BTCUSDT", "granularity": "1h"},
        )
        assert len(result["candles"]) == 3

    def test_list_futures_tickers(self):
        result = self._post(
            "/bitget.v1.BitgetService/ListFuturesTickers",
            {"productType": "USDT-FUTURES"},
        )
        assert len(result["tickers"]) == 1

    def test_get_futures_orderbook(self):
        result = self._post(
            "/bitget.v1.BitgetService/GetFuturesOrderbook",
            {"symbol": "BTCUSDT", "productType": "USDT-FUTURES"},
        )
        assert len(result["asks"]) == 2
        assert len(result["bids"]) == 2

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
