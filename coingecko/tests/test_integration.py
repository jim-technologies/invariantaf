"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from coingecko_mcp.gen.coingecko.v1 import coingecko_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 10

    def test_tool_names(self, server):
        expected = {
            "CoinGeckoService.GetPrice",
            "CoinGeckoService.Search",
            "CoinGeckoService.GetTrending",
            "CoinGeckoService.GetMarkets",
            "CoinGeckoService.GetCoin",
            "CoinGeckoService.GetMarketChart",
            "CoinGeckoService.GetOHLC",
            "CoinGeckoService.GetGlobal",
            "CoinGeckoService.GetCategories",
            "CoinGeckoService.GetExchangeRates",
        }
        actual = set(server.tools.keys())
        missing = expected - actual
        assert not missing, f"Missing tools: {missing}"
        assert expected.issubset(actual)

    def test_tools_have_descriptions(self, server):
        for name, tool in server.tools.items():
            assert tool.description, f"{name} has no description"
            assert len(tool.description) > 10, f"{name} description too short"

    def test_tools_have_input_schemas(self, server):
        for name, tool in server.tools.items():
            schema = tool.input_schema
            assert isinstance(schema, dict), f"{name} schema is not a dict"
            assert schema.get("type") == "object", f"{name} schema type != object"


class TestCLIProjection:
    def test_get_price(self, server):
        result = server._cli(
            ["CoinGeckoService", "GetPrice", "-r", '{"ids":"bitcoin"}']
        )
        assert "prices" in result
        assert len(result["prices"]) >= 1

    def test_search(self, server):
        result = server._cli(
            ["CoinGeckoService", "Search", "-r", '{"query":"bitcoin"}']
        )
        assert "coins" in result
        assert result["coins"][0]["id"] == "bitcoin"

    def test_get_trending(self, server):
        result = server._cli(["CoinGeckoService", "GetTrending"])
        assert "coins" in result
        assert len(result["coins"]) == 2

    def test_get_markets(self, server):
        result = server._cli(["CoinGeckoService", "GetMarkets"])
        assert "coins" in result
        assert result["coins"][0]["id"] == "bitcoin"

    def test_get_coin(self, server):
        result = server._cli(
            ["CoinGeckoService", "GetCoin", "-r", '{"coin_id":"bitcoin"}']
        )
        assert result["name"] == "Bitcoin"
        assert result["symbol"] == "btc"

    def test_get_global(self, server):
        result = server._cli(["CoinGeckoService", "GetGlobal"])
        assert result.get("activeCryptocurrencies") == 15000 or result.get("active_cryptocurrencies") == 15000

    def test_get_categories(self, server):
        result = server._cli(["CoinGeckoService", "GetCategories"])
        assert "categories" in result
        assert len(result["categories"]) == 2

    def test_get_exchange_rates(self, server):
        result = server._cli(["CoinGeckoService", "GetExchangeRates"])
        assert "rates" in result
        assert "usd" in result["rates"]

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["CoinGeckoService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "CoinGeckoService" in result
        assert "GetPrice" in result

    def test_no_args_shows_usage(self, server):
        result = server._cli([])
        assert "Usage:" in result


class TestHTTPProjection:
    @pytest.fixture(autouse=True)
    def start_http(self, server):
        self.port = server._start_http(0)
        yield
        server._stop_http()

    def _post(self, path, body=None):
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read())

    def test_get_price(self):
        result = self._post(
            "/coingecko.v1.CoinGeckoService/GetPrice",
            {"ids": "bitcoin"},
        )
        assert "prices" in result

    def test_get_trending(self):
        result = self._post("/coingecko.v1.CoinGeckoService/GetTrending")
        assert "coins" in result

    def test_get_global(self):
        result = self._post("/coingecko.v1.CoinGeckoService/GetGlobal")
        # JSON field names may be camelCase or snake_case depending on serializer
        assert "activeCryptocurrencies" in result or "active_cryptocurrencies" in result

    def test_get_exchange_rates(self):
        result = self._post("/coingecko.v1.CoinGeckoService/GetExchangeRates")
        assert "rates" in result

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404


class TestMCPProjection:
    """Test the actual MCP JSON-RPC protocol over stdio."""

    @staticmethod
    def _mcp_request(msg_id, method, params=None):
        msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            msg["params"] = params
        return json.dumps(msg)

    @staticmethod
    def _run_mcp_session(messages: list[str]) -> list[dict]:
        import subprocess
        import sys

        stdin_data = "\n".join(messages) + "\n"

        script = f"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent.parent / "src"))

from coingecko_mcp.gen.coingecko.v1 import coingecko_pb2 as pb
from coingecko_mcp.service import CoinGeckoService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/simple/price" in url:
        resp.json.return_value = {{"bitcoin": {{"usd": 67000.0, "usd_market_cap": 1320000000000,
            "usd_24h_vol": 35000000000, "usd_24h_change": 2.5, "last_updated_at": 1700000000}}}}
    elif "/search/trending" in url:
        resp.json.return_value = {{
            "coins": [{{"item": {{"id": "pepe", "name": "Pepe", "symbol": "pepe",
                "market_cap_rank": 30, "thumb": "", "price_btc": 0.0000001, "score": 0}}}}],
            "nfts": [], "categories": []}}
    elif "/search" in url:
        resp.json.return_value = {{
            "coins": [{{"id": "bitcoin", "name": "Bitcoin", "symbol": "btc",
                "market_cap_rank": 1, "thumb": "", "large": ""}}],
            "exchanges": [], "categories": []}}
    elif "/coins/markets" in url:
        resp.json.return_value = [{{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin",
            "image": "", "current_price": 67000.0, "market_cap": 1320000000000,
            "market_cap_rank": 1, "total_volume": 35000000000, "high_24h": 68000.0,
            "low_24h": 66000.0, "price_change_24h": 1500.0, "price_change_percentage_24h": 2.3,
            "circulating_supply": 19700000, "total_supply": 21000000, "max_supply": 21000000,
            "ath": 73000.0, "ath_change_percentage": -8.2, "ath_date": "2024-03-14",
            "atl": 67.81, "atl_change_percentage": 98700.0, "atl_date": "2013-07-06",
            "last_updated": "2025-01-15T10:00:00Z"}}]
    elif "/global" in url:
        resp.json.return_value = {{"data": {{"active_cryptocurrencies": 15000, "markets": 1100,
            "total_market_cap": {{"usd": 2500000000000}}, "total_volume": {{"usd": 100000000000}},
            "market_cap_percentage": {{"btc": 52.3, "eth": 16.8}},
            "market_cap_change_percentage_24h_usd": 1.5, "updated_at": 1700000000}}}}
    elif "/exchange_rates" in url:
        resp.json.return_value = {{"rates": {{
            "usd": {{"name": "US Dollar", "unit": "$", "value": 67000.0, "type": "fiat"}}}}}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = CoinGeckoService.__new__(CoinGeckoService)
svc._http = http
svc._api_key = None

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-cg", version="0.0.1")
server.register(svc)
server.serve(mcp=True)
"""
        proc = subprocess.run(
            [sys.executable, "-c", script],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=10,
        )

        responses = []
        for line in proc.stdout.strip().split("\n"):
            if line.strip():
                responses.append(json.loads(line))
        return responses

    def test_initialize(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }),
        ])
        assert len(responses) == 1
        assert responses[0]["result"]["protocolVersion"] == "2024-11-05"
        assert responses[0]["result"]["serverInfo"]["name"] == "test-cg"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "CoinGeckoService.GetPrice" in names
        assert "CoinGeckoService.GetTrending" in names
        assert "CoinGeckoService.GetGlobal" in names

    def test_tool_call_get_price(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CoinGeckoService.GetPrice",
                "arguments": {"ids": "bitcoin"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "prices" in result
        assert result["prices"][0].get("coinId") == "bitcoin" or result["prices"][0].get("coin_id") == "bitcoin"

    def test_tool_call_get_trending(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CoinGeckoService.GetTrending",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "coins" in result
        assert result["coins"][0]["id"] == "pepe"

    def test_tool_call_get_global(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CoinGeckoService.GetGlobal",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("activeCryptocurrencies") == 15000 or result.get("active_cryptocurrencies") == 15000

    def test_unknown_tool(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DoesNotExist",
                "arguments": {},
            }),
        ])
        resp = responses[1]
        assert "error" in resp or resp.get("result", {}).get("isError") is True

    def test_ping(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "ping", {}),
        ])
        assert responses[1]["result"] == {}

    def test_unknown_method(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "unknown/method", {}),
        ])
        assert "error" in responses[1]
        assert responses[1]["error"]["code"] == -32601

    def test_notification_ignored(self):
        """Notifications (no id) should not produce a response."""
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            # notification — no id field
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            self._mcp_request(2, "ping", {}),
        ])
        # Should only get responses for id=0 and id=2, not the notification.
        ids = [r.get("id") for r in responses]
        assert 0 in ids
        assert 2 in ids
        assert len(responses) == 2


class TestInterceptor:
    def test_interceptor_fires(self, server):
        calls = []

        def logging_interceptor(request, context, info, handler):
            calls.append(info.full_method)
            return handler(request, context)

        server.use(logging_interceptor)
        server._cli(["CoinGeckoService", "GetGlobal"])
        assert len(calls) == 1
        assert calls[0] == "/coingecko.v1.CoinGeckoService/GetGlobal"

    def test_interceptor_chain_order(self, server):
        order = []

        def interceptor_a(request, context, info, handler):
            order.append("A-before")
            resp = handler(request, context)
            order.append("A-after")
            return resp

        def interceptor_b(request, context, info, handler):
            order.append("B-before")
            resp = handler(request, context)
            order.append("B-after")
            return resp

        server.use(interceptor_a)
        server.use(interceptor_b)
        server._cli(["CoinGeckoService", "GetTrending"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
