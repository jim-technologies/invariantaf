"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from lido_mcp.gen.lido.v1 import lido_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 3

    def test_tool_names(self, server):
        expected = {
            "LidoService.GetStETHApr",
            "LidoService.GetStETHAprSMA",
            "LidoService.GetWithdrawalTime",
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
    def test_get_steth_apr(self, server):
        result = server._cli(["LidoService", "GetStETHApr"])
        assert "data" in result
        assert "meta" in result
        data = result["data"]
        assert "apr" in data
        assert data["apr"] == 2.464

    def test_get_steth_apr_sma(self, server):
        result = server._cli(["LidoService", "GetStETHAprSMA"])
        key = "smaApr" if "smaApr" in result else "sma_apr"
        assert key in result
        assert result[key] == 2.387125
        assert "aprs" in result
        assert len(result["aprs"]) == 8

    def test_get_withdrawal_time(self, server):
        result = server._cli(
            ["LidoService", "GetWithdrawalTime", "-r", '{"amount":32}']
        )
        assert result.get("status") == "calculated"
        key = "requestInfo" if "requestInfo" in result else "request_info"
        assert key in result
        info = result[key]
        fin_key = "finalizationIn" if "finalizationIn" in info else "finalization_in"
        assert fin_key in info

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["LidoService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "LidoService" in result
        assert "GetStETHApr" in result

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

    def test_get_steth_apr(self):
        result = self._post("/lido.v1.LidoService/GetStETHApr")
        assert "data" in result
        assert "meta" in result

    def test_get_steth_apr_sma(self):
        result = self._post("/lido.v1.LidoService/GetStETHAprSMA")
        assert "aprs" in result

    def test_get_withdrawal_time(self):
        result = self._post(
            "/lido.v1.LidoService/GetWithdrawalTime",
            {"amount": 32},
        )
        assert "status" in result

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

from lido_mcp.gen.lido.v1 import lido_pb2 as pb
from lido_mcp.service import LidoService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/apr/last" in url:
        resp.json.return_value = {{
            "data": {{"timeUnix": 1773318119, "apr": 2.464}},
            "meta": {{"symbol": "stETH",
                      "address": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
                      "chainId": 1}}
        }}
    elif "/apr/sma" in url:
        resp.json.return_value = {{
            "data": {{
                "aprs": [
                    {{"timeUnix": 1772713319, "apr": 2.438}},
                    {{"timeUnix": 1772799719, "apr": 2.34}},
                    {{"timeUnix": 1772886071, "apr": 2.332}},
                    {{"timeUnix": 1772972459, "apr": 2.338}},
                    {{"timeUnix": 1773058919, "apr": 2.371}},
                    {{"timeUnix": 1773145403, "apr": 2.384}},
                    {{"timeUnix": 1773231791, "apr": 2.43}},
                    {{"timeUnix": 1773318119, "apr": 2.464}},
                ],
                "smaApr": 2.387125,
            }},
            "meta": {{"symbol": "stETH",
                      "address": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
                      "chainId": 1}}
        }}
    elif "/request-time/calculate" in url:
        resp.json.return_value = {{
            "requestInfo": {{
                "finalizationIn": 427922000,
                "finalizationAt": "2026-03-17T12:30:23.056Z",
                "type": "exitValidators",
            }},
            "status": "calculated",
            "nextCalculationAt": "2026-03-12T13:40:00.308Z",
        }}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = LidoService.__new__(LidoService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-lido", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-lido"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 3
        names = {t["name"] for t in tools}
        assert "LidoService.GetStETHApr" in names
        assert "LidoService.GetStETHAprSMA" in names
        assert "LidoService.GetWithdrawalTime" in names

    def test_tool_call_get_steth_apr(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "LidoService.GetStETHApr",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "data" in result
        assert result["data"]["apr"] == 2.464

    def test_tool_call_get_steth_apr_sma(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "LidoService.GetStETHAprSMA",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "aprs" in result

    def test_tool_call_get_withdrawal_time(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "LidoService.GetWithdrawalTime",
                "arguments": {"amount": 32},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert result.get("status") == "calculated"

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
        server._cli(["LidoService", "GetStETHApr"])
        assert len(calls) == 1
        assert calls[0] == "/lido.v1.LidoService/GetStETHApr"

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
        server._cli(["LidoService", "GetStETHApr"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
