"""Unit tests -- descriptor/registration/CLI/HTTP wiring for Opinion.trade."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "OpinionService.ListMarkets",
    "OpinionService.GetMarket",
    "OpinionService.GetCategoricalMarket",
    "OpinionService.GetMarketBySlug",
    "OpinionService.GetLatestPrice",
    "OpinionService.GetOrderbook",
    "OpinionService.GetPriceHistory",
    "OpinionService.GetUserTrades",
    "OpinionService.ListQuoteTokens",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 9

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_list_markets(self, server):
        result = server._cli(
            ["OpinionService", "ListMarkets", "-r", '{"page":1,"limit":10}']
        )
        assert result["data"]["total"] == 2
        assert len(result["data"]["list"]) == 2
        assert result["data"]["list"][0]["market_id"] == 101
        assert result["data"]["list"][0]["market_title"] == "Will BTC hit $200k by 2027?"

    def test_list_markets_default_params(self, server):
        result = server._cli(["OpinionService", "ListMarkets"])
        assert result["data"]["total"] == 2

    def test_get_market(self, server):
        result = server._cli(
            ["OpinionService", "GetMarket", "-r", '{"market_id":101}']
        )
        assert result["data"]["market_id"] == 101
        assert result["data"]["status"] == "activated"
        # market_type == 0 (binary) may be omitted by proto3 default-value elision
        assert result["data"].get("market_type", 0) == 0
        assert result["data"]["yes_label"] == "Yes"
        assert result["data"]["no_label"] == "No"
        assert len(result["data"]["tokens"]) == 2
        assert result["data"]["tokens"][0]["token_id"] == "tok-yes-101"

    def test_get_market_conditions(self, server):
        result = server._cli(
            ["OpinionService", "GetMarket", "-r", '{"market_id":101}']
        )
        assert len(result["data"]["conditions"]) == 1
        assert result["data"]["conditions"][0]["condition_id"] == "cond-101"

    def test_get_market_rules(self, server):
        result = server._cli(
            ["OpinionService", "GetMarket", "-r", '{"market_id":101}']
        )
        assert "Resolves Yes" in result["data"]["rules"]

    def test_get_categorical_market(self, server):
        result = server._cli(
            ["OpinionService", "GetCategoricalMarket", "-r", '{"market_id":101}']
        )
        assert result["data"]["parent"]["market_id"] == 101
        assert len(result["data"]["child_markets"]) == 2

    def test_get_market_by_slug(self, server):
        result = server._cli(
            ["OpinionService", "GetMarketBySlug", "-r", '{"slug":"btc-200k-2027"}']
        )
        assert result["data"]["market_id"] == 101
        assert result["data"]["slug"] == "btc-200k-2027"

    def test_get_latest_price(self, server):
        result = server._cli(
            ["OpinionService", "GetLatestPrice", "-r", '{"token_id":"tok-yes-101"}']
        )
        assert result["data"]["token_id"] == "tok-yes-101"
        assert result["data"]["price"] == "0.62"
        assert result["data"]["side"] == "BUY"
        assert result["data"]["size"] == "150"

    def test_get_orderbook(self, server):
        result = server._cli(
            ["OpinionService", "GetOrderbook", "-r", '{"token_id":"tok-yes-101"}']
        )
        assert result["data"]["token_id"] == "tok-yes-101"
        assert len(result["data"]["bids"]) == 2
        assert len(result["data"]["asks"]) == 2
        assert result["data"]["bids"][0]["price"] == "0.61"
        assert result["data"]["asks"][0]["size"] == "180"

    def test_get_price_history(self, server):
        result = server._cli(
            [
                "OpinionService",
                "GetPriceHistory",
                "-r",
                '{"token_id":"tok-yes-101","interval":"1h"}',
            ]
        )
        assert len(result["data"]["history"]) == 3
        # int64 fields are serialized as strings in proto3 JSON
        assert str(result["data"]["history"][0]["t"]) == "1772720000"
        assert result["data"]["history"][2]["p"] == "0.62"

    def test_get_user_trades(self, server):
        result = server._cli(
            [
                "OpinionService",
                "GetUserTrades",
                "-r",
                '{"wallet_address":"0xuser1","page":1,"limit":10}',
            ]
        )
        assert result["data"]["total"] == 1
        assert len(result["data"]["list"]) == 1
        trade = result["data"]["list"][0]
        assert trade["tx_hash"] == "0xabc123"
        assert trade["market_id"] == 101
        assert trade["side"] == "BUY"
        assert trade["outcome"] == "Yes"
        assert trade["price"] == "0.60"
        assert trade["shares"] == "100"

    def test_list_quote_tokens(self, server):
        result = server._cli(["OpinionService", "ListQuoteTokens"])
        assert len(result["data"]) == 1
        qt = result["data"][0]
        assert qt["symbol"] == "USDC"
        assert qt["name"] == "USD Coin"
        assert qt["decimals"] == 6

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["OpinionService", "DoesNotExist"])


_HTTP_CASES = [
    ("/opinion.v1.OpinionService/ListMarkets", {"page": 1, "limit": 10}),
    ("/opinion.v1.OpinionService/GetMarket", {"market_id": 101}),
    ("/opinion.v1.OpinionService/GetCategoricalMarket", {"market_id": 101}),
    ("/opinion.v1.OpinionService/GetMarketBySlug", {"slug": "btc-200k-2027"}),
    ("/opinion.v1.OpinionService/GetLatestPrice", {"token_id": "tok-yes-101"}),
    ("/opinion.v1.OpinionService/GetOrderbook", {"token_id": "tok-yes-101"}),
    (
        "/opinion.v1.OpinionService/GetPriceHistory",
        {"token_id": "tok-yes-101", "interval": "1h"},
    ),
    (
        "/opinion.v1.OpinionService/GetUserTrades",
        {"wallet_address": "0xuser1", "page": 1, "limit": 10},
    ),
    ("/opinion.v1.OpinionService/ListQuoteTokens", {}),
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
