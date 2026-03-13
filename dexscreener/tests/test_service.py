"""Unit tests for DexScreener service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "DexScreenerService.SearchPairs",
    "DexScreenerService.GetPairsByChainAndAddress",
    "DexScreenerService.GetTokenPairs",
    "DexScreenerService.GetLatestTokenProfiles",
    "DexScreenerService.GetLatestBoostedTokens",
    "DexScreenerService.GetTopBoostedTokens",
    "DexScreenerService.GetOrdersByToken",
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
    def test_search_pairs(self, server):
        result = server._cli(
            ["DexScreenerService", "SearchPairs", "-r", '{"query":"WETH"}']
        )
        assert "pairs" in result
        pairs = result["pairs"]
        assert len(pairs) == 1
        pair = pairs[0]
        assert pair["chain_id"] == "ethereum"
        assert pair["dex_id"] == "uniswap"
        assert pair["pair_address"] == "0xabcdef1234567890abcdef1234567890abcdef12"
        assert pair["base_token"]["symbol"] == "WETH"
        assert pair["base_token"]["name"] == "Wrapped Ether"
        assert pair["quote_token"]["symbol"] == "USDT"
        assert pair["price_usd"] == "2100.50"
        assert pair["volume"]["h24"] == 14000000.0
        assert pair["price_change"]["h24"] == 2.5
        assert pair["liquidity"]["usd"] == 5000000.0
        assert pair["txns"]["h24"]["buys"] == 2800
        assert pair["txns"]["h24"]["sells"] == 2100
        assert pair["fdv"] == 250000000.0
        assert pair["market_cap"] == 250000000.0
        assert pair["pair_created_at"] == "1669602341000"

    def test_get_pairs_by_chain_and_address(self, server):
        result = server._cli(
            [
                "DexScreenerService",
                "GetPairsByChainAndAddress",
                "-r",
                '{"chain_id":"ethereum","pair_addresses":"0xabcdef"}',
            ]
        )
        assert "pairs" in result
        pairs = result["pairs"]
        assert len(pairs) == 1
        assert pairs[0]["chain_id"] == "ethereum"
        assert pairs[0]["base_token"]["symbol"] == "WETH"

    def test_get_token_pairs(self, server):
        result = server._cli(
            [
                "DexScreenerService",
                "GetTokenPairs",
                "-r",
                '{"token_addresses":"0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"}',
            ]
        )
        assert "pairs" in result
        pairs = result["pairs"]
        assert len(pairs) == 1
        assert pairs[0]["base_token"]["address"] == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

    def test_get_latest_token_profiles(self, server):
        result = server._cli(
            ["DexScreenerService", "GetLatestTokenProfiles"]
        )
        assert "profiles" in result
        profiles = result["profiles"]
        assert len(profiles) == 1
        p = profiles[0]
        assert p["chain_id"] == "ethereum"
        assert p["token_address"] == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        assert p["icon"] == "https://example.com/icon.png"
        assert p["description"] == "Wrapped Ether token"
        assert len(p["links"]) == 2
        assert p["links"][0]["type"] == "website"
        assert p["links"][0]["url"] == "https://weth.io"

    def test_get_latest_boosted_tokens(self, server):
        result = server._cli(
            ["DexScreenerService", "GetLatestBoostedTokens"]
        )
        assert "tokens" in result
        tokens = result["tokens"]
        assert len(tokens) == 1
        t = tokens[0]
        assert t["chain_id"] == "solana"
        assert t["token_address"] == "abc123def456"
        assert t["total_amount"] == 500.0
        assert t["amount"] == 100.0
        assert t["description"] == "A boosted token"
        assert len(t["links"]) == 1

    def test_get_top_boosted_tokens(self, server):
        result = server._cli(
            ["DexScreenerService", "GetTopBoostedTokens"]
        )
        assert "tokens" in result
        tokens = result["tokens"]
        assert len(tokens) == 1
        assert tokens[0]["total_amount"] == 500.0

    def test_get_orders_by_token(self, server):
        result = server._cli(
            [
                "DexScreenerService",
                "GetOrdersByToken",
                "-r",
                '{"chain_id":"solana","token_address":"abc123def456"}',
            ]
        )
        assert "orders" in result
        orders = result["orders"]
        assert len(orders) == 1
        o = orders[0]
        assert o["chain_id"] == "solana"
        assert o["token_address"] == "abc123def456"
        assert o["type"] == "tokenProfile"
        assert o["status"] == "approved"
        assert o["payment_timestamp"] == "1700000000000"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["DexScreenerService", "DoesNotExist"])


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

    def test_search_pairs(self):
        result = self._post(
            "/dexscreener.v1.DexScreenerService/SearchPairs",
            {"query": "WETH"},
        )
        assert len(result["pairs"]) == 1

    def test_get_latest_token_profiles(self):
        result = self._post(
            "/dexscreener.v1.DexScreenerService/GetLatestTokenProfiles",
        )
        assert len(result["profiles"]) == 1

    def test_get_latest_boosted_tokens(self):
        result = self._post(
            "/dexscreener.v1.DexScreenerService/GetLatestBoostedTokens",
        )
        assert len(result["tokens"]) == 1

    def test_get_orders_by_token(self):
        result = self._post(
            "/dexscreener.v1.DexScreenerService/GetOrdersByToken",
            {"chain_id": "solana", "token_address": "abc123def456"},
        )
        assert len(result["orders"]) == 1

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
