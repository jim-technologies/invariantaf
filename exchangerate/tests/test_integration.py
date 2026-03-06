"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from exchangerate_mcp.gen.exchangerate.v1 import exchangerate_pb2 as pb
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
            "ExchangeRateService.GetLatestRates",
            "ExchangeRateService.GetLatestForCurrencies",
            "ExchangeRateService.Convert",
            "ExchangeRateService.GetHistoricalRates",
            "ExchangeRateService.GetTimeSeries",
            "ExchangeRateService.ListCurrencies",
            "ExchangeRateService.GetHistoricalForCurrencies",
            "ExchangeRateService.ConvertHistorical",
            "ExchangeRateService.GetTimeSeriesForPair",
            "ExchangeRateService.GetLatestAll",
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
    def test_get_latest_rates(self, server):
        result = server._cli(
            ["ExchangeRateService", "GetLatestRates", "-r", '{"base":"EUR"}']
        )
        assert "rates" in result
        assert "USD" in result["rates"]

    def test_get_latest_for_currencies(self, server):
        result = server._cli(
            ["ExchangeRateService", "GetLatestForCurrencies", "-r", '{"base":"EUR","symbols":"USD,GBP"}']
        )
        assert "rates" in result
        assert "USD" in result["rates"]

    def test_convert(self, server):
        result = server._cli(
            ["ExchangeRateService", "Convert", "-r", '{"from":"USD","to":"EUR","amount":100}']
        )
        assert "rates" in result
        assert result.get("amount") == 100.0

    def test_get_historical_rates(self, server):
        result = server._cli(
            ["ExchangeRateService", "GetHistoricalRates", "-r", '{"date":"2024-01-15"}']
        )
        assert "rates" in result
        assert "USD" in result["rates"]

    def test_get_time_series(self, server):
        result = server._cli(
            ["ExchangeRateService", "GetTimeSeries", "-r", '{"start_date":"2025-01-10","end_date":"2025-01-15"}']
        )
        key = "dailyRates" if "dailyRates" in result else "daily_rates"
        assert key in result
        assert len(result[key]) >= 1

    def test_list_currencies(self, server):
        result = server._cli(["ExchangeRateService", "ListCurrencies"])
        assert "currencies" in result
        assert "USD" in result["currencies"]

    def test_get_latest_all(self, server):
        result = server._cli(["ExchangeRateService", "GetLatestAll"])
        assert "rates" in result
        assert result.get("base") == "EUR"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["ExchangeRateService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "ExchangeRateService" in result
        assert "GetLatestRates" in result

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

    def test_get_latest_rates(self):
        result = self._post(
            "/exchangerate.v1.ExchangeRateService/GetLatestRates",
            {"base": "EUR"},
        )
        assert "rates" in result

    def test_list_currencies(self):
        result = self._post("/exchangerate.v1.ExchangeRateService/ListCurrencies")
        assert "currencies" in result

    def test_get_latest_all(self):
        result = self._post("/exchangerate.v1.ExchangeRateService/GetLatestAll")
        assert "rates" in result

    def test_convert(self):
        result = self._post(
            "/exchangerate.v1.ExchangeRateService/Convert",
            {"from": "USD", "to": "EUR", "amount": 100},
        )
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

sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent / "src"))

from exchangerate_mcp.gen.exchangerate.v1 import exchangerate_pb2 as pb
from exchangerate_mcp.service import ExchangeRateService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    params = params or {{}}
    if "/currencies" in url:
        resp.json.return_value = {{"USD": "United States Dollar", "EUR": "Euro", "GBP": "British Pound"}}
    elif ".." in url:
        resp.json.return_value = {{"base": "EUR", "start_date": "2025-01-10", "end_date": "2025-01-15",
            "rates": {{"2025-01-10": {{"USD": 1.029}}, "2025-01-15": {{"USD": 1.0305}}}}}}
    elif "amount" in params:
        resp.json.return_value = {{"amount": 100.0, "base": "USD", "date": "2025-01-15",
            "rates": {{"EUR": 97.04}}}}
    elif "symbols" in params:
        resp.json.return_value = {{"base": "EUR", "date": "2025-01-15",
            "rates": {{"USD": 1.0305}}}}
    else:
        resp.json.return_value = {{"base": "EUR", "date": "2025-01-15",
            "rates": {{"USD": 1.0305, "GBP": 0.8451, "JPY": 161.52}}}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = ExchangeRateService.__new__(ExchangeRateService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-er", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-er"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "ExchangeRateService.GetLatestRates" in names
        assert "ExchangeRateService.Convert" in names
        assert "ExchangeRateService.ListCurrencies" in names

    def test_tool_call_get_latest_rates(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "ExchangeRateService.GetLatestRates",
                "arguments": {"base": "EUR"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "rates" in result
        assert "USD" in result["rates"]

    def test_tool_call_list_currencies(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "ExchangeRateService.ListCurrencies",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "currencies" in result
        assert "USD" in result["currencies"]

    def test_tool_call_get_latest_all(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "ExchangeRateService.GetLatestAll",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "rates" in result
        assert result.get("base") == "EUR"

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
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            self._mcp_request(2, "ping", {}),
        ])
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
        server._cli(["ExchangeRateService", "GetLatestAll"])
        assert len(calls) == 1
        assert calls[0] == "/exchangerate.v1.ExchangeRateService/GetLatestAll"

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
        server._cli(["ExchangeRateService", "ListCurrencies"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
