"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from finnhub_mcp.gen.finnhub.v1 import finnhub_pb2 as pb
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
            "FinnhubService.GetQuote",
            "FinnhubService.SearchSymbol",
            "FinnhubService.GetCompanyProfile",
            "FinnhubService.GetCompanyNews",
            "FinnhubService.GetEarningsCalendar",
            "FinnhubService.GetRecommendationTrends",
            "FinnhubService.GetInsiderTransactions",
            "FinnhubService.GetMarketNews",
            "FinnhubService.GetPeers",
            "FinnhubService.GetBasicFinancials",
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
    def test_get_quote(self, server):
        result = server._cli(
            ["FinnhubService", "GetQuote", "-r", '{"symbol":"AAPL"}']
        )
        assert "currentPrice" in result or "current_price" in result

    def test_search_symbol(self, server):
        result = server._cli(
            ["FinnhubService", "SearchSymbol", "-r", '{"query":"apple"}']
        )
        assert "results" in result
        assert result["results"][0]["symbol"] == "AAPL"

    def test_get_company_profile(self, server):
        result = server._cli(
            ["FinnhubService", "GetCompanyProfile", "-r", '{"symbol":"AAPL"}']
        )
        assert result.get("name") == "Apple Inc" or result.get("ticker") == "AAPL"

    def test_get_company_news(self, server):
        result = server._cli(
            ["FinnhubService", "GetCompanyNews", "-r", '{"symbol":"AAPL","from_date":"2024-01-01","to_date":"2024-12-31"}']
        )
        assert "articles" in result
        assert len(result["articles"]) == 2

    def test_get_earnings_calendar(self, server):
        result = server._cli(
            ["FinnhubService", "GetEarningsCalendar", "-r", '{"from_date":"2024-01-01","to_date":"2024-03-31"}']
        )
        assert "earnings" in result
        assert len(result["earnings"]) == 2

    def test_get_recommendation_trends(self, server):
        result = server._cli(
            ["FinnhubService", "GetRecommendationTrends", "-r", '{"symbol":"AAPL"}']
        )
        assert "trends" in result
        assert len(result["trends"]) == 2

    def test_get_insider_transactions(self, server):
        result = server._cli(
            ["FinnhubService", "GetInsiderTransactions", "-r", '{"symbol":"AAPL"}']
        )
        assert "transactions" in result
        assert len(result["transactions"]) == 2

    def test_get_market_news(self, server):
        result = server._cli(["FinnhubService", "GetMarketNews"])
        assert "articles" in result
        assert len(result["articles"]) >= 1

    def test_get_peers(self, server):
        result = server._cli(
            ["FinnhubService", "GetPeers", "-r", '{"symbol":"AAPL"}']
        )
        assert "peers" in result
        assert "MSFT" in result["peers"]

    def test_get_basic_financials(self, server):
        result = server._cli(
            ["FinnhubService", "GetBasicFinancials", "-r", '{"symbol":"AAPL","metric":"all"}']
        )
        assert "peTrailing" in result or "pe_trailing" in result

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["FinnhubService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "FinnhubService" in result
        assert "GetQuote" in result

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

    def test_get_quote(self):
        result = self._post(
            "/finnhub.v1.FinnhubService/GetQuote",
            {"symbol": "AAPL"},
        )
        assert "currentPrice" in result or "current_price" in result

    def test_search_symbol(self):
        result = self._post(
            "/finnhub.v1.FinnhubService/SearchSymbol",
            {"query": "apple"},
        )
        assert "results" in result

    def test_get_market_news(self):
        result = self._post("/finnhub.v1.FinnhubService/GetMarketNews")
        assert "articles" in result

    def test_get_peers(self):
        result = self._post(
            "/finnhub.v1.FinnhubService/GetPeers",
            {"symbol": "AAPL"},
        )
        assert "peers" in result

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

from finnhub_mcp.gen.finnhub.v1 import finnhub_pb2 as pb
from finnhub_mcp.service import FinnhubService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/quote" in url and "/stock/" not in url:
        resp.json.return_value = {{"c": 178.72, "d": 2.38, "dp": 1.35,
            "h": 179.63, "l": 176.21, "o": 176.50, "pc": 176.34, "t": 1700000000}}
    elif "/search" in url:
        resp.json.return_value = {{"count": 2, "result": [
            {{"symbol": "AAPL", "description": "Apple Inc", "displaySymbol": "AAPL", "type": "Common Stock"}},
            {{"symbol": "AAPL.SW", "description": "Apple Inc", "displaySymbol": "AAPL.SW", "type": "Common Stock"}}]}}
    elif "/stock/peers" in url:
        resp.json.return_value = ["MSFT", "GOOGL", "META"]
    elif "/news" in url:
        resp.json.return_value = [{{"headline": "Markets Rally", "summary": "Stocks surged.",
            "source": "Bloomberg", "url": "https://bloomberg.com/rally",
            "datetime": 1700000000, "related": "", "category": "general",
            "image": "", "id": 789012}}]
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = FinnhubService.__new__(FinnhubService)
svc._http = http
svc._api_key = "test-key"

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-fh", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-fh"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "FinnhubService.GetQuote" in names
        assert "FinnhubService.SearchSymbol" in names
        assert "FinnhubService.GetMarketNews" in names

    def test_tool_call_get_quote(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FinnhubService.GetQuote",
                "arguments": {"symbol": "AAPL"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert result.get("currentPrice") == 178.72 or result.get("current_price") == 178.72

    def test_tool_call_search_symbol(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FinnhubService.SearchSymbol",
                "arguments": {"query": "apple"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "results" in result
        assert result["results"][0]["symbol"] == "AAPL"

    def test_tool_call_get_market_news(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FinnhubService.GetMarketNews",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "articles" in result
        assert result["articles"][0]["headline"] == "Markets Rally"

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
        server._cli(["FinnhubService", "GetMarketNews"])
        assert len(calls) == 1
        assert calls[0] == "/finnhub.v1.FinnhubService/GetMarketNews"

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
        server._cli(["FinnhubService", "GetPeers", "-r", '{"symbol":"AAPL"}'])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
