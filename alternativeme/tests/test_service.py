"""Unit tests for Alternative.me service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "AlternativeMeService.GetFearGreedIndex",
    "AlternativeMeService.GetGlobalMarketData",
    "AlternativeMeService.GetCoinData",
    "AlternativeMeService.GetListings",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 4

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_get_fear_greed_index(self, server):
        result = server._cli(
            ["AlternativeMeService", "GetFearGreedIndex", "-r", '{}']
        )
        assert "data" in result
        data = result["data"]
        assert len(data) == 1
        entry = data[0]
        assert entry["value"] == "25"
        assert entry["value_classification"] == "Extreme Fear"
        assert int(entry["timestamp"]) == 1710288000
        assert entry["time_until_update"] == "43210"

    def test_get_fear_greed_index_with_limit(self, server):
        result = server._cli(
            ["AlternativeMeService", "GetFearGreedIndex", "-r", '{"limit":3}']
        )
        assert "data" in result
        assert len(result["data"]) == 3

    def test_get_global_market_data(self, server):
        result = server._cli(
            ["AlternativeMeService", "GetGlobalMarketData", "-r", '{}']
        )
        assert "data" in result
        data = result["data"]
        assert len(data) == 2
        # Find Bitcoin in results
        btc = [d for d in data if d["name"] == "Bitcoin"]
        assert len(btc) == 1
        btc = btc[0]
        assert btc["symbol"] == "BTC"
        assert btc["rank"] == 1
        assert float(btc["price_usd"]) == 65000.50
        assert float(btc["market_cap_usd"]) == 1270000000000

    def test_get_coin_data(self, server):
        result = server._cli(
            ["AlternativeMeService", "GetCoinData", "-r", '{"id":"1"}']
        )
        assert "data" in result
        data = result["data"]
        assert data["name"] == "Bitcoin"
        assert data["symbol"] == "BTC"
        assert data["rank"] == 1
        assert float(data["price_usd"]) == 65000.50

    def test_get_coin_data_eth(self, server):
        result = server._cli(
            ["AlternativeMeService", "GetCoinData", "-r", '{"id":"1027"}']
        )
        assert "data" in result
        data = result["data"]
        assert data["name"] == "Ethereum"
        assert data["symbol"] == "ETH"
        assert data["rank"] == 2
        assert float(data["price_usd"]) == 3500.75

    def test_get_listings(self, server):
        result = server._cli(
            ["AlternativeMeService", "GetListings", "-r", '{}']
        )
        assert "data" in result
        data = result["data"]
        assert len(data) == 2
        assert data[0]["name"] == "Bitcoin"
        assert data[0]["symbol"] == "BTC"
        assert data[0]["website_slug"] == "bitcoin"
        assert data[0]["rank"] == 1
        assert data[1]["name"] == "Ethereum"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["AlternativeMeService", "DoesNotExist"])


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

    def test_get_fear_greed_index(self):
        result = self._post(
            "/alternativeme.v1.AlternativeMeService/GetFearGreedIndex",
            {},
        )
        assert len(result["data"]) == 1
        assert result["data"][0]["value"] == "25"

    def test_get_global_market_data(self):
        result = self._post(
            "/alternativeme.v1.AlternativeMeService/GetGlobalMarketData",
            {},
        )
        assert len(result["data"]) == 2

    def test_get_coin_data(self):
        result = self._post(
            "/alternativeme.v1.AlternativeMeService/GetCoinData",
            {"id": "1"},
        )
        assert result["data"]["name"] == "Bitcoin"

    def test_get_listings(self):
        result = self._post(
            "/alternativeme.v1.AlternativeMeService/GetListings",
            {},
        )
        assert len(result["data"]) == 2

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
