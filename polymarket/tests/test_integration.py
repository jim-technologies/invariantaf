"""Integration tests -- descriptor/registration/CLI/HTTP wiring."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "PolymarketGammaService.Search",
    "PolymarketGammaService.ListEvents",
    "PolymarketGammaService.GetEvent",
    "PolymarketGammaService.GetEventById",
    "PolymarketGammaService.GetMarket",
    "PolymarketGammaService.GetMarketById",
    "PolymarketClobService.GetOrderbook",
    "PolymarketClobService.GetPrice",
    "PolymarketClobService.GetMidpoint",
    "PolymarketClobService.GetSpread",
    "PolymarketClobService.GetPriceHistory",
    "PolymarketClobService.PlaceOrder",
    "PolymarketClobService.CreateAndPostOrder",
    "PolymarketClobService.CancelOrder",
    "PolymarketClobService.CancelAllOrders",
    "PolymarketClobService.GetOpenOrders",
    "PolymarketClobService.GetTrades",
    "PolymarketClobService.GetBalance",
    "PolymarketClobService.GetBalanceAllowance",
    "PolymarketDataService.GetPositions",
    "PolymarketDataService.GetLeaderboard",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 21

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_search(self, server):
        result = server._cli(["PolymarketGammaService", "Search", "-r", '{"q":"btc","limit":1}'])
        assert result["data"]["events"][0]["slug"] == "test-event"
        assert result["data"]["markets"][0]["id"] == "456"
        assert result["data"]["profiles"][0]["pseudonym"] == "alpha"

    def test_list_events(self, server):
        result = server._cli(["PolymarketGammaService", "ListEvents", "-r", '{"limit": 1}'])
        assert isinstance(result["data"], list)
        assert result["data"][0]["slug"] == "test-event"

    def test_get_event(self, server):
        result = server._cli(
            ["PolymarketGammaService", "GetEvent", "-r", '{"slug":"test-event"}']
        )
        assert result["data"]["id"] == "123"
        assert result["data"]["markets"][0]["id"] == "456"

    def test_get_event_by_id(self, server):
        result = server._cli(["PolymarketGammaService", "GetEventById", "-r", '{"id":"123"}'])
        assert result["data"]["slug"] == "test-event"

    def test_get_market(self, server):
        result = server._cli(["PolymarketGammaService", "GetMarket", "-r", '{"slug":"test-market"}'])
        assert result["data"][0]["id"] == "456"
        assert result["data"][0]["tokens"][0]["token_id"] == "tok-yes"

    def test_get_market_by_id(self, server):
        result = server._cli(["PolymarketGammaService", "GetMarketById", "-r", '{"id":"456"}'])
        assert result["data"]["slug"] == "test-market"

    def test_get_orderbook(self, server):
        result = server._cli(
            ["PolymarketClobService", "GetOrderbook", "-r", '{"token_id":"tok-yes"}']
        )
        assert result["data"]["bids"][0]["price"] == 0.41
        assert result["data"]["tick_size"] == 0.01

    def test_get_price(self, server):
        result = server._cli(
            ["PolymarketClobService", "GetPrice", "-r", '{"token_id":"tok-yes","side":"BUY"}']
        )
        assert result["data"]["price"] == 0.42

    def test_get_midpoint(self, server):
        result = server._cli(
            ["PolymarketClobService", "GetMidpoint", "-r", '{"token_id":"tok-yes"}']
        )
        assert result["data"]["mid"] == 0.42

    def test_get_spread(self, server):
        result = server._cli(
            ["PolymarketClobService", "GetSpread", "-r", '{"token_id":"tok-yes"}']
        )
        assert result["data"]["spread"] == 0.02

    def test_get_price_history(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "GetPriceHistory",
                "-r",
                '{"market":"0xmarket","interval":"1m","fidelity":1}',
            ]
        )
        assert len(result["data"]["history"]) == 2
        assert result["data"]["history"][1]["p"] == 0.42

    def test_place_order(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "PlaceOrder",
                "-r",
                (
                    '{"order":{"salt":"1","maker":"0xmaker","signer":"0xmaker",'
                    '"taker":"0x0000000000000000000000000000000000000000",'
                    '"tokenId":"123456789","makerAmount":"10","takerAmount":"4.2",'
                    '"expiration":"0","nonce":"0","feeRateBps":"0","side":"BUY",'
                    '"signatureType":0,"signature":"0xsig"},'
                    '"order_type":"GTC","post_only":false}'
                ),
            ]
        )
        assert result["data"]["success"] is True
        assert result["data"]["order_id"] == "ord-1"
        assert result["data"]["transactions_hashes"] == ["0xtx1"]

    def test_place_order_sdk_json_field_names(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "PlaceOrder",
                "-r",
                (
                    '{"order":{"salt":"1","maker":"0xmaker","signer":"0xmaker",'
                    '"taker":"0x0000000000000000000000000000000000000000",'
                    '"tokenId":"123456789","makerAmount":"10","takerAmount":"4.2",'
                    '"expiration":"0","nonce":"0","feeRateBps":"0","side":"BUY",'
                    '"signatureType":0,"signature":"0xsig"},'
                    '"orderType":"GTC","postOnly":true}'
                ),
            ]
        )
        assert result["data"]["success"] is True
        assert result["data"]["order_id"] == "ord-1"

    def test_create_and_post_order(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "CreateAndPostOrder",
                "-r",
                (
                    '{"token_id":"123456789","price":0.42,"size":10,'
                    '"side":"BUY","fee_rate_bps":0,"nonce":1,'
                    '"expiration":0}'
                ),
            ]
        )
        assert result["data"]["success"] is True
        assert result["data"]["order_id"] == "ord-1"
        assert result["data"]["transactions_hashes"] == ["0xtx1"]

    def test_create_and_post_order_required_only(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "CreateAndPostOrder",
                "-r",
                (
                    '{"token_id":"123456789","price":0.42,"size":10,'
                    '"side":"BUY"}'
                ),
            ]
        )
        assert result["data"]["success"] is True
        assert result["data"]["order_id"] == "ord-1"

    def test_cancel_order(self, server):
        result = server._cli(["PolymarketClobService", "CancelOrder", "-r", '{"order_id":"ord-1"}'])
        assert result["data"]["canceled"] == ["ord-1"]

    def test_cancel_all_orders(self, server):
        result = server._cli(["PolymarketClobService", "CancelAllOrders"])
        assert result["data"]["canceled"] == ["ord-1"]

    def test_get_open_orders(self, server):
        result = server._cli(["PolymarketClobService", "GetOpenOrders"])
        assert result["data"][0]["id"] == "ord-1"

    def test_get_trades(self, server):
        result = server._cli(["PolymarketClobService", "GetTrades"])
        assert result["data"][0]["id"] == "trd-1"
        assert result["data"][0]["price"] == 0.41

    def test_get_balance(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "GetBalance",
                "-r",
                '{"asset_type":"COLLATERAL","token_id":"","signature_type":0}',
            ]
        )
        assert result["data"]["balance"] == "1000.5"
        assert result["data"]["allowance"] == "2500.25"
        assert (
            result["data"]["allowances"]["0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"]
            == "2500.25"
        )

    def test_get_balance_defaults_signature_type(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "GetBalance",
                "-r",
                '{"asset_type":"COLLATERAL","token_id":""}',
            ]
        )
        assert result["data"]["balance"] == "1000.5"

    def test_get_balance_sentinel_signature_type(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "GetBalance",
                "-r",
                '{"asset_type":"COLLATERAL","token_id":"","signature_type":-1}',
            ]
        )
        assert result["data"]["balance"] == "1000.5"

    def test_private_auth_headers_are_applied(self, server):
        # This call is private and will fail if L2 auth headers are not attached.
        result = server._cli(["PolymarketClobService", "GetOpenOrders"])
        assert len(result["data"]) == 1

    def test_get_balance_allowance_alias(self, server):
        result = server._cli(
            [
                "PolymarketClobService",
                "GetBalanceAllowance",
                "-r",
                '{"asset_type":"COLLATERAL","token_id":"","signature_type":0}',
            ]
        )
        assert result["data"]["balance"] == "1000.5"
        assert (
            result["data"]["allowances"]["0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"]
            == "2500.25"
        )

    def test_get_positions(self, server):
        result = server._cli(
            [
                "PolymarketDataService",
                "GetPositions",
                "-r",
                '{"user":"0xabc","sizeThreshold":0}',
            ]
        )
        assert result["data"][0]["asset"] == "tok-yes"
        assert result["data"][0]["avg_price"] == 0.41

    def test_get_leaderboard(self, server):
        result = server._cli(
            [
                "PolymarketDataService",
                "GetLeaderboard",
                "-r",
                '{"interval":"max","limit":1,"offset":0}',
            ]
        )
        assert result["data"][0]["pseudonym"] == "alpha"
        assert result["data"][0]["profile_image_optimized"]["image_30px"].endswith("p-30.png")

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["PolymarketGammaService", "DoesNotExist"])


_HTTP_CASES = [
    ("/polymarket.v1.PolymarketGammaService/Search", {"q": "btc", "limit": 1}),
    ("/polymarket.v1.PolymarketGammaService/ListEvents", {"limit": 1}),
    ("/polymarket.v1.PolymarketGammaService/GetEvent", {"slug": "test-event"}),
    ("/polymarket.v1.PolymarketGammaService/GetEventById", {"id": "123"}),
    ("/polymarket.v1.PolymarketGammaService/GetMarket", {"slug": "test-market"}),
    ("/polymarket.v1.PolymarketGammaService/GetMarketById", {"id": "456"}),
    ("/polymarket.v1.PolymarketClobService/GetOrderbook", {"token_id": "tok-yes"}),
    ("/polymarket.v1.PolymarketClobService/GetPrice", {"token_id": "tok-yes", "side": "BUY"}),
    ("/polymarket.v1.PolymarketClobService/GetMidpoint", {"token_id": "tok-yes"}),
    ("/polymarket.v1.PolymarketClobService/GetSpread", {"token_id": "tok-yes"}),
    (
        "/polymarket.v1.PolymarketClobService/GetPriceHistory",
        {"market": "0xmarket", "interval": "1m", "fidelity": 1},
    ),
    (
        "/polymarket.v1.PolymarketClobService/PlaceOrder",
        {
            "order": {
                "salt": "1",
                "maker": "0xmaker",
                "signer": "0xmaker",
                "taker": "0x0000000000000000000000000000000000000000",
                "tokenId": "123456789",
                "makerAmount": "10",
                "takerAmount": "4.2",
                "expiration": "0",
                "nonce": "0",
                "feeRateBps": "0",
                "side": "BUY",
                "signatureType": 0,
                "signature": "0xsig",
            },
            "order_type": "GTC",
            "post_only": False,
        },
    ),
    (
        "/polymarket.v1.PolymarketClobService/CreateAndPostOrder",
        {
            "token_id": "123456789",
            "price": 0.42,
            "size": 10,
            "side": "BUY",
            "fee_rate_bps": 0,
            "nonce": 1,
            "expiration": 0,
        },
    ),
    ("/polymarket.v1.PolymarketClobService/CancelOrder", {"order_id": "ord-1"}),
    ("/polymarket.v1.PolymarketClobService/CancelAllOrders", {}),
    ("/polymarket.v1.PolymarketClobService/GetOpenOrders", {}),
    ("/polymarket.v1.PolymarketClobService/GetTrades", {}),
    (
        "/polymarket.v1.PolymarketClobService/GetBalance",
        {"asset_type": "COLLATERAL", "token_id": "", "signature_type": 0},
    ),
    (
        "/polymarket.v1.PolymarketClobService/GetBalanceAllowance",
        {"asset_type": "COLLATERAL", "token_id": "", "signature_type": 0},
    ),
    (
        "/polymarket.v1.PolymarketDataService/GetPositions",
        {"user": "0xabc", "sizeThreshold": 0},
    ),
    (
        "/polymarket.v1.PolymarketDataService/GetLeaderboard",
        {"interval": "max", "limit": 1, "offset": 0},
    ),
]


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

    @pytest.mark.parametrize(("path", "body"), _HTTP_CASES)
    def test_all_routes(self, path: str, body: dict):
        result = self._post(path, body)
        assert "data" in result

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
