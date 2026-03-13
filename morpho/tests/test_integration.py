"""Integration tests -- verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from morpho_mcp.gen.morpho.v1 import morpho_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 5

    def test_tool_names(self, server):
        expected = {
            "MorphoService.ListMarkets",
            "MorphoService.GetMarket",
            "MorphoService.ListVaults",
            "MorphoService.GetVault",
            "MorphoService.ListMarketPositions",
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
    def test_list_markets(self, server):
        result = server._cli(["MorphoService", "ListMarkets"])
        assert "markets" in result
        assert len(result["markets"]) == 2

    def test_get_market(self, server):
        result = server._cli(
            [
                "MorphoService",
                "GetMarket",
                "-r",
                '{"uniqueKey":"0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"}',
            ]
        )
        assert "market" in result
        m = result["market"]
        key = m.get("uniqueKey") or m.get("unique_key")
        assert key == "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"

    def test_list_vaults(self, server):
        result = server._cli(["MorphoService", "ListVaults"])
        assert "vaults" in result
        assert len(result["vaults"]) == 2

    def test_get_vault(self, server):
        result = server._cli(
            [
                "MorphoService",
                "GetVault",
                "-r",
                '{"address":"0xBEEF01735c132Ada46AA9aA9cE6E9faA753e1076"}',
            ]
        )
        assert "vault" in result
        v = result["vault"]
        assert v["name"] == "Steakhouse Prime USDC"

    def test_list_market_positions(self, server):
        result = server._cli(
            [
                "MorphoService",
                "ListMarketPositions",
                "-r",
                '{"userAddress":"0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}',
            ]
        )
        assert "positions" in result
        assert len(result["positions"]) == 1

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["MorphoService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "MorphoService" in result
        assert "ListMarkets" in result

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

    def test_list_markets(self):
        result = self._post("/morpho.v1.MorphoService/ListMarkets")
        assert "markets" in result

    def test_get_vault(self):
        result = self._post(
            "/morpho.v1.MorphoService/GetVault",
            {"address": "0xBEEF01735c132Ada46AA9aA9cE6E9faA753e1076"},
        )
        assert "vault" in result

    def test_list_vaults(self):
        result = self._post("/morpho.v1.MorphoService/ListVaults")
        assert "vaults" in result

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

from conftest import _make_mock_http
from morpho_mcp.service import MorphoService
from invariant import Server

svc = MorphoService.__new__(MorphoService)
svc._http = _make_mock_http()

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-morpho", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-morpho"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 5
        names = {t["name"] for t in tools}
        assert "MorphoService.ListMarkets" in names
        assert "MorphoService.GetMarket" in names
        assert "MorphoService.ListVaults" in names
        assert "MorphoService.GetVault" in names
        assert "MorphoService.ListMarketPositions" in names

    def test_tool_call_list_markets(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "MorphoService.ListMarkets",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "markets" in result
        assert len(result["markets"]) == 2

    def test_tool_call_list_vaults(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "MorphoService.ListVaults",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "vaults" in result

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
        server._cli(["MorphoService", "ListMarkets"])
        assert len(calls) == 1
        assert calls[0] == "/morpho.v1.MorphoService/ListMarkets"

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
        server._cli(["MorphoService", "ListVaults"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
