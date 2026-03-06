"""Integration tests -- descriptor/registration/CLI/HTTP wiring."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from bybit_mcp.spec_meta import TOOL_COUNT
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == TOOL_COUNT

    def test_tool_names(self, server):
        expected = {
            "BybitMarketService.Time",
            "BybitMarketService.Kline",
            "BybitTradeService.CreateOrder",
            "BybitTradeService.CancelOrder",
            "BybitAccountService.Wallet",
            "BybitAssetService.CoinInfo",
            "BybitPositionService.PositionInfo",
            "BybitUserService.ApikeyInfo",
        }
        assert expected.issubset(set(server.tools.keys()))


class TestCLIProjection:
    def test_get_server_time(self, server):
        result = server._cli(["BybitMarketService", "Time"])
        assert int(result["retCode"]) == 0
        assert result["result"]["timeSecond"] == "1700000000"

    def test_get_wallet_balance_private_auth(self, server):
        result = server._cli(
            [
                "BybitAccountService",
                "Wallet",
                "-r",
                '{"accountType":"UNIFIED"}',
            ]
        )
        assert int(result["retCode"]) == 0
        assert result["result"]["accountType"] == "UNIFIED"

    def test_create_order_private_auth(self, server):
        result = server._cli(
            [
                "BybitTradeService",
                "CreateOrder",
                "-r",
                (
                    '{"body":{"category":"linear","symbol":"BTCUSDT","side":"Buy",'
                    '"orderType":"Limit","qty":"1","price":"30000"}}'
                ),
            ]
        )
        assert int(result["retCode"]) == 0
        assert result["result"]["orderId"] == "order-123"
        assert result["result"]["echo"]["orderType"] == "Limit"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["BybitMarketService", "DoesNotExist"])


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

    def test_get_server_time(self):
        result = self._post("/bybit.v1.BybitMarketService/Time")
        assert int(result["retCode"]) == 0
        assert result["result"]["timeNano"] == "1700000000000000000"

    def test_wallet_private_endpoint(self):
        result = self._post(
            "/bybit.v1.BybitAccountService/Wallet",
            {"accountType": "UNIFIED"},
        )
        assert int(result["retCode"]) == 0
        assert result["result"]["accountType"] == "UNIFIED"

    def test_create_order_private_endpoint(self):
        result = self._post(
            "/bybit.v1.BybitTradeService/CreateOrder",
            {
                "body": {
                    "category": "linear",
                    "symbol": "BTCUSDT",
                    "side": "Buy",
                    "orderType": "Limit",
                    "qty": "1",
                    "price": "30000",
                }
            },
        )
        assert int(result["retCode"]) == 0
        assert result["result"]["echo"]["symbol"] == "BTCUSDT"

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
