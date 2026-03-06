"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from alphavantage_mcp.gen.alphavantage.v1 import alphavantage_pb2 as pb
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
            "AlphaVantageService.GetQuote",
            "AlphaVantageService.SearchSymbol",
            "AlphaVantageService.GetDailyTimeSeries",
            "AlphaVantageService.GetWeeklyTimeSeries",
            "AlphaVantageService.GetMonthlyTimeSeries",
            "AlphaVantageService.GetSMA",
            "AlphaVantageService.GetRSI",
            "AlphaVantageService.GetMACD",
            "AlphaVantageService.GetCompanyOverview",
            "AlphaVantageService.GetEarnings",
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
            ["AlphaVantageService", "GetQuote", "-r", '{"symbol":"AAPL"}']
        )
        assert "symbol" in result
        assert result["symbol"] == "AAPL"

    def test_search_symbol(self, server):
        result = server._cli(
            ["AlphaVantageService", "SearchSymbol", "-r", '{"keywords":"Apple"}']
        )
        assert "matches" in result
        assert result["matches"][0]["symbol"] == "AAPL"

    def test_get_daily_time_series(self, server):
        result = server._cli(
            ["AlphaVantageService", "GetDailyTimeSeries", "-r", '{"symbol":"AAPL"}']
        )
        assert "entries" in result
        assert len(result["entries"]) == 2

    def test_get_weekly_time_series(self, server):
        result = server._cli(
            ["AlphaVantageService", "GetWeeklyTimeSeries", "-r", '{"symbol":"AAPL"}']
        )
        assert "entries" in result
        assert len(result["entries"]) == 2

    def test_get_monthly_time_series(self, server):
        result = server._cli(
            ["AlphaVantageService", "GetMonthlyTimeSeries", "-r", '{"symbol":"AAPL"}']
        )
        assert "entries" in result
        assert len(result["entries"]) == 2

    def test_get_sma(self, server):
        result = server._cli(
            ["AlphaVantageService", "GetSMA", "-r", '{"symbol":"AAPL"}']
        )
        assert "entries" in result
        assert len(result["entries"]) == 3

    def test_get_rsi(self, server):
        result = server._cli(
            ["AlphaVantageService", "GetRSI", "-r", '{"symbol":"AAPL"}']
        )
        assert "entries" in result
        assert len(result["entries"]) == 3

    def test_get_macd(self, server):
        result = server._cli(
            ["AlphaVantageService", "GetMACD", "-r", '{"symbol":"AAPL"}']
        )
        assert "entries" in result
        assert len(result["entries"]) == 2

    def test_get_company_overview(self, server):
        result = server._cli(
            ["AlphaVantageService", "GetCompanyOverview", "-r", '{"symbol":"AAPL"}']
        )
        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc"

    def test_get_earnings(self, server):
        result = server._cli(
            ["AlphaVantageService", "GetEarnings", "-r", '{"symbol":"AAPL"}']
        )
        assert result["symbol"] == "AAPL"
        ann_key = "annualEarnings" if "annualEarnings" in result else "annual_earnings"
        assert len(result[ann_key]) == 2

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["AlphaVantageService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "AlphaVantageService" in result
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
            "/alphavantage.v1.AlphaVantageService/GetQuote",
            {"symbol": "AAPL"},
        )
        assert result["symbol"] == "AAPL"

    def test_search_symbol(self):
        result = self._post(
            "/alphavantage.v1.AlphaVantageService/SearchSymbol",
            {"keywords": "Apple"},
        )
        assert "matches" in result

    def test_get_company_overview(self):
        result = self._post(
            "/alphavantage.v1.AlphaVantageService/GetCompanyOverview",
            {"symbol": "AAPL"},
        )
        assert result["symbol"] == "AAPL"

    def test_get_earnings(self):
        result = self._post(
            "/alphavantage.v1.AlphaVantageService/GetEarnings",
            {"symbol": "AAPL"},
        )
        assert result["symbol"] == "AAPL"

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

from alphavantage_mcp.gen.alphavantage.v1 import alphavantage_pb2 as pb
from alphavantage_mcp.service import AlphaVantageService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    fn = (params or {{}}).get("function", "")
    if fn == "GLOBAL_QUOTE":
        resp.json.return_value = {{"Global Quote": {{
            "01. symbol": "AAPL", "02. open": "182.35", "03. high": "183.92",
            "04. low": "181.46", "05. price": "183.58", "06. volume": "48425673",
            "07. latest trading day": "2025-01-15", "08. previous close": "181.18",
            "09. change": "2.40", "10. change percent": "1.3244%"}}}}
    elif fn == "SYMBOL_SEARCH":
        resp.json.return_value = {{"bestMatches": [
            {{"1. symbol": "AAPL", "2. name": "Apple Inc", "3. type": "Equity",
             "4. region": "United States", "5. marketOpen": "09:30",
             "6. marketClose": "16:00", "7. timezone": "UTC-04",
             "8. currency": "USD", "9. matchScore": "1.0000"}}]}}
    elif fn == "OVERVIEW":
        resp.json.return_value = {{"Symbol": "AAPL", "Name": "Apple Inc",
            "Description": "Apple Inc. designs smartphones.",
            "Exchange": "NASDAQ", "Currency": "USD", "Country": "USA",
            "Sector": "TECHNOLOGY", "Industry": "ELECTRONIC COMPUTERS",
            "MarketCapitalization": "2850000000000", "PERatio": "29.50",
            "EPS": "6.42"}}
    elif fn == "EARNINGS":
        resp.json.return_value = {{"symbol": "AAPL",
            "annualEarnings": [{{"fiscalDateEnding": "2024-09-30", "reportedEPS": "6.42"}}],
            "quarterlyEarnings": [{{"fiscalDateEnding": "2024-09-30",
                "reportedDate": "2024-10-31", "reportedEPS": "1.64",
                "estimatedEPS": "1.60", "surprise": "0.04",
                "surprisePercentage": "2.5000"}}]}}
    elif fn == "TIME_SERIES_DAILY":
        resp.json.return_value = {{"Meta Data": {{"2. Symbol": "AAPL",
            "3. Last Refreshed": "2025-01-15"}},
            "Time Series (Daily)": {{"2025-01-15": {{
                "1. open": "182.35", "2. high": "183.92",
                "3. low": "181.46", "4. close": "183.58",
                "5. volume": "48425673"}}}}}}
    elif fn == "SMA":
        resp.json.return_value = {{"Meta Data": {{"1: Symbol": "AAPL",
            "2: Indicator": "Simple Moving Average (SMA)"}},
            "Technical Analysis: SMA": {{"2025-01-15": {{"SMA": "180.25"}}}}}}
    elif fn == "RSI":
        resp.json.return_value = {{"Meta Data": {{"1: Symbol": "AAPL",
            "2: Indicator": "Relative Strength Index (RSI)"}},
            "Technical Analysis: RSI": {{"2025-01-15": {{"RSI": "62.34"}}}}}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = AlphaVantageService.__new__(AlphaVantageService)
svc._http = http
svc._api_key = "demo"

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-av", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-av"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "AlphaVantageService.GetQuote" in names
        assert "AlphaVantageService.SearchSymbol" in names
        assert "AlphaVantageService.GetCompanyOverview" in names

    def test_tool_call_get_quote(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "AlphaVantageService.GetQuote",
                "arguments": {"symbol": "AAPL"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert result["symbol"] == "AAPL"

    def test_tool_call_search_symbol(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "AlphaVantageService.SearchSymbol",
                "arguments": {"keywords": "Apple"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "matches" in result
        assert result["matches"][0]["symbol"] == "AAPL"

    def test_tool_call_get_company_overview(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "AlphaVantageService.GetCompanyOverview",
                "arguments": {"symbol": "AAPL"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc"

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
        server._cli(["AlphaVantageService", "GetQuote", "-r", '{"symbol":"AAPL"}'])
        assert len(calls) == 1
        assert calls[0] == "/alphavantage.v1.AlphaVantageService/GetQuote"

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
        server._cli(["AlphaVantageService", "GetQuote", "-r", '{"symbol":"AAPL"}'])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
