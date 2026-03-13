"""Unit tests for GeckoTerminal service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "GeckoTerminalService.ListNetworks",
    "GeckoTerminalService.GetTrendingPools",
    "GeckoTerminalService.GetPool",
    "GeckoTerminalService.SearchPools",
    "GeckoTerminalService.GetPoolOHLCV",
    "GeckoTerminalService.GetNewPools",
    "GeckoTerminalService.GetTopPools",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 7

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_list_networks(self, server):
        result = server._cli(
            ["GeckoTerminalService", "ListNetworks"]
        )
        assert "networks" in result
        networks = result["networks"]
        assert len(networks) == 1
        net = networks[0]
        assert net["id"] == "eth"
        assert net["name"] == "Ethereum"
        assert net["coingecko_asset_platform_id"] == "ethereum"

    def test_get_trending_pools_all(self, server):
        result = server._cli(
            ["GeckoTerminalService", "GetTrendingPools"]
        )
        assert "pools" in result
        pools = result["pools"]
        assert len(pools) == 1
        pool = pools[0]
        assert pool["address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        assert pool["name"] == "USDC / WETH 0.05%"
        assert pool["volume_usd_h24"] == 28000000.0
        assert pool["price_change_percentage_h24"] == -2.3

    def test_get_trending_pools_network(self, server):
        result = server._cli(
            ["GeckoTerminalService", "GetTrendingPools", "-r", '{"network":"eth"}']
        )
        assert "pools" in result
        assert len(result["pools"]) == 1
        assert result["pools"][0]["network_id"] == "eth"

    def test_get_pool(self, server):
        result = server._cli(
            [
                "GeckoTerminalService",
                "GetPool",
                "-r",
                json.dumps({
                    "network": "eth",
                    "address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                }),
            ]
        )
        assert "pool" in result
        pool = result["pool"]
        assert pool["address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        assert pool["name"] == "USDC / WETH 0.05%"
        assert pool["base_token_price_usd"] == 3456.78
        assert pool["fdv_usd"] == 5000000000.0
        assert pool["reserve_in_usd"] == 250000000.0
        assert pool["dex_id"] == "uniswap_v3"

    def test_search_pools(self, server):
        result = server._cli(
            ["GeckoTerminalService", "SearchPools", "-r", '{"query":"WETH"}']
        )
        assert "pools" in result
        pools = result["pools"]
        assert len(pools) == 1
        assert pools[0]["address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    def test_get_pool_ohlcv(self, server):
        result = server._cli(
            [
                "GeckoTerminalService",
                "GetPoolOHLCV",
                "-r",
                json.dumps({
                    "network": "eth",
                    "pool_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                    "timeframe": "hour",
                }),
            ]
        )
        assert "candles" in result
        candles = result["candles"]
        assert len(candles) == 3
        c = candles[0]
        assert int(c["timestamp"]) == 1700000000
        assert c["open"] == 3400.0
        assert c["high"] == 3500.0
        assert c["low"] == 3350.0
        assert c["close"] == 3450.0
        assert c["volume"] == 1000000.0

    def test_get_new_pools(self, server):
        result = server._cli(
            ["GeckoTerminalService", "GetNewPools", "-r", '{"network":"eth"}']
        )
        assert "pools" in result
        pools = result["pools"]
        assert len(pools) == 1
        assert pools[0]["address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    def test_get_top_pools(self, server):
        result = server._cli(
            [
                "GeckoTerminalService",
                "GetTopPools",
                "-r",
                json.dumps({"network": "eth", "dex": "uniswap_v3"}),
            ]
        )
        assert "pools" in result
        pools = result["pools"]
        assert len(pools) == 1
        assert pools[0]["address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["GeckoTerminalService", "DoesNotExist"])


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

    def test_list_networks(self):
        result = self._post(
            "/geckoterminal.v1.GeckoTerminalService/ListNetworks",
        )
        assert len(result["networks"]) == 1

    def test_get_pool(self):
        result = self._post(
            "/geckoterminal.v1.GeckoTerminalService/GetPool",
            {"network": "eth", "address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"},
        )
        assert result["pool"]["address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    def test_search_pools(self):
        result = self._post(
            "/geckoterminal.v1.GeckoTerminalService/SearchPools",
            {"query": "WETH"},
        )
        assert len(result["pools"]) == 1

    def test_get_pool_ohlcv(self):
        result = self._post(
            "/geckoterminal.v1.GeckoTerminalService/GetPoolOHLCV",
            {
                "network": "eth",
                "pool_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "timeframe": "hour",
            },
        )
        assert len(result["candles"]) == 3

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
