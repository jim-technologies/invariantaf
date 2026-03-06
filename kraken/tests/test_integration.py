"""Integration tests -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "KrakenSpotService.GetServerTime",
    "KrakenSpotService.GetSystemStatus",
    "KrakenSpotService.GetTradableAssetPairs",
    "KrakenSpotService.GetTickerInformation",
    "KrakenSpotService.GetOrderBook",
    "KrakenSpotService.GetAccountBalance",
    "KrakenSpotService.GetOpenOrders",
    "KrakenSpotService.AddOrder",
    "KrakenSpotService.CancelOrder",
    "KrakenSpotService.CancelAllOrders",
    "KrakenSpotService.CancelAllOrdersAfter",
    "KrakenFuturesService.GetInstruments",
    "KrakenFuturesService.GetTickers",
    "KrakenFuturesService.GetOrderbook",
    "KrakenFuturesService.SendOrder",
    "KrakenFuturesService.CancelOrder",
    "KrakenFuturesService.GetOpenOrders",
    "KrakenFuturesService.GetOpenPositions",
    "KrakenFuturesService.GetFills",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 19

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_spot_get_server_time(self, server):
        result = server._cli(["KrakenSpotService", "GetServerTime"])
        assert result["result"]["unixtime"] == "1700000000"

    def test_spot_get_ticker_information(self, server):
        result = server._cli(
            ["KrakenSpotService", "GetTickerInformation", "-r", '{"pair":"XBTUSD"}']
        )
        assert result["result"]["XBTUSD"]["a"]["price"] == "30001.0"
        assert result["result"]["XBTUSD"]["t"]["today"] == "10"

    def test_spot_add_order_private_auth(self, server):
        result = server._cli(
            [
                "KrakenSpotService",
                "AddOrder",
                "-r",
                '{"ordertype":"limit","type":"buy","volume":"1.0","pair":"XBTUSD","price":"30000"}',
            ]
        )
        assert result["result"]["txid"] == ["OABC-123"]

    def test_futures_send_order_private_auth(self, server):
        result = server._cli(
            [
                "KrakenFuturesService",
                "SendOrder",
                "-r",
                '{"order_type":"lmt","symbol":"PF_XBTUSD","side":"buy","size":1.0,"limit_price":30000}',
            ]
        )
        assert result["send_status"]["status"] == "placed"
        assert result["send_status"]["order_id"] == "ord-2"

    def test_futures_get_orderbook(self, server):
        result = server._cli(
            ["KrakenFuturesService", "GetOrderbook", "-r", '{"symbol":"PF_XBTUSD"}']
        )
        assert result["order_book"]["asks"][0]["price"] == 30001.0
        assert result["order_book"]["bids"][0]["size"] == 1.5

    def test_futures_get_open_positions(self, server):
        result = server._cli(["KrakenFuturesService", "GetOpenPositions"])
        assert result["open_positions"][0]["symbol"] == "PF_XBTUSD"
        assert result["open_positions"][0]["side"] == "long"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["KrakenSpotService", "DoesNotExist"])


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

    def test_spot_get_system_status(self):
        result = self._post("/kraken.v1.KrakenSpotService/GetSystemStatus")
        assert result["result"]["status"] == "online"

    def test_futures_get_fills(self):
        result = self._post("/kraken.v1.KrakenFuturesService/GetFills")
        assert result["fills"][0]["fill_id"] == "fill-1"

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
