"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from fred_mcp.gen.fred.v1 import fred_pb2 as pb
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
            "FREDService.GetSeries",
            "FREDService.GetSeriesObservations",
            "FREDService.SearchSeries",
            "FREDService.GetCategory",
            "FREDService.GetCategoryChildren",
            "FREDService.GetCategorySeries",
            "FREDService.GetRelease",
            "FREDService.GetReleaseDates",
            "FREDService.GetReleaseSeries",
            "FREDService.GetSeriesCategories",
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
    def test_get_series(self, server):
        result = server._cli(
            ["FREDService", "GetSeries", "-r", '{"series_id":"GDP"}']
        )
        assert "series" in result
        assert result["series"]["id"] == "GDP"
        assert result["series"]["title"] == "Gross Domestic Product"

    def test_get_series_observations(self, server):
        result = server._cli(
            ["FREDService", "GetSeriesObservations", "-r", '{"series_id":"GDP"}']
        )
        assert "observations" in result
        assert len(result["observations"]) == 3
        assert result["observations"][0]["date"] == "2024-01-01"

    def test_search_series(self, server):
        result = server._cli(
            ["FREDService", "SearchSeries", "-r", '{"search_text":"inflation"}']
        )
        assert "results" in result
        assert result["results"][0]["id"] == "CPIAUCSL"

    def test_get_category(self, server):
        result = server._cli(
            ["FREDService", "GetCategory", "-r", '{"category_id":32991}']
        )
        assert "category" in result
        assert result["category"]["name"] == "Prices"

    def test_get_category_children(self, server):
        result = server._cli(
            ["FREDService", "GetCategoryChildren", "-r", '{"category_id":32991}']
        )
        assert "categories" in result
        assert len(result["categories"]) == 2

    def test_get_release(self, server):
        result = server._cli(
            ["FREDService", "GetRelease", "-r", '{"release_id":10}']
        )
        assert "release" in result
        assert result["release"]["name"] == "Consumer Price Index"

    def test_get_release_dates(self, server):
        result = server._cli(
            ["FREDService", "GetReleaseDates", "-r", '{"release_id":10}']
        )
        assert "releaseDates" in result or "release_dates" in result
        dates = result.get("releaseDates") or result.get("release_dates")
        assert len(dates) == 3

    def test_get_series_categories(self, server):
        result = server._cli(
            ["FREDService", "GetSeriesCategories", "-r", '{"series_id":"GDP"}']
        )
        assert "categories" in result
        assert len(result["categories"]) == 2

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["FREDService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "FREDService" in result
        assert "GetSeries" in result

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

    def test_get_series(self):
        result = self._post(
            "/fred.v1.FREDService/GetSeries",
            {"series_id": "GDP"},
        )
        assert "series" in result

    def test_search_series(self):
        result = self._post(
            "/fred.v1.FREDService/SearchSeries",
            {"search_text": "inflation"},
        )
        assert "results" in result

    def test_get_series_observations(self):
        result = self._post(
            "/fred.v1.FREDService/GetSeriesObservations",
            {"series_id": "GDP"},
        )
        assert "observations" in result

    def test_get_release(self):
        result = self._post(
            "/fred.v1.FREDService/GetRelease",
            {"release_id": 10},
        )
        assert "release" in result

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
sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent / "tests"))

from fred_mcp.gen.fred.v1 import fred_pb2 as pb
from fred_mcp.service import FREDService
from invariant import Server
from conftest import _make_mock_http

http = _make_mock_http()

svc = FREDService.__new__(FREDService)
svc._http = http
svc._api_key = "test-key"

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-fred", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-fred"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "FREDService.GetSeries" in names
        assert "FREDService.SearchSeries" in names
        assert "FREDService.GetSeriesObservations" in names

    def test_tool_call_get_series(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FREDService.GetSeries",
                "arguments": {"series_id": "GDP"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "series" in result
        assert result["series"]["id"] == "GDP"

    def test_tool_call_search(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FREDService.SearchSeries",
                "arguments": {"search_text": "inflation"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "results" in result
        assert result["results"][0]["id"] == "CPIAUCSL"

    def test_tool_call_get_observations(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FREDService.GetSeriesObservations",
                "arguments": {"series_id": "GDP"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "observations" in result
        assert len(result["observations"]) == 3

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
        server._cli(["FREDService", "GetSeries", "-r", '{"series_id":"GDP"}'])
        assert len(calls) == 1
        assert calls[0] == "/fred.v1.FREDService/GetSeries"

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
        server._cli(["FREDService", "SearchSeries", "-r", '{"search_text":"test"}'])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
