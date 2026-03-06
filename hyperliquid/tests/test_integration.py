"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from hyperliquid_mcp.gen.hyperliquid.v1 import hyperliquid_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_13_tools_registered(self, server):
        assert len(server.tools) == 13

    def test_tool_names(self, server):
        expected = {
            "HyperliquidService.GetMeta",
            "HyperliquidService.GetAllMids",
            "HyperliquidService.GetOrderbook",
            "HyperliquidService.GetCandles",
            "HyperliquidService.GetAccountState",
            "HyperliquidService.GetOpenOrders",
            "HyperliquidService.GetFills",
            "HyperliquidService.PlaceOrder",
            "HyperliquidService.CancelOrder",
            "HyperliquidService.MarketOpen",
            "HyperliquidService.MarketClose",
            "HyperliquidService.UpdateLeverage",
            "HyperliquidService.Transfer",
        }
        assert set(server.tools.keys()) == expected

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
    def test_get_all_mids(self, server):
        result = server._cli(["HyperliquidService", "GetAllMids"])
        assert result["mids"]["BTC"] == "67000.0"
        assert result["mids"]["ETH"] == "3500.0"

    def test_get_orderbook(self, server):
        result = server._cli(
            ["HyperliquidService", "GetOrderbook", "-r", '{"coin":"BTC"}']
        )
        assert len(result["bids"]) == 2
        assert result["bids"][0]["price"] == "66990.0"

    def test_get_account_state(self, server):
        result = server._cli(
            [
                "HyperliquidService",
                "GetAccountState",
                "-r",
                '{"address":"0xabc"}',
            ]
        )
        assert result["account_value"] == "10000.0"
        assert len(result["positions"]) == 1
        assert result["positions"][0]["coin"] == "ETH"

    def test_place_order(self, server):
        result = server._cli(
            [
                "HyperliquidService",
                "PlaceOrder",
                "-r",
                '{"coin":"BTC","side":"SIDE_BUY","size":"0.1","price":"65000.0"}',
            ]
        )
        assert result["success"] is True
        assert int(result["order_id"]) == 99999

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["HyperliquidService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "HyperliquidService" in result
        assert "GetMeta" in result

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

    def test_get_all_mids(self):
        result = self._post("/hyperliquid.v1.HyperliquidService/GetAllMids")
        assert result["mids"]["BTC"] == "67000.0"

    def test_get_orderbook(self):
        result = self._post(
            "/hyperliquid.v1.HyperliquidService/GetOrderbook", {"coin": "BTC"}
        )
        assert len(result["bids"]) == 2
        assert result["asks"][0]["price"] == "67010.0"

    def test_place_order(self):
        result = self._post(
            "/hyperliquid.v1.HyperliquidService/PlaceOrder",
            {
                "coin": "BTC",
                "side": "SIDE_BUY",
                "size": "0.1",
                "price": "65000.0",
                "time_in_force": "TIME_IN_FORCE_GTC",
            },
        )
        assert result["success"] is True

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
        """Spawn MCP server subprocess, pipe JSON-RPC messages, collect responses."""
        import subprocess
        import sys

        stdin_data = "\n".join(messages) + "\n"

        script = f"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent.parent / "src"))

from hyperliquid_mcp.gen.hyperliquid.v1 import hyperliquid_pb2 as pb
from hyperliquid_mcp.service import HyperliquidService
from invariant import Server

# Build mocked service (same as conftest.py fixtures).
info = MagicMock()
info.meta.return_value = {{"universe": [{{"name": "BTC", "szDecimals": 5, "maxLeverage": 40}}]}}
info.all_mids.return_value = {{"BTC": "67000.0", "ETH": "3500.0"}}
info.l2_snapshot.return_value = {{
    "levels": [
        [{{"px": "66990.0", "sz": "1.5", "n": 3}}],
        [{{"px": "67010.0", "sz": "0.8", "n": 2}}],
    ]
}}

exchange = MagicMock()
exchange.order.return_value = {{
    "status": "ok",
    "response": {{"type": "order", "data": {{"statuses": [{{"resting": {{"oid": 99999}}}}]}}}},
}}

svc = HyperliquidService.__new__(HyperliquidService)
svc._info = info
svc._exchange = exchange

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-hl", version="0.0.1")
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
        responses = self._run_mcp_session(
            [
                self._mcp_request(
                    0,
                    "initialize",
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"},
                    },
                ),
            ]
        )
        assert len(responses) == 1
        assert responses[0]["result"]["protocolVersion"] == "2024-11-05"
        assert responses[0]["result"]["serverInfo"]["name"] == "test-hl"
        assert responses[0]["result"]["capabilities"]["tools"] == {}

    def test_tools_list(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(1, "tools/list", {}),
            ]
        )
        tools = responses[1]["result"]["tools"]
        assert len(tools) == 13
        names = {t["name"] for t in tools}
        assert "HyperliquidService.GetMeta" in names
        assert "HyperliquidService.PlaceOrder" in names
        assert "HyperliquidService.Transfer" in names

    def test_tools_have_descriptions_and_schemas(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(1, "tools/list", {}),
            ]
        )
        for tool in responses[1]["result"]["tools"]:
            assert tool["description"], f"{tool['name']} missing description"
            assert tool["inputSchema"]["type"] == "object"

    def test_tool_call_get_all_mids(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(
                    1,
                    "tools/call",
                    {"name": "HyperliquidService.GetAllMids", "arguments": {}},
                ),
            ]
        )
        content = responses[1]["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        result = json.loads(content[0]["text"])
        assert result["mids"]["BTC"] == "67000.0"
        assert result["mids"]["ETH"] == "3500.0"

    def test_tool_call_with_arguments(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(
                    1,
                    "tools/call",
                    {
                        "name": "HyperliquidService.PlaceOrder",
                        "arguments": {
                            "coin": "BTC",
                            "side": "SIDE_BUY",
                            "size": "0.1",
                            "price": "65000.0",
                        },
                    },
                ),
            ]
        )
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result["success"] is True
        assert result["status"] == "resting"

    def test_tool_call_unknown_tool(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(
                    1,
                    "tools/call",
                    {"name": "DoesNotExist", "arguments": {}},
                ),
            ]
        )
        resp = responses[1]
        assert "error" in resp or resp.get("result", {}).get("isError") is True

    def test_ping(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(1, "ping", {}),
            ]
        )
        assert responses[1]["result"] == {}

    def test_unknown_method(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(1, "unknown/method", {}),
            ]
        )
        assert "error" in responses[1]
        assert responses[1]["error"]["code"] == -32601

    def test_notification_gets_no_response(self):
        """Notifications (no id) should not produce a response."""
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                # Notification — no id field.
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                self._mcp_request(1, "ping", {}),
            ]
        )
        # Should have exactly 2 responses: initialize + ping. Notification is silent.
        assert len(responses) == 2
        assert responses[0]["id"] == 0
        assert responses[1]["id"] == 1


class TestInterceptor:
    def test_interceptor_fires(self, server):
        calls = []

        def logging_interceptor(request, context, info, handler):
            calls.append(info.full_method)
            return handler(request, context)

        server.use(logging_interceptor)
        server._cli(["HyperliquidService", "GetAllMids"])
        assert len(calls) == 1
        assert calls[0] == "/hyperliquid.v1.HyperliquidService/GetAllMids"

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
        server._cli(["HyperliquidService", "GetMeta"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
